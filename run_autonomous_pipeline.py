#!/usr/bin/env python3
"""
Run the full autonomous pipeline for a user.
Tests: Discovery → Processing → Summary
"""
import sys
sys.path.insert(0, '.')

from tools.db import execute_query
from agents.pipeline import graph, JobState

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("RUNNING AUTONOMOUS PIPELINE")
print("=" * 70)
print()

# Get user profile
profile_result = execute_query(
    "SELECT target_roles, preferred_countries FROM user_profiles WHERE user_id = %s",
    (user_id,)
)

if not profile_result:
    print(f"ERROR: User profile not found for {user_id}")
    sys.exit(1)

profile = profile_result[0]
target_roles = profile.get('target_roles', ['AI Engineer'])
preferred_countries = profile.get('preferred_countries', [])

print(f"User: {user_id}")
print(f"Target roles: {target_roles}")
print(f"Preferred countries: {preferred_countries}")
print()

# Initialize pipeline state
state = JobState(
    user_id=user_id,
    raw_jobs=[],
    unprocessed_jobs=[],
    processed_count=0,
    applied_count=0,
    review_count=0,
    ignored_count=0,
    error="",
    roles=target_roles,
    profile=profile,
    summary={}
)

print("[PIPELINE] Starting autonomous job discovery + processing...")
print()

# Run the full pipeline
try:
    result = graph.invoke(state)

    print()
    print("=" * 70)
    print("PIPELINE RESULTS")
    print("=" * 70)
    print()

    discovered = len(result.get('raw_jobs', []))
    processed = result.get('processed_count', 0)
    applied = result.get('applied_count', 0)
    review = result.get('review_count', 0)
    ignored = result.get('ignored_count', 0)

    print(f"Discovery Phase:")
    print(f"  Jobs found: {discovered}")
    print()

    print(f"Processing Phase:")
    print(f"  Processed: {processed}")
    print(f"  Auto-applied (score >= 85): {applied}")
    print(f"  Pending user approval (60-84): {review}")
    print(f"  Ignored (score < 60): {ignored}")
    print()

    # Check pending approvals
    pending = execute_query(
        "SELECT COUNT(*) as cnt FROM applications WHERE user_id = %s AND status = 'pending_approval'",
        (user_id,)
    )
    pending_count = pending[0]['cnt'] if pending else 0

    print(f"Approval Queue:")
    print(f"  Pending user approval: {pending_count}")
    print()

    print("=" * 70)
    print("✅ AUTONOMOUS PIPELINE COMPLETE")
    print("=" * 70)

except Exception as e:
    print()
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
