"""
Deduplicate and save discovered jobs to the database.

Checks if each job URL already exists for the user, then inserts only new jobs
with status='discovered'. Returns counts for logging.

Example usage:
  from tools.save_jobs import save_jobs
  result = save_jobs(user_id='550e8400-...', jobs=jobs_list)
  # Returns: {'jobs_found': 50, 'jobs_saved': 45, 'duplicates_skipped': 5}
"""

import json
from tools.db import execute_query, execute_update
from tools.logger import log_agent_run


def save_jobs(user_id, jobs):
    """Deduplicate and save discovered jobs. Returns {jobs_found, jobs_saved, duplicates_skipped}."""
    if not jobs:
        return {
            'jobs_found': 0,
            'jobs_saved': 0,
            'duplicates_skipped': 0,
        }

    jobs_found = len(jobs)
    jobs_saved = 0
    duplicates_skipped = 0

    try:
        # Get all existing job URLs for this user
        existing_urls_result = execute_query(
            'SELECT url FROM jobs WHERE user_id = %s',
            (str(user_id),)
        )
        existing_urls = {row['url'] for row in existing_urls_result}

        # Insert only new jobs
        for job in jobs:
            if job.get('url') in existing_urls:
                duplicates_skipped += 1
                continue

            try:
                params = (str(user_id), job.get('source', ''), job.get('url', ''),
                          job.get('title', ''), job.get('title', ''), job.get('company', ''),
                          job.get('location', ''), job.get('modality', 'unknown'),
                          job.get('salary_min'), job.get('salary_max'), json.dumps([]),
                          json.dumps([]), job.get('description_raw', ''), 'discovered')
                query = """INSERT INTO jobs (user_id, source, url, title_raw, title, company,
                            location, modality, salary_min, salary_max, required_skills,
                            nice_to_have_skills, description_raw, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())"""
                execute_update(query, params)
                jobs_saved += 1
                existing_urls.add(job.get('url'))
            except Exception as e:
                raise Exception(f"Failed to insert {job.get('url', 'unknown')}: {str(e)}")

        # Log the result
        log_agent_run(
            user_id=user_id,
            agent='job_discovery',
            status='success',
            details={
                'jobs_found': jobs_found,
                'jobs_saved': jobs_saved,
                'duplicates_skipped': duplicates_skipped,
            },
        )

        return {
            'jobs_found': jobs_found,
            'jobs_saved': jobs_saved,
            'duplicates_skipped': duplicates_skipped,
        }

    except Exception as e:
        # Log the error
        log_agent_run(
            user_id=user_id,
            agent='job_discovery',
            status='failed',
            details={'error': str(e), 'jobs_found': jobs_found},
        )
        raise Exception(f"save_jobs failed: {str(e)}")
