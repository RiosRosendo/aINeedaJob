#!/usr/bin/env python3
"""
Interview Prep Agent: Generates interview prep materials when interview detected.

Responsibilities:
1. Detect when email_monitor marks an application as 'interview'
2. Fetch job description, company info, and user profile
3. Use Groq LLM to generate:
   - 10 likely interview questions for this role
   - Key talking points about user's relevant experience
   - Company research summary
4. Save to interview_prep table
5. Provide via API endpoint: GET /api/applications/{id}/interview-prep
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.db import execute_query, execute_update
from tools.llm import call_llm
from tools.logger import log_agent_run


def generate_interview_prep(user_id: str, job_id: str, application_id: str) -> dict:
    """Generate interview preparation materials for a job."""
    print(f"[INTERVIEW_PREP] Generating prep for application {application_id}")

    try:
        # Fetch job details
        job_result = execute_query(
            "SELECT title, company, description_raw, required_skills FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

        if not job_result:
            raise Exception("Job not found")

        job = job_result[0]
        job_title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        description = job.get("description_raw", "")
        required_skills = job.get("required_skills", [])

        # Fetch user profile
        profile_result = execute_query(
            "SELECT cv_data, target_roles, tech_stack FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not profile_result:
            raise Exception("User profile not found")

        profile = profile_result[0]
        cv_data = profile.get("cv_data", {})
        user_tech_stack = profile.get("tech_stack", [])

        # Parse JSON fields
        if isinstance(cv_data, str):
            cv_data = json.loads(cv_data) if cv_data else {}
        if isinstance(required_skills, str):
            required_skills = json.loads(required_skills) if required_skills else []
        if isinstance(user_tech_stack, str):
            user_tech_stack = json.loads(user_tech_stack) if user_tech_stack else []

        # Generate interview questions
        questions = _generate_interview_questions(
            job_title, company, description, required_skills
        )

        # Generate talking points
        talking_points = _generate_talking_points(
            cv_data, required_skills, user_tech_stack, job_title
        )

        # Generate company research
        company_research = _generate_company_research(company, job_title)

        # Create interview prep record
        prep_data = {
            "application_id": application_id,
            "job_id": job_id,
            "user_id": user_id,
            "questions": questions,
            "talking_points": talking_points,
            "company_research": company_research,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Save to database
        try:
            result = execute_query(
                "SELECT id FROM interview_prep WHERE application_id = %s",
                (application_id,)
            )

            if result:
                # Update existing
                execute_update(
                    """UPDATE interview_prep
                       SET questions = %s, talking_points = %s, company_research = %s,
                           updated_at = NOW()
                       WHERE application_id = %s""",
                    (
                        json.dumps(questions),
                        json.dumps(talking_points),
                        company_research,
                        application_id
                    )
                )
                print("[INTERVIEW_PREP] Updated existing prep record")
            else:
                # Create new
                execute_update(
                    """INSERT INTO interview_prep
                       (application_id, job_id, user_id, questions, talking_points, company_research, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                    (
                        application_id,
                        job_id,
                        user_id,
                        json.dumps(questions),
                        json.dumps(talking_points),
                        company_research
                    )
                )
                print("[INTERVIEW_PREP] Created new prep record")

        except Exception as db_err:
            print(f"[INTERVIEW_PREP] Warning - could not save to DB: {str(db_err)}")
            # Continue even if DB save fails, return the prep data

        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='interview_prep',
            status='success',
            details={
                'company': company,
                'job_title': job_title,
                'questions_count': len(questions),
                'talking_points_count': len(talking_points)
            }
        )

        print(f"[INTERVIEW_PREP] Generated prep for {job_title} at {company}")
        return prep_data

    except Exception as e:
        print(f"[INTERVIEW_PREP] Error: {str(e)}")
        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='interview_prep',
            status='failed',
            details={'error': str(e)}
        )
        raise


def _generate_interview_questions(job_title: str, company: str, description: str, required_skills: list) -> list:
    """Generate 10 likely interview questions using Groq LLM."""
    skills_str = ", ".join(required_skills[:10]) if required_skills else "relevant technologies"

    prompt = f"""Generate 10 specific interview questions for a {job_title} position at {company}.

Job Requirements: {skills_str}
Job Description (excerpt): {description[:800]}

Requirements:
- Questions should be role-specific, not generic
- Mix of technical, behavioral, and company-specific questions
- Include questions about specific technologies mentioned
- Questions should be challenging but fair
- Return as a JSON array of strings only, no other text

Format: ["Question 1?", "Question 2?", ...]"""

    try:
        response = call_llm(prompt)
        response = response.strip()

        # Try to parse JSON
        if response.startswith("["):
            questions = json.loads(response)
        else:
            # Fallback: split by numbering
            lines = response.split("\n")
            questions = [
                line.replace(f"{i+1}.", "").strip()
                for i, line in enumerate(lines)
                if line.strip()
            ][:10]

        return questions if questions else ["Tell us about your experience with this technology."]

    except Exception as e:
        print(f"[INTERVIEW_PREP] Error generating questions: {str(e)}")
        return ["Tell us about your relevant experience.", "What interests you about this role?"]


def _generate_talking_points(cv_data: dict, required_skills: list, user_tech_stack: list, job_title: str) -> list:
    """Generate talking points using user's experience and job requirements."""
    user_skills_str = ", ".join(user_tech_stack[:10]) if user_tech_stack else "various technologies"
    user_name = cv_data.get("name", "candidate") if cv_data else "candidate"
    user_experience = cv_data.get("experience_summary", "") if cv_data else ""

    prompt = f"""Generate 5-7 key talking points for {user_name} interviewing for a {job_title} role.

User's Tech Stack: {user_skills_str}
User's Experience: {user_experience[:300] if user_experience else "Not specified"}
Required Skills: {", ".join(required_skills[:10]) if required_skills else "various"}

Requirements:
- Talking points should highlight relevant experience
- Focus on matching user skills to job requirements
- Include specific examples or achievements if known
- Points should be memorable and confident
- Return as JSON array of strings only

Format: ["Point 1", "Point 2", ...]"""

    try:
        response = call_llm(prompt)
        response = response.strip()

        if response.startswith("["):
            points = json.loads(response)
        else:
            points = [p.strip() for p in response.split("\n") if p.strip()][:7]

        return points if points else ["I have strong experience with the required technologies."]

    except Exception as e:
        print(f"[INTERVIEW_PREP] Error generating talking points: {str(e)}")
        return ["Strong technical background", "Experience with relevant technologies"]


def _generate_company_research(company: str, job_title: str) -> str:
    """Generate company research summary using Groq LLM."""
    prompt = f"""Write a brief company research summary for interview preparation.

Company: {company}
Position: {job_title}

Requirements:
- 2-3 sentences max
- Focus on what makes this company interesting
- Mention relevant industry/market positioning if known
- Include potential questions about company direction
- Make it interview-ready (what you should know)"""

    try:
        research = call_llm(prompt)
        return research.strip()
    except Exception as e:
        print(f"[INTERVIEW_PREP] Error generating research: {str(e)}")
        return f"Research the company {company} and their recent news before the interview."


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python interview_prep_agent.py <user_id> <job_id> <application_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    job_id = sys.argv[2]
    application_id = sys.argv[3]

    try:
        result = generate_interview_prep(user_id, job_id, application_id)
        print(f"[INTERVIEW_PREP] Success: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"[INTERVIEW_PREP] Failed: {str(e)}")
        sys.exit(1)
