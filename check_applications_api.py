#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

# Get all pending_approval records from DB
pending_apps = execute_query(
    """
    SELECT a.id, a.job_id, a.status, j.title, j.company
    FROM applications a
    LEFT JOIN jobs j ON a.job_id = j.id
    WHERE a.user_id = %s AND a.status = 'pending_approval'
    ORDER BY a.created_at DESC
    """,
    (user_id,)
)

print(f"Total pending_approval in DB: {len(pending_apps)}")
print("\nAll pending applications:")
for i, app in enumerate(pending_apps, 1):
    print(f"{i}. ID: {app['id']}, Job: {app.get('title', 'N/A')} ({app.get('company', 'N/A')})")

# Now check what the applications endpoint query would return
print("\n" + "=" * 70)
print("Via API endpoint query (with limit=100):")
print("=" * 70)

api_query_result = execute_query(
    """
    SELECT a.id, a.job_id, a.status, j.title, j.company
    FROM applications a
    LEFT JOIN jobs j ON a.job_id = j.id
    WHERE a.user_id = %s
    ORDER BY CASE WHEN a.status = 'pending_approval' THEN 0 ELSE 1 END, a.created_at DESC
    LIMIT 100
    """,
    (user_id,)
)

pending_from_api = [a for a in api_query_result if a.get('status') == 'pending_approval']
print(f"Pending applications returned by API query: {len(pending_from_api)}")

print("\nPending applications from API query:")
for i, app in enumerate(pending_from_api, 1):
    print(f"{i}. ID: {app['id']}, Job: {app.get('title', 'N/A')} ({app.get('company', 'N/A')})")

# Check if any job_ids are duplicated
print("\n" + "=" * 70)
print("Checking for duplicates by job_id:")
print("=" * 70)

job_ids = [a['job_id'] for a in pending_apps]
unique_job_ids = set(job_ids)

if len(job_ids) != len(unique_job_ids):
    print(f"⚠ Found duplicate job_ids: {len(job_ids)} records but only {len(unique_job_ids)} unique jobs")
    # Show which job_ids have multiple applications
    from collections import Counter
    counts = Counter(job_ids)
    for job_id, count in counts.items():
        if count > 1:
            print(f"  Job {job_id}: {count} applications")
else:
    print(f"✓ No duplicates: {len(unique_job_ids)} unique job_ids")
