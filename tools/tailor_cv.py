"""
CV Tailoring Tool - Personalizes user's CV for a specific job.

Uses REAL user data from cv_data JSONB in user_profiles.
- Fetches user's real projects
- Selects 3-4 most relevant for the job
- Uses user's real name, skills, and background
- Never invents projects

Saves result to cv_tailored table for retrieval and display.
"""

import json
from tools.db import execute_query, execute_update
from tools.llm import call_llm


def tailor_cv_for_job(user_id: str, job_id: str) -> dict:
    """
    Generate a tailored CV for a specific job using REAL data from cv_data.

    Args:
        user_id: UUID of the user
        job_id: UUID of the job

    Returns:
        dict with keys: summary, highlighted_skills, relevant_projects, tailoring_notes, status

    Raises:
        Exception: If required data is missing or LLM call fails
    """
    try:
        print(f"[CV TAILOR] Tailoring CV for user {user_id}, job {job_id}", flush=True)

        # Fetch cv_data from user_profiles
        cv_result = execute_query(
            """
            SELECT cv_data FROM user_profiles WHERE user_id = %s
            """,
            (user_id,)
        )

        if not cv_result:
            raise Exception(f"User profile not found for user {user_id}")

        cv_data_raw = cv_result[0].get('cv_data') if cv_result else None
        if not cv_data_raw:
            raise Exception(f"CV data not found for user {user_id}. User must upload CV first.")

        # Parse cv_data (handle both dict and string formats)
        cv_data = cv_data_raw
        if isinstance(cv_data, str):
            try:
                cv_data = json.loads(cv_data)
            except json.JSONDecodeError:
                raise Exception(f"CV data is malformed JSON for user {user_id}")
        elif not isinstance(cv_data, dict):
            raise Exception(f"CV data is in invalid format for user {user_id}")

        # Extract user data from cv_data
        user_name = cv_data.get('name', 'Professional')
        user_email = cv_data.get('email', '')
        user_phone = cv_data.get('phone', '')
        user_summary = cv_data.get('summary', '')
        user_skills = cv_data.get('skills', []) or []
        user_projects = cv_data.get('projects', []) or []

        print(f"[CV TAILOR] Loaded CV data for {user_name}", flush=True)
        print(f"[CV TAILOR] Projects: {len(user_projects)} | Skills: {len(user_skills)}", flush=True)

        if not user_projects:
            raise Exception(f"No projects found in CV data for user {user_id}")

        # Fetch job details
        job_result = execute_query(
            """
            SELECT title, company, location, modality,
                   required_skills, nice_to_have_skills, responsibilities, description_raw
            FROM jobs
            WHERE id = %s AND user_id = %s
            """,
            (job_id, user_id)
        )

        if not job_result:
            raise Exception(f"Job not found for job_id {job_id}, user {user_id}")

        job = job_result[0]
        job_title = job.get('title', '')
        job_company = job.get('company', '')
        required_skills = job.get('required_skills', []) or []
        nice_to_have_skills = job.get('nice_to_have_skills', []) or []
        responsibilities = job.get('responsibilities', []) or []

        # Format projects for LLM (include skills each project used)
        projects_formatted = []
        for proj in user_projects:
            if isinstance(proj, dict):
                proj_name = proj.get('name', 'Unknown')
                proj_skills = proj.get('skills', [])
                projects_formatted.append(f"- {proj_name} (Skills: {', '.join(proj_skills) if proj_skills else 'N/A'})")
            else:
                projects_formatted.append(f"- {proj}")

        projects_list = '\n'.join(projects_formatted)

        # Build LLM prompt with REAL data and STRICT instructions
        prompt = f"""You are an expert CV writer specializing in ATS optimization and job match.

USER: {user_name}
Email: {user_email}
Summary: {user_summary}
Technical Skills: {', '.join(user_skills) if user_skills else 'Multiple'}

USER'S REAL PROJECTS (do NOT invent new ones):
{projects_list}

TARGET JOB:
Position: {job_title}
Company: {job_company}
Location: {job.get('location', 'Not specified')}
Required Skills: {', '.join(required_skills) if required_skills else 'N/A'}
Nice-to-Have: {', '.join(nice_to_have_skills) if nice_to_have_skills else 'N/A'}
Key Responsibilities: {', '.join(responsibilities[:2]) if responsibilities else 'N/A'}

TASK:
1. Select the 3-4 MOST RELEVANT projects from the user's real projects list above
2. Use EXACT project names from the list - do NOT invent new projects
3. For each project, explain WHY it demonstrates capability for this specific job
4. Generate a professional summary tailored to this job using the user's real background
5. Highlight 5-8 technical skills from the user's CV that match this job

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "summary": "2-3 sentence professional summary for {job_title} position, based on {user_name}'s real experience",
  "highlighted_skills": ["5-8 skills from the user's technical skills that match this job, in order of relevance"],
  "relevant_projects": [
    {{
      "name": "EXACT project name from the list above - do NOT modify or invent",
      "why_relevant": "Specific explanation of why this project demonstrates capability for this job"
    }}
  ],
  "tailoring_notes": "Brief note on which of {user_name}'s strengths are most relevant to {job_title}"
}}"""

        print(f"[CV TAILOR] Calling LLM to select relevant projects for {job_title}...", flush=True)

        # Call LLM
        response = call_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()

        # Parse response
        tailored_data = json.loads(response)

        # Validate required fields
        if not isinstance(tailored_data.get('highlighted_skills'), list):
            tailored_data['highlighted_skills'] = []
        if not isinstance(tailored_data.get('relevant_projects'), list):
            tailored_data['relevant_projects'] = []

        # Verify projects come from real list
        real_project_names = set()
        for proj in user_projects:
            if isinstance(proj, dict):
                real_project_names.add(proj.get('name', ''))
            else:
                real_project_names.add(str(proj))

        for tailored_proj in tailored_data.get('relevant_projects', []):
            proj_name = tailored_proj.get('name', '')
            if proj_name not in real_project_names:
                print(f"[CV TAILOR] WARNING: Project '{proj_name}' not in real project list", flush=True)

        # Save to database
        print(f"[CV TAILOR] Saving tailored CV to database", flush=True)
        execute_update(
            """
            INSERT INTO cv_tailored (user_id, job_id, summary, highlighted_skills, relevant_projects, tailoring_notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, job_id) DO UPDATE SET
              summary = EXCLUDED.summary,
              highlighted_skills = EXCLUDED.highlighted_skills,
              relevant_projects = EXCLUDED.relevant_projects,
              tailoring_notes = EXCLUDED.tailoring_notes
            """,
            (
                user_id,
                job_id,
                tailored_data.get('summary', ''),
                json.dumps(tailored_data.get('highlighted_skills', [])),
                json.dumps(tailored_data.get('relevant_projects', [])),
                tailored_data.get('tailoring_notes', '')
            )
        )

        print(f"[CV TAILOR] [OK] CV tailored successfully | Projects: {len(tailored_data.get('relevant_projects', []))}", flush=True)

        return {
            "status": "success",
            "summary": tailored_data.get('summary', ''),
            "highlighted_skills": tailored_data.get('highlighted_skills', []),
            "relevant_projects": tailored_data.get('relevant_projects', []),
            "tailoring_notes": tailored_data.get('tailoring_notes', '')
        }

    except json.JSONDecodeError as e:
        print(f"[CV TAILOR] JSON parse error: {str(e)}", flush=True)
        raise Exception(f"Failed to parse LLM response: {str(e)}")
    except Exception as e:
        print(f"[CV TAILOR] ERROR: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise


def get_tailored_cv(user_id: str, job_id: str) -> dict:
    """
    Retrieve a previously tailored CV from the database.

    Args:
        user_id: UUID of the user
        job_id: UUID of the job

    Returns:
        dict with tailored CV data or empty dict if not found
    """
    try:
        result = execute_query(
            """
            SELECT summary, highlighted_skills, relevant_projects, tailoring_notes, created_at
            FROM cv_tailored
            WHERE user_id = %s AND job_id = %s
            """,
            (user_id, job_id)
        )

        if not result:
            return {}

        cv = result[0]
        return {
            "summary": cv.get('summary', ''),
            "highlighted_skills": cv.get('highlighted_skills', []) if isinstance(cv.get('highlighted_skills'), list) else json.loads(cv.get('highlighted_skills', '[]')),
            "relevant_projects": cv.get('relevant_projects', []) if isinstance(cv.get('relevant_projects'), list) else json.loads(cv.get('relevant_projects', '[]')),
            "tailoring_notes": cv.get('tailoring_notes', ''),
            "created_at": cv.get('created_at')
        }

    except Exception as e:
        print(f"[CV TAILOR] Error retrieving tailored CV: {type(e).__name__}: {str(e)}", flush=True)
        return {}
