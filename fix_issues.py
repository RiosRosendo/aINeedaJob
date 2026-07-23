#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_update, execute_query

# Issue 1: Restore 9 preferred countries
sql = """UPDATE user_profiles
SET preferred_countries = '["US", "Canada", "Mexico", "Japan", "Italy", "France", "Germany", "UAE", "China"]'::jsonb
WHERE user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'"""

try:
    rows = execute_update(sql, ())
    print(f"✓ Issue 2 FIXED: Restored preferred_countries - {rows} row updated")

    # Verify
    profile = execute_query(
        "SELECT preferred_countries FROM user_profiles WHERE user_id = %s",
        ('14ab2d63-1eef-43d9-b3f4-748566bad8da',)
    )
    if profile:
        countries = profile[0].get('preferred_countries', [])
        print(f"  Verified: {len(countries)} countries in profile: {countries}")
except Exception as e:
    print(f"✗ Issue 2 FAILED: {str(e)}")

# Check current counts
print("\n=== Current State ===")
try:
    # Total discovered jobs
    total = execute_query("SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s", ('14ab2d63-1eef-43d9-b3f4-748566bad8da',))
    print(f"Total discovered jobs: {total[0]['cnt']}")

    # Scored jobs
    scored = execute_query(
        "SELECT COUNT(*) as cnt FROM jobs j INNER JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s WHERE j.user_id = %s",
        ('14ab2d63-1eef-43d9-b3f4-748566bad8da', '14ab2d63-1eef-43d9-b3f4-748566bad8da')
    )
    print(f"Scored jobs: {scored[0]['cnt']}")

    # Pending approvals
    pending = execute_query(
        "SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s AND status = 'pending_approval'",
        ('14ab2d63-1eef-43d9-b3f4-748566bad8da',)
    )
    print(f"Pending approvals: {pending[0]['cnt']}")

except Exception as e:
    print(f"Error checking counts: {str(e)}")
