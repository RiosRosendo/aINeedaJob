#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query, execute_update

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("CRITICAL FIX 4: CLEAN UP IRRELEVANT JOBS IN APPROVALS")
print("=" * 70)

# Find irrelevant jobs that are in approvals
irrelevant_keywords = [
    'Controls Engineer',
    'Process Engineer',
    'Defense Technology',
    'Manufacturing',
    'Quality Assurance',
    'Supply Chain',
]

print("\n[CLEANUP] Checking for irrelevant jobs in pending approvals...")

# Get all pending_approval applications
pending_apps = execute_query(
    """
    SELECT a.id, a.job_id, j.title, j.company
    FROM applications a
    JOIN jobs j ON a.job_id = j.id
    WHERE a.user_id = %s AND a.status = 'pending_approval'
    ORDER BY j.title
    """,
    (user_id,)
)

print(f"Total pending approvals: {len(pending_apps)}")

irrelevant_count = 0
to_cleanup = []

for app in pending_apps:
    title = (app['title'] or '').lower()
    is_irrelevant = False

    for keyword in irrelevant_keywords:
        if keyword.lower() in title:
            is_irrelevant = True
            break

    if is_irrelevant:
        print(f"  ✓ Found irrelevant: {app['title'][:50]}")
        to_cleanup.append((app['job_id'], app['id']))
        irrelevant_count += 1

if to_cleanup:
    print(f"\n[CLEANUP] Marking {irrelevant_count} irrelevant jobs as ignored...")

    for job_id, app_id in to_cleanup:
        try:
            # Update application status
            execute_update(
                "UPDATE applications SET status = 'ignored' WHERE id = %s",
                (app_id,)
            )
        except Exception as e:
            print(f"  Error updating app {app_id}: {str(e)}")

    print(f"✓ Cleaned up {irrelevant_count} irrelevant job approvals")
else:
    print("✓ No irrelevant jobs found in pending approvals")

# Verify final count
final_pending = execute_query(
    "SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s AND status = 'pending_approval'",
    (user_id,)
)

print(f"\nFinal pending approvals: {final_pending[0]['cnt']}")
print("\n" + "=" * 70)
print("CLEANUP COMPLETE")
print("=" * 70)
