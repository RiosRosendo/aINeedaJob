#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from tools.db import execute_update, execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("STEP 1: CLEAN DATABASE FOR USER")
print("=" * 70)
print()

# Show counts before
print("Before cleanup:")
fit_scores = execute_query("SELECT COUNT(*) as cnt FROM fit_scores WHERE user_id = %s", (user_id,))
applications = execute_query("SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s", (user_id,))
jobs = execute_query("SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s", (user_id,))

print(f"  fit_scores: {fit_scores[0]['cnt']}")
print(f"  applications: {applications[0]['cnt']}")
print(f"  jobs: {jobs[0]['cnt']}")
print()

# Delete in order (foreign key constraints)
print("Deleting...")
execute_update("DELETE FROM fit_scores WHERE user_id = %s", (user_id,))
print("  ✓ fit_scores deleted")

execute_update("DELETE FROM applications WHERE user_id = %s", (user_id,))
print("  ✓ applications deleted")

# Also delete from cv_tailored (foreign key to jobs)
execute_update("DELETE FROM cv_tailored WHERE job_id IN (SELECT id FROM jobs WHERE user_id = %s)", (user_id,))
print("  ✓ cv_tailored deleted")

execute_update("DELETE FROM jobs WHERE user_id = %s", (user_id,))
print("  ✓ jobs deleted")

print()
print("After cleanup:")
fit_scores = execute_query("SELECT COUNT(*) as cnt FROM fit_scores WHERE user_id = %s", (user_id,))
applications = execute_query("SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s", (user_id,))
jobs = execute_query("SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s", (user_id,))

print(f"  fit_scores: {fit_scores[0]['cnt']}")
print(f"  applications: {applications[0]['cnt']}")
print(f"  jobs: {jobs[0]['cnt']}")
print()
print("✓ Database cleaned for user")
