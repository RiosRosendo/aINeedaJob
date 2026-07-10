"""
Email monitoring tool for tracking application replies from companies.

Monitors Gmail inbox for emails from companies where user has applied.
Classifies emails using LLM to determine application status.
"""

import os
from typing import Optional, List, Dict
from datetime import datetime
from groq import Groq
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from tools.db import execute_query, execute_update


def check_gmail_for_replies(user_id: str) -> Dict:
    """
    Monitor Gmail inbox for replies from companies where user applied.

    Returns:
        {
            "user_id": str,
            "checked_at": datetime,
            "emails_found": int,
            "statuses_updated": int,
            "emails": [{ "application_id", "company", "status", "subject", "snippet" }]
        }
    """
    result = {
        "user_id": user_id,
        "checked_at": datetime.utcnow(),
        "emails_found": 0,
        "statuses_updated": 0,
        "emails": [],
        "error": None
    }

    try:
        print(f"[EMAIL MONITOR] Checking Gmail for user {user_id}", flush=True)

        # Get Gmail tokens for user
        gmail_result = execute_query(
            "SELECT access_token, refresh_token FROM gmail_tokens WHERE user_id = %s",
            (user_id,)
        )

        if not gmail_result:
            msg = f"No Gmail tokens found for user {user_id}"
            print(f"[EMAIL MONITOR] {msg}", flush=True)
            result["error"] = msg
            return result

        gmail_tokens = gmail_result[0]
        access_token = gmail_tokens.get('access_token')
        refresh_token = gmail_tokens.get('refresh_token')

        # Create Credentials object
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GMAIL_CLIENT_ID"),
            client_secret=os.getenv("GMAIL_CLIENT_SECRET")
        )

        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)

        # Get applications for this user where status is "applied"
        apps_result = execute_query(
            """
            SELECT a.id as application_id, a.job_id, a.status, j.company
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.user_id = %s AND a.status = 'applied'
            ORDER BY a.created_at DESC
            """,
            (user_id,)
        )

        if not apps_result:
            print(f"[EMAIL MONITOR] No pending applications for user {user_id}", flush=True)
            return result

        print(f"[EMAIL MONITOR] Found {len(apps_result)} pending applications", flush=True)

        # For each application, search for emails from that company
        for app in apps_result:
            application_id = app.get('application_id')
            job_id = app.get('job_id')
            company = app.get('company')

            try:
                # Search for emails from company domain
                # Try to extract domain from company name or search broadly
                search_query = f'from:{_extract_domain(company)} OR from:{company}'

                print(f"[EMAIL MONITOR] Searching for emails from {company}: {search_query}", flush=True)

                # Search Gmail
                results = service.users().messages().list(
                    userId='me',
                    q=search_query,
                    maxResults=5
                ).execute()

                messages = results.get('messages', [])

                if not messages:
                    print(f"[EMAIL MONITOR] No emails from {company}", flush=True)
                    continue

                print(f"[EMAIL MONITOR] Found {len(messages)} emails from {company}", flush=True)

                # Process each email
                for msg in messages:
                    try:
                        msg_id = msg['id']
                        # Get full message details
                        message = service.users().messages().get(
                            userId='me',
                            id=msg_id,
                            format='full'
                        ).execute()

                        headers = message['payload'].get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
                        snippet = message.get('snippet', '')

                        print(f"[EMAIL MONITOR] Processing email from {company}: {subject[:50]}", flush=True)

                        # Classify email using LLM
                        status = _classify_email_with_llm(subject, snippet, company)

                        if status and status in ['interview', 'offer', 'rejected', 'follow_up']:
                            # Update application status
                            _update_application_status(application_id, status)
                            result["statuses_updated"] += 1

                            email_info = {
                                "application_id": application_id,
                                "company": company,
                                "status": status,
                                "subject": subject,
                                "snippet": snippet[:100]
                            }
                            result["emails"].append(email_info)

                            print(f"[EMAIL MONITOR] Updated {application_id} status to {status}", flush=True)

                    except Exception as e:
                        print(f"[EMAIL MONITOR] Error processing message {msg_id}: {str(e)}", flush=True)
                        _log_error(user_id, application_id, f"Failed to process email: {str(e)}")
                        continue

                result["emails_found"] += len(messages)

            except Exception as e:
                print(f"[EMAIL MONITOR] Error searching emails for {company}: {str(e)}", flush=True)
                _log_error(user_id, application_id, f"Failed to search emails: {str(e)}")
                continue

        print(f"[EMAIL MONITOR] Check complete for user {user_id}: "
              f"found={result['emails_found']}, updated={result['statuses_updated']}", flush=True)

        return result

    except Exception as e:
        print(f"[EMAIL MONITOR] FATAL ERROR for user {user_id}: {type(e).__name__}: {str(e)}", flush=True)
        result["error"] = str(e)
        _log_error(user_id, None, f"Email monitor error: {str(e)}")
        return result


def _extract_domain(company: str) -> str:
    """
    Extract probable domain from company name.

    Example: "Google Inc" -> "google.com"
    """
    # Simple heuristic: convert company name to lowercase, remove spaces/special chars
    domain = company.lower().split()[0]
    # Remove common suffixes
    for suffix in [' inc', ' corp', ' ltd', ' llc', ' plc', ' ag', ' gmbh']:
        domain = domain.replace(suffix, '')
    return f"{domain.replace(' ', '')}.com"


def _classify_email_with_llm(subject: str, snippet: str, company: str) -> Optional[str]:
    """
    Classify email status using LLM.

    Returns: "interview" | "offer" | "rejected" | "follow_up" | None
    """
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""You are an email classifier. Analyze this email and classify it into ONE category.

Email from: {company}
Subject: {subject}
Snippet: {snippet}

Classify this email into EXACTLY ONE of these categories:
- "interview" → if it's about scheduling an interview, call, meeting, or next steps for an interview
- "offer" → if it's a job offer or acceptance
- "rejected" → if it's a rejection or they're not moving forward
- "follow_up" → any other reply (not decision-making)

Respond with ONLY the category name, nothing else."""

        response = client.messages.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10
        )

        status = response.content[0].text.strip().lower()

        # Validate response
        if status in ['interview', 'offer', 'rejected', 'follow_up']:
            print(f"[EMAIL CLASSIFY] '{subject[:40]}' → {status}", flush=True)
            return status
        else:
            print(f"[EMAIL CLASSIFY] Invalid response: {status}", flush=True)
            return None

    except Exception as e:
        print(f"[EMAIL CLASSIFY] ERROR: {type(e).__name__}: {str(e)}", flush=True)
        return None


def _update_application_status(application_id: str, status: str):
    """
    Update application status in database.

    Also updates updated_at timestamp.
    """
    try:
        execute_update(
            """
            UPDATE applications
            SET status = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (status, application_id)
        )
        print(f"[EMAIL MONITOR] Updated application {application_id} to status {status}", flush=True)
    except Exception as e:
        print(f"[EMAIL MONITOR] Error updating application {application_id}: {str(e)}", flush=True)
        raise


def _log_error(user_id: str, application_id: Optional[str], error_msg: str):
    """
    Log error to agent_logs table.
    """
    try:
        execute_update(
            """
            INSERT INTO agent_logs (user_id, application_id, agent, status, details)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, application_id, "email_monitor", "error", error_msg)
        )
    except Exception as e:
        print(f"[EMAIL MONITOR] Failed to log error: {str(e)}", flush=True)
