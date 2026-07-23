#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

# Check pending approvals
pending = execute_query(
    "SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s AND status = 'pending_approval'",
    (user_id,)
)

print(f'Pending approvals in DB: {pending[0]["cnt"]}')

# Show all statuses
all_statuses = execute_query(
    "SELECT status, COUNT(*) as cnt FROM applications WHERE user_id = %s GROUP BY status ORDER BY cnt DESC",
    (user_id,)
)

print(f'\nAll application statuses:')
for row in all_statuses:
    print(f'  {row["status"]}: {row["cnt"]}')

# If not 11, show the pending ones
if pending[0]["cnt"] != 11:
    print("\nPending approval applications:")
    pend_apps = execute_query(
        "SELECT id, job_id FROM applications WHERE user_id = %s AND status = 'pending_approval' LIMIT 20",
        (user_id,)
    )
    for app in pend_apps:
        print(f"  {app['id']}: job {app['job_id']}")
