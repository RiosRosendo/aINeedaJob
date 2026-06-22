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

        params = (parsed_fields.get('title'), parsed_fields.get('company'),
                  parsed_fields.get('location'), parsed_fields.get('modality', 'unknown'),
                  parsed_fields.get('salary_min'), parsed_fields.get('salary_max'),
                  json.dumps(parsed_fields.get('required_skills', [])),
                  json.dumps(parsed_fields.get('nice_to_have_skills', [])),
                  parsed_fields.get('experience_level', 'unknown'),
                  parsed_fields.get('experience_years_min'),
                  json.dumps(parsed_fields.get('responsibilities', [])),
                  str(job_id), str(user_id))
        query = """UPDATE jobs SET title=%s, company=%s, location=%s, modality=%s,
                   salary_min=%s, salary_max=%s, required_skills=%s, nice_to_have_skills=%s,
                   experience_level=%s, experience_years_min=%s, responsibilities=%s,
                   status='parsed' WHERE id=%s AND user_id=%s"""

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
        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='job_parsing',
            status='failed',
            details={'error': str(e)}
        )
        raise Exception(f"Failed to update job: {str(e)}")
