"""Update job record with parsed fields and set status to 'parsed'. Validates and logs results."""

import json
from tools.db import execute_update
from tools.logger import log_agent_run


def update_job(job_id, user_id, parsed_fields):
    """Update job with parsed fields. Validates title and modality, sets status='parsed'."""
    try:
        # Validate critical fields
        if not parsed_fields.get('title'):
            raise Exception("title is required and cannot be empty")

        modality = parsed_fields.get('modality', 'unknown')
        if modality not in {'remote', 'hybrid', 'on-site', 'unknown'}:
            raise Exception(f"Invalid modality: {modality}")

        # Validate and sanitize numeric fields
        salary_min = parsed_fields.get('salary_min')
        salary_max = parsed_fields.get('salary_max')
        experience_years_min = parsed_fields.get('experience_years_min')

        # Ensure numeric fields are actually numeric
        if salary_min is not None:
            try:
                salary_min = int(salary_min) if salary_min else None
            except (ValueError, TypeError):
                print(f"[UPDATE_JOB WARNING] salary_min is not numeric: {salary_min}, setting to NULL", flush=True)
                salary_min = None

        if salary_max is not None:
            try:
                salary_max = int(salary_max) if salary_max else None
            except (ValueError, TypeError):
                print(f"[UPDATE_JOB WARNING] salary_max is not numeric: {salary_max}, setting to NULL", flush=True)
                salary_max = None

        if experience_years_min is not None:
            try:
                experience_years_min = int(experience_years_min) if experience_years_min else None
            except (ValueError, TypeError):
                print(f"[UPDATE_JOB WARNING] experience_years_min is not numeric: {experience_years_min}, setting to NULL", flush=True)
                experience_years_min = None

        # Build params tuple with validated values
        params = (
            parsed_fields.get('title'),
            parsed_fields.get('company'),
            parsed_fields.get('location'),
            parsed_fields.get('modality', 'unknown'),
            salary_min,
            salary_max,
            json.dumps(parsed_fields.get('required_skills', [])),
            json.dumps(parsed_fields.get('nice_to_have_skills', [])),
            parsed_fields.get('experience_level', 'unknown'),
            experience_years_min,
            json.dumps(parsed_fields.get('responsibilities', [])),
            str(job_id),
            str(user_id)
        )

        query = """UPDATE jobs SET title=%s, company=%s, location=%s, modality=%s,
                   salary_min=%s, salary_max=%s, required_skills=%s, nice_to_have_skills=%s,
                   experience_level=%s, experience_years_min=%s, responsibilities=%s,
                   status='parsed' WHERE id=%s AND user_id=%s"""

        print(f"[UPDATE_JOB] Updating job {job_id} with parsed fields", flush=True)
        rows = execute_update(query, params)

        if rows == 0:
            raise Exception(f"Job {job_id} not found or user mismatch")

        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='job_parsing',
            status='success',
            details={'title': parsed_fields.get('title')}
        )

    except Exception as e:
        print(f"[UPDATE_JOB ERROR] Full error: {str(e)}", flush=True)
        print(f"[UPDATE_JOB ERROR] Data being saved:", flush=True)
        print(f"[UPDATE_JOB ERROR]   title: {parsed_fields.get('title')}", flush=True)
        print(f"[UPDATE_JOB ERROR]   company: {parsed_fields.get('company')}", flush=True)
        print(f"[UPDATE_JOB ERROR]   location: {parsed_fields.get('location')}", flush=True)
        print(f"[UPDATE_JOB ERROR]   salary_min: {parsed_fields.get('salary_min')} (type: {type(parsed_fields.get('salary_min')).__name__})", flush=True)
        print(f"[UPDATE_JOB ERROR]   salary_max: {parsed_fields.get('salary_max')} (type: {type(parsed_fields.get('salary_max')).__name__})", flush=True)
        print(f"[UPDATE_JOB ERROR]   experience_years_min: {parsed_fields.get('experience_years_min')} (type: {type(parsed_fields.get('experience_years_min')).__name__})", flush=True)
        print(f"[UPDATE_JOB ERROR]   required_skills: {parsed_fields.get('required_skills')}", flush=True)
        print(f"[UPDATE_JOB ERROR]   responsibilities: {parsed_fields.get('responsibilities')}", flush=True)

        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='job_parsing',
            status='failed',
            details={'error': str(e)}
        )
        raise Exception(f"Failed to update job: {str(e)}")
