"""
Cover letter generation tool for job applications.

Generates personalized cover letters based on job description and user CV.
"""

import os
from typing import Optional
from groq import Groq
from tools.db import execute_query, execute_update


def should_generate_cover_letter(job_description: str) -> bool:
    """
    Check if job description mentions cover letter requirement.

    Returns True if cover letter is mentioned, False otherwise.
    """
    if not job_description:
        return False

    keywords = [
        "cover letter",
        "coverletter",
        "cover note",
        "motivation letter",
        "letter of motivation",
        "statement of purpose",
        "accompanying letter"
    ]

    desc_lower = job_description.lower()
    return any(keyword in desc_lower for keyword in keywords)


def generate_cover_letter(user_id: str, job_id: str, job_title: str, company: str, job_description: str) -> Optional[str]:
    """
    Generate a personalized cover letter for a job application.

    Returns:
        Generated cover letter text, or None if generation fails
    """
    try:
        print(f"[COVER_LETTER] Generating for job {job_id}: {company} - {job_title}", flush=True)

        # Get user CV data
        cv_result = execute_query(
            "SELECT cv_data FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not cv_result or not cv_result[0].get('cv_data'):
            print(f"[COVER_LETTER] No CV data found for user {user_id}", flush=True)
            return None

        cv_data = cv_result[0].get('cv_data')
        user_name = cv_data.get('name', 'Applicant')
        user_email = cv_data.get('email', '')
        user_phone = cv_data.get('phone', '')
        user_summary = cv_data.get('summary', '')
        user_skills = cv_data.get('skills', [])

        # Prepare skills text
        skills_text = ", ".join(user_skills[:10]) if user_skills else "technical skills"

        prompt = f"""Generate a professional, personalized cover letter for this job application.

APPLICANT INFO:
Name: {user_name}
Email: {user_email}
Phone: {user_phone}
Summary: {user_summary}
Key Skills: {skills_text}

JOB INFO:
Company: {company}
Position: {job_title}
Job Description:
{job_description[:1500]}

REQUIREMENTS:
- Professional tone, 2-3 paragraphs
- Personalized to the specific job and company
- Highlight 2-3 relevant skills
- Show enthusiasm and cultural fit
- End with call to action
- No placeholders or generic content
- Start with "Dear Hiring Team," (no specific name if unknown)
- Sign with the applicant's name

Generate ONLY the cover letter text, ready to send. No headers, no explanation."""

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        response = client.messages.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600
        )

        cover_letter = response.content[0].text.strip()

        if cover_letter:
            print(f"[COVER_LETTER] Generated {len(cover_letter)} chars for job {job_id}", flush=True)
            return cover_letter
        else:
            print(f"[COVER_LETTER] Failed to generate cover letter", flush=True)
            return None

    except Exception as e:
        print(f"[COVER_LETTER] Error generating cover letter: {type(e).__name__}: {str(e)}", flush=True)
        return None


def save_cover_letter(user_id: str, job_id: str, cover_letter: str) -> bool:
    """
    Save generated cover letter to database.

    Stores in cv_tailored table with cover_letter field.
    """
    try:
        # Check if cv_tailored record exists for this job
        existing = execute_query(
            "SELECT id FROM cv_tailored WHERE user_id = %s AND job_id = %s",
            (user_id, job_id)
        )

        if existing:
            # Update existing record
            execute_update(
                """
                UPDATE cv_tailored
                SET cover_letter = %s, updated_at = NOW()
                WHERE user_id = %s AND job_id = %s
                """,
                (cover_letter, user_id, job_id)
            )
            print(f"[COVER_LETTER] Updated cover letter for job {job_id}", flush=True)
        else:
            # Create new record
            execute_update(
                """
                INSERT INTO cv_tailored (user_id, job_id, cover_letter, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                """,
                (user_id, job_id, cover_letter)
            )
            print(f"[COVER_LETTER] Saved cover letter for job {job_id}", flush=True)

        return True

    except Exception as e:
        print(f"[COVER_LETTER] Error saving cover letter: {str(e)}", flush=True)
        return False


def get_cover_letter(user_id: str, job_id: str) -> Optional[str]:
    """
    Retrieve saved cover letter for a job.

    Returns:
        Cover letter text, or None if not found
    """
    try:
        result = execute_query(
            "SELECT cover_letter FROM cv_tailored WHERE user_id = %s AND job_id = %s",
            (user_id, job_id)
        )

        if result and result[0].get('cover_letter'):
            return result[0].get('cover_letter')

        return None

    except Exception as e:
        print(f"[COVER_LETTER] Error retrieving cover letter: {str(e)}", flush=True)
        return None
