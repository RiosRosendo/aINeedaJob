"""Monitor Gmail for replies and classify emails to update application status."""

import os
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import json
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from tools.db import execute_query, execute_update
from api.routes.gmail import get_gmail_tokens, refresh_gmail_token, GOOGLE_TOKEN_URL
from tools.llm_client import get_groq_client


def check_gmail_for_replies(user_id: str) -> Dict:
    """
    Check Gmail for replies related to applied jobs.

    1. Get Gmail credentials from database
    2. Fetch all applications for user
    3. Search emails by company/job title
    4. Classify emails using LLM (supports any language)
    5. Update application status based on classification
    6. Track processed email IDs to avoid duplicates

    Returns: {
        "error": str or None,
        "checked_at": datetime,
        "emails_found": int,
        "statuses_updated": int,
        "emails": [{ id, from, subject, classification, action_taken }]
    }
    """
    try:
        print(f"[EMAIL MONITOR] Starting email check for user {user_id}", flush=True)

        # Get Gmail tokens
        tokens = get_gmail_tokens(user_id)
        if not tokens:
            return {
                "error": "Gmail not connected. User needs to authorize Gmail access.",
                "checked_at": datetime.utcnow(),
                "emails_found": 0,
                "statuses_updated": 0,
                "emails": []
            }

        # Refresh token if expired
        if _is_token_expired(tokens.get('token_expiry')):
            print(f"[EMAIL MONITOR] Token expired, refreshing...", flush=True)
            new_token = refresh_gmail_token(user_id)
            if not new_token:
                return {
                    "error": "Failed to refresh Gmail token. Reconnect required.",
                    "checked_at": datetime.utcnow(),
                    "emails_found": 0,
                    "statuses_updated": 0,
                    "emails": []
                }
            tokens['access_token'] = new_token

        # Build Gmail service
        credentials = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri=GOOGLE_TOKEN_URL,
            client_id=os.getenv("GMAIL_CLIENT_ID"),
            client_secret=os.getenv("GMAIL_CLIENT_SECRET")
        )

        service = build('gmail', 'v1', credentials=credentials)

        # Get all user's applications
        apps = execute_query(
            """
            SELECT a.id, a.job_id, a.status, a.created_at, j.company, j.title
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.user_id = %s AND a.status IN ('applied', 'applied_unconfirmed')
            """,
            (user_id,)
        )

        if not apps:
            print(f"[EMAIL MONITOR] No applied jobs found for user {user_id}", flush=True)
            return {
                "error": None,
                "checked_at": datetime.utcnow(),
                "emails_found": 0,
                "statuses_updated": 0,
                "emails": []
            }

        # Search and classify emails
        emails_found = []
        statuses_updated = 0

        for app in apps:
            company = app.get('company', '')
            job_title = app.get('title', '')
            app_id = app.get('id')
            app_created = app.get('created_at')

            # Search emails from this company after application was created
            search_query = f'from:{company.split()[0].lower()} after:{app_created.strftime("%Y/%m/%d")}'

            print(f"[EMAIL MONITOR] Searching for emails: {search_query}", flush=True)

            try:
                results = service.users().messages().list(
                    userId='me',
                    q=search_query,
                    maxResults=10
                ).execute()

                messages = results.get('messages', [])

                for msg_data in messages:
                    msg_id = msg_data['id']

                    # Check if email already processed
                    if _is_email_processed(user_id, msg_id):
                        print(f"[EMAIL MONITOR] Email {msg_id} already processed, skipping", flush=True)
                        continue

                    # Fetch full email
                    message = service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full'
                    ).execute()

                    headers = message['payload'].get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), '')

                    # Get email body (simple version)
                    email_body = _extract_email_body(message)

                    # Classify email using LLM (autonomous, language-agnostic)
                    classification = _classify_email(
                        subject=subject,
                        sender=sender,
                        body=email_body,
                        company=company,
                        job_title=job_title
                    )

                    print(f"[EMAIL MONITOR] Email classified as: {classification}", flush=True)

                    # Update application status based on classification
                    new_status = _get_status_from_classification(classification)

                    if new_status and new_status != app.get('status'):
                        execute_update(
                            """
                            UPDATE applications
                            SET status = %s, updated_at = NOW()
                            WHERE id = %s AND user_id = %s
                            """,
                            (new_status, app_id, user_id)
                        )
                        print(f"[EMAIL MONITOR] Updated application {app_id} to status {new_status}", flush=True)
                        statuses_updated += 1

                    # Mark email as processed
                    _mark_email_processed(user_id, msg_id)

                    emails_found.append({
                        "id": msg_id,
                        "from": sender,
                        "subject": subject,
                        "classification": classification,
                        "action_taken": new_status if new_status else "no_status_change"
                    })

            except Exception as e:
                print(f"[EMAIL MONITOR] Error processing emails for {company}: {str(e)}", flush=True)
                continue

        print(f"[EMAIL MONITOR] Email check complete: found {len(emails_found)}, updated {statuses_updated}", flush=True)

        return {
            "error": None,
            "checked_at": datetime.utcnow(),
            "emails_found": len(emails_found),
            "statuses_updated": statuses_updated,
            "emails": emails_found
        }

    except Exception as e:
        print(f"[EMAIL MONITOR] FATAL ERROR: {type(e).__name__}: {str(e)}", flush=True)
        return {
            "error": f"Email check failed: {str(e)}",
            "checked_at": datetime.utcnow(),
            "emails_found": 0,
            "statuses_updated": 0,
            "emails": []
        }


