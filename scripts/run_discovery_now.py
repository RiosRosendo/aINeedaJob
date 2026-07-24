#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from agents.pipeline import graph
from tools.db import execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("RUNNING DISCOVERY PIPELINE FOR ROSENDO")
print("=" * 70)

# Check before
before = execute_query(
    "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND expires_at IS NULL",
    (user_id,)
)
print(f"\nBefore: {before[0]['cnt']} jobs in database")

try:
    # Create initial state
    state = {
        'user_id': user_id,
        'raw_jobs': [],
        'unprocessed_jobs': [],
        'processed_count': 0,
        'applied_count': 0,
        'review_count': 0,
        'ignored_count': 0,
        'error': None,
        'roles': None,  # Use profile roles
        'profile': {},
        'summary': {}
    }

    # Run the pipeline
    print("\nRunning discovery → processing → summary pipeline...\n")
    result = graph.invoke(state)

    print(f"\nPipeline completed!")
    print(f"  Processed: {result.get('processed_count')} jobs")
    print(f"  Applied: {result.get('applied_count')} jobs")
    print(f"  Review: {result.get('review_count')} jobs")
    print(f"  Ignored: {result.get('ignored_count')} jobs")

    # Check after
    after = execute_query(
        "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND expires_at IS NULL",
        (user_id,)
    )
    print(f"\nAfter: {after[0]['cnt']} jobs in database")
    print(f"Added: {after[0]['cnt'] - before[0]['cnt']} jobs")

    # Check Mexico
    mexico = execute_query(
        "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND search_country = 'mx' AND expires_at IS NULL",
        (user_id,)
    )
    print(f"\nMexico jobs (search_country='mx'): {mexico[0]['cnt']}")

except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
