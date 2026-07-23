"""Update job record with parsed fields and set status to 'parsed'. Validates and logs results."""

import json
from tools.db import execute_update
from tools.logger import log_agent_run


def _extract_country_code(location_str):
    """Extract 2-letter country code from location string using LLM (called once during parsing)."""
    if not location_str:
        return None

    location_lower = location_str.lower().strip()

    # Quick check for remote/non-location strings
    if location_lower in ("remote", "flexible", "hybrid", "on-site", "unknown", "n/a", "not specified", ""):
        return None

    try:
        from tools.llm import call_llm

        prompt = f"""Extract the 2-letter country code from this location string.

Location: {location_str}

Rules:
- Return ONLY the 2-letter ISO country code (e.g., "us", "mx", "de", "jp", "br")
- Handle any language: English, Spanish, German, Portuguese, French, etc.
- Recognize country names and city names
- Examples: "Ciudad de Mexico, MX" → "mx", "Berlin, Germany" → "de"
- If location is remote/flexible/unknown, return "none"

Country code (2 letters only):"""

        response = call_llm(prompt).strip().lower()

        # Validate it's a 2-letter code or "none"
        if response == "none":
            return None
        elif len(response) == 2 and response.isalpha():
            return response
        else:
            print(f"[UPDATE_JOB] Invalid country code response '{response}' for location '{location_str}', skipping", flush=True)
            return None

    except Exception as e:
        print(f"[UPDATE_JOB] Warning - LLM error extracting country for '{location_str}': {str(e)}", flush=True)
        return None


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

        # Extract country code from location (done once during parsing, not on every request)
        location = parsed_fields.get('location')
        country_code = None
        if location:
            country_code = _extract_country_code(location)
            if country_code:
                print(f"[UPDATE_JOB] Extracted country code '{country_code}' from location '{location}'", flush=True)

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
            country_code,
            str(job_id),
            str(user_id)
        )

        query = """UPDATE jobs SET title=%s, company=%s, location=%s, modality=%s,
                   salary_min=%s, salary_max=%s, required_skills=%s, nice_to_have_skills=%s,
                   experience_level=%s, experience_years_min=%s, responsibilities=%s,
                   country_code=%s, status='parsed' WHERE id=%s AND user_id=%s"""

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