def _extract_email_body(message: Dict) -> str:
    """Extract text body from email message."""
    try:
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'body' in message['payload']:
            if 'data' in message['payload']['body']:
                return base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
    except:
        pass
    return ""


def _classify_email(subject: str, sender: str, body: str, company: str, job_title: str) -> str:
    """
    Use Groq LLM to classify email as: interview_invite, offer, rejection, confirmation, other.

    Fully autonomous - works in any language without hardcoded keywords.
    """
    try:
        client = get_groq_client()

        prompt = f"""You are analyzing an email received in response to a job application.

Company Applied To: {company}
Job Title: {job_title}

Email Details:
From: {sender}
Subject: {subject}

Body:
{body}

Classify this email into ONE of these categories:
- interview_invite: Company is inviting for an interview/phone screen/technical assessment
- offer: Company is making a job offer
- rejection: Company is rejecting the application
- confirmation: Company is confirming receipt of application or providing reference number
- other: Doesn't fit above categories

Respond with ONLY the classification word (interview_invite, offer, rejection, confirmation, or other).
Analyze the content in ANY language - do not rely on English keywords."""

        response = client.messages.create(
            model="mixtral-8x7b-32768",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        classification = response.content[0].text.strip().lower()

        # Validate classification
        valid = ['interview_invite', 'offer', 'rejection', 'confirmation', 'other']
        if classification not in valid:
            classification = 'other'

        print(f"[EMAIL CLASSIFY] Result: {classification}", flush=True)
        return classification

    except Exception as e:
        print(f"[EMAIL CLASSIFY] Error: {type(e).__name__}: {str(e)}", flush=True)
        return 'other'


def _get_status_from_classification(classification: str) -> Optional[str]:
    """Map email classification to application status."""
    mapping = {
        'interview_invite': 'interview',
        'offer': 'offer',
        'rejection': 'rejected',
        'confirmation': None,  # Keep current status
        'other': None  # Keep current status
    }
    return mapping.get(classification)


def _is_email_processed(user_id: str, email_id: str) -> bool:
    """Check if email has already been processed for this user."""
    try:
        result = execute_query(
            "SELECT id FROM processed_emails WHERE user_id = %s AND email_id = %s",
            (user_id, email_id)
        )
        return bool(result)
    except:
        return False


def _mark_email_processed(user_id: str, email_id: str) -> None:
    """Mark email as processed to avoid reprocessing."""
    try:
        execute_update(
            "INSERT INTO processed_emails (user_id, email_id, processed_at) VALUES (%s, %s, NOW())",
            (user_id, email_id)
        )
        print(f"[EMAIL MONITOR] Marked email {email_id} as processed", flush=True)
    except Exception as e:
        print(f"[EMAIL MONITOR] Error marking email processed: {str(e)}", flush=True)


def _is_token_expired(token_expiry) -> bool:
    """Check if Gmail token is expired."""
    if not token_expiry:
        return True
    return datetime.utcnow() > (token_expiry - timedelta(minutes=5))
