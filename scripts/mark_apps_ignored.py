#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from tools.db import execute_query, execute_update

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

# Get jobs matching the criteria
jobs = execute_query(
    """
    SELECT id, title FROM jobs
    WHERE user_id = %s
    AND (title ILIKE %s OR title ILIKE %s)
    """,
    (user_id, '%data engineering%', '%project engineer%')
)

print(f"Found {len(jobs)} jobs to mark as ignored:")
for job in jobs:
    print(f"  - {job['id']}: {job['title']}")

# Mark applications as ignored
job_ids = [job['id'] for job in jobs]
if job_ids:
    placeholders = ','.join(['%s'] * len(job_ids))
    execute_update(
        f"""
        UPDATE applications
        SET status='ignored'
        WHERE user_id = %s AND job_id IN ({placeholders})
        """,
        (user_id, *job_ids)
    )
    print(f"\n✓ Marked {len(job_ids)} applications as ignored")
else:
    print("\nNo jobs matched the criteria")
