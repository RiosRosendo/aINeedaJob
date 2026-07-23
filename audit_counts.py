#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query, execute_update

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("DATA CONSISTENCY AUDIT")
print("=" * 70)

# ===== COUNT AUDIT =====
print("\n[AUDIT 1] Job Count Consistency")
print("-" * 70)

# True count: all non-expired jobs
true_count = execute_query(
    "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND expires_at IS NULL",
    (user_id,)
)
true_jobs = true_count[0]['cnt']
print(f"True count (all non-expired): {true_jobs}")

# Scored jobs (currently in dashboard)
scored = execute_query(
    """SELECT COUNT(*) as cnt FROM jobs j
       INNER JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
       WHERE j.user_id = %s AND j.expires_at IS NULL""",
    (user_id, user_id)
)
scored_jobs = scored[0]['cnt']
print(f"Scored jobs (dashboard currently shows): {scored_jobs}")

# ===== APPROVALS AUDIT =====
print("\n[AUDIT 2] Approvals Count")
print("-" * 70)

pending = execute_query(
    "SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s AND status = 'pending_approval'",
    (user_id,)
)
pending_apps = pending[0]['cnt']
print(f"Pending approvals (real count): {pending_apps}")

applied = execute_query(
    "SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s AND status = 'applied'",
    (user_id,)
)
applied_apps = applied[0]['cnt']
print(f"Applied (for reference): {applied_apps}")

# ===== TITLE CLEANUP =====
print("\n[AUDIT 3] Bad Job Titles")
print("-" * 70)

bad_titles = execute_query(
    """SELECT id, title, company FROM jobs
       WHERE user_id = %s AND title = 'Mid Level Opportunity'""",
    (user_id,)
)

if bad_titles:
    for job in bad_titles:
        print(f"Found: '{job['title']}' from {job['company']}")
        if 'HII' in job['company'] or 'Mission Technologies' in job['company']:
            print(f"  → Cleaning to 'Senior Embedded Systems Engineer'")
            execute_update(
                """UPDATE jobs SET title = 'Senior Embedded Systems Engineer'
                   WHERE id = %s""",
                (job['id'],)
            )
else:
    print("No bad titles found")

# ===== SUMMARY =====
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)
print(f"\nJob Counts (should all match {true_jobs}):")
print(f"  ✓ True count (non-expired): {true_jobs}")
print(f"  ⚠ Scored (dashboard shows): {scored_jobs}")
print(f"  Difference: {true_jobs - scored_jobs} unscored jobs")

print(f"\nApprovals:")
print(f"  ✓ Real count: {pending_apps}")
print(f"  Note: Dashboard shows 4, Weekly Summary shows 11")

print("\n" + "=" * 70)
print("NEXT: Fix queries to use consistent counts")
print("=" * 70)
