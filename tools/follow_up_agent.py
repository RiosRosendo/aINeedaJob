#!/usr/bin/env python3
"""
Follow-up Agent: Sends follow-up emails to companies after 7+ days without response.

Process:
1. Find all applications with status='applied' created 7+ days ago
2. Check if email response received from company (via Gmail)
3. If no response: generate follow-up email, send via Gmail API, update status to 'follow_up_sent'
4. Log all actions to agent_logs
"""

import sys
import os
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db import execute_query, execute_update
from tools.llm import call_llm
from tools.logger import log_agent_run
from tools.gmail_client import get_gmail_client, check_email_from_company, send_email


def run_follow_up_agent():
    """Find old applications and send follow-up emails."""
    print("[FOLLOW_UP] Starting follow-up agent...")

    try:
        # Find all applications with status='applied' created 7+ days ago
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        print(f"[FOLLOW_UP] Looking for applications older than {cutoff_date}")

        applications = execute_query(
            """
            SELECT a.id, a.job_id, a.user_id, a.created_at,
                   j.title, j.company, j.description_raw, j.url,
                   up.cv_data
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN user_profiles up ON a.user_id = up.user_id
            WHERE a.status = 'applied'
              AND a.created_at < %s
              AND (a.follow_up_sent_at IS NULL OR a.follow_up_attempt_count < 2)
            ORDER BY a.created_at ASC
            LIMIT 20
            """,
            (cutoff_date,)
        )

        if not applications:
            print("[FOLLOW_UP] No applications need follow-up")
            return {"total_processed": 0, "emails_sent": 0, "errors": 0}

        print(f"[FOLLOW_UP] Found {len(applications)} applications needing follow-up")

        total_processed = 0
        emails_sent = 0
        errors = 0

        for app in applications:
            app_id = app.get("id")
            user_id = app.get("user_id")
            job_id = app.get("job_id")
            company = app.get("company", "Unknown")
            job_title = app.get("title", "Unknown")
            job_url = app.get("url")
            cv_data = app.get("cv_data")

            print(f"\n[FOLLOW_UP] Processing application {app_id} for {job_title} at {company}")

            try:
                # Parse cv_data to get candidate name
                candidate_name = "there"
                if cv_data:
                    try:
                        if isinstance(cv_data, str):
                            cv_data = json.loads(cv_data)
                        candidate_name = cv_data.get("name", "there")
                    except:
                        pass

                # Check if email received from company
                gmail_client = get_gmail_client(user_id)
                if not gmail_client:
                    print(f"[FOLLOW_UP] No Gmail client for user {user_id}, skipping")
                    errors += 1
                    continue

                has_response = check_email_from_company(gmail_client, company, job_title)
                if has_response:
                    print(f"[FOLLOW_UP] Email from {company} already received, skipping")
                    # Mark as responded
                    execute_update(
                        "UPDATE applications SET status = %s, updated_at = NOW() WHERE id = %s",
                        ("in_review", app_id)
                    )
                    total_processed += 1
                    continue

                # Generate follow-up email
                follow_up_text = _generate_follow_up_email(
                    candidate_name, job_title, company
                )

                if not follow_up_text:
                    print(f"[FOLLOW_UP] Failed to generate follow-up email")
                    errors += 1
                    continue

                # Send email via Gmail API
                to_email = _get_company_email(company)
                if not to_email:
                    print(f"[FOLLOW_UP] Could not find company email for {company}")
                    errors += 1
                    continue

                success = send_email(gmail_client, to_email, follow_up_text, job_title)
                if not success:
                    print(f"[FOLLOW_UP] Failed to send follow-up email")
                    errors += 1
                    continue

                # Update application status
                attempt_count = 1
                execute_update(
                    """UPDATE applications
                       SET status = %s, follow_up_sent_at = NOW(),
                           follow_up_attempt_count = %s, updated_at = NOW()
                       WHERE id = %s""",
                    ("follow_up_sent", attempt_count, app_id)
                )

                log_agent_run(
                    user_id=user_id,
                    job_id=job_id,
                    agent='follow_up',
                    status='success',
                    details={
                        'company': company,
                        'job_title': job_title,
                        'recipient': to_email
                    }
                )

                print(f"[FOLLOW_UP] Sent follow-up email to {to_email}")
                emails_sent += 1
                total_processed += 1

            except Exception as e:
                print(f"[FOLLOW_UP] Error processing application {app_id}: {str(e)}")
                log_agent_run(
                    user_id=user_id,
                    job_id=job_id,
                    agent='follow_up',
                    status='failed',
                    details={'error': str(e)}
                )
                errors += 1

        result = {
            "total_processed": total_processed,
            "emails_sent": emails_sent,
            "errors": errors
        }

        print(f"\n[FOLLOW_UP] Summary: {result}")
        return result

    except Exception as e:
        print(f"[FOLLOW_UP] Fatal error: {str(e)}")
        return {"total_processed": 0, "emails_sent": 0, "errors": 1}


def _generate_follow_up_email(candidate_name: str, job_title: str, company: str) -> str:
    """Generate a follow-up email using Groq LLM."""
    prompt = f"""Generate a professional follow-up email for a job application.

Candidate Name: {candidate_name}
Job Title: {job_title}
Company: {company}

Requirements:
- Keep it brief (2-3 paragraphs max)
- Professional and friendly tone
- Show genuine interest in the role
- Mention willingness to provide additional information
- Include a clear call to action

Return ONLY the email body, no subject line."""

    try:
        email_text = call_llm(prompt)
        return email_text.strip()
    except Exception as e:
        print(f"[FOLLOW_UP] LLM error generating email: {str(e)}")
        return None


def _get_company_email(company: str) -> str:
    """Try to find company email or hiring contact. This is a simplified version."""
    # In production, this would use a company database or email lookup service
    # For now, return None to indicate we can't find the email
    # The actual implementation would integrate with Clearbit or similar services

    # Check if we have cached company emails in database
    try:
        result = execute_query(
            "SELECT contact_email FROM company_emails WHERE company_name ILIKE %s LIMIT 1",
            (f"%{company}%",)
        )
        if result:
            return result[0].get("contact_email")
    except:
        pass

    return None


if __name__ == "__main__":
    result = run_follow_up_agent()
    sys.exit(0 if result["errors"] == 0 else 1)
