#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query, execute_update

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("DASHBOARD ISSUE FIXES")
print("=" * 70)

# ===== ISSUE 3: Mark bad jobs as ignored =====
print("\n[FIX 1] Marking irrelevant jobs as ignored...")
print("-" * 70)

bad_jobs = [
    {"title": "Unknown", "company": "Anduril"},
    {"title": "Embedded Systems Engineer", "company": None},
    {"title": "Jr Project Engineer", "company": "Adecco"},
    {"title": "Data Engineering organization", "company": "General Motors"},
]

marked = 0
for job_spec in bad_jobs:
    if job_spec["company"]:
        jobs = execute_query(
            "SELECT id FROM jobs WHERE user_id = %s AND title = %s AND company = %s LIMIT 1",
            (user_id, job_spec["title"], job_spec["company"])
        )
    else:
        jobs = execute_query(
            "SELECT id FROM jobs WHERE user_id = %s AND title = %s LIMIT 1",
            (user_id, job_spec["title"])
        )

    if jobs:
        job_id = jobs[0]['id']
        # Mark in fit_scores as ignored (0 score, ignored decision)
        execute_update(
            "UPDATE fit_scores SET score = 0, decision = 'ignore' WHERE job_id = %s",
            (job_id,)
        )
        print(f"  ✓ Marked '{job_spec['title']}' as ignored")
        marked += 1
    else:
        print(f"  ⚠ Not found: '{job_spec['title']}'")

print(f"\nTotal marked: {marked}")

# ===== VERIFY: Check current state =====
print("\n[VERIFY] Current state after fixes...")
print("-" * 70)

# Total jobs
total = execute_query(
    "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND expires_at IS NULL",
    (user_id,)
)
print(f"Total jobs (for 'Jobs Found'): {total[0]['cnt']}")

# Jobs with fit_score >= 60
above_60 = execute_query(
    "SELECT COUNT(*) as cnt FROM fit_scores WHERE user_id = %s AND score >= 60",
    (user_id,)
)
print(f"Jobs with score >= 60 (for Queue): {above_60[0]['cnt']}")

# Pending approvals
pending = execute_query(
    "SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s AND status = 'pending_approval'",
    (user_id,)
)
print(f"Pending approvals (for Weekly Summary): {pending[0]['cnt']}")

# ===== MEXICO MAP CHECK =====
print("\n[CHECK] Mexico on world map...")
print("-" * 70)

mexico_jobs = execute_query(
    """
    WITH country_mapping AS (
      SELECT id, COALESCE(search_country,
        CASE
          WHEN location ILIKE '%%Mexico%%' OR location = 'MX' THEN 'mx'
          ELSE NULL
        END
      ) as country_code
      FROM jobs
      WHERE user_id = %s AND expires_at IS NULL
    )
    SELECT country_code, COUNT(*) as job_count
    FROM country_mapping
    WHERE country_code = 'mx'
    GROUP BY country_code
    """,
    (user_id,)
)

if mexico_jobs:
    print(f"  ✓ Mexico found on map: {mexico_jobs[0]['job_count']} jobs")
else:
    print(f"  ⚠ Mexico NOT on map yet")

print("\n" + "=" * 70)
print("READY FOR VERIFICATION")
print("=" * 70)
