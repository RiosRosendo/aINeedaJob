#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query, execute_update

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("CRITICAL FIX 1: DUPLICATE JOBS ANALYSIS & CLEANUP")
print("=" * 70)

# Check for duplicates
duplicates = execute_query('''
SELECT COUNT(*) as dup_count, url FROM jobs
WHERE user_id = %s AND url IS NOT NULL
GROUP BY url HAVING COUNT(*) > 1
ORDER BY dup_count DESC
LIMIT 20
''', (user_id,))

print(f'\nTotal unique URLs with duplicates: {len(duplicates)}')

if duplicates:
    total_dup_jobs = sum(d['dup_count'] for d in duplicates)
    total_excess = sum(d['dup_count'] - 1 for d in duplicates)
    print(f'Total duplicate records: {total_excess} excess jobs')
    print(f'\nTop 10 duplicates:')
    for i, d in enumerate(duplicates[:10], 1):
        print(f'  {i}. {d["dup_count"]} copies - {d["url"][:65]}')
else:
    print('No duplicates found!')

# Total jobs before cleanup
total_before = execute_query('SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s', (user_id,))
print(f'\nJobs in DB before cleanup: {total_before[0]["cnt"]}')

# Cleanup: Keep only the first (oldest) occurrence of each URL
print('\n' + '=' * 70)
print('CLEANING UP DUPLICATES')
print('=' * 70)

if duplicates:
    # For each duplicate URL, keep only the one with the earliest created_at
    cleanup_query = '''
    DELETE FROM jobs
    WHERE user_id = %s
    AND id NOT IN (
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY url ORDER BY created_at ASC) as rn
            FROM jobs
            WHERE user_id = %s AND url IS NOT NULL
        ) ranked
        WHERE rn = 1
    )
    AND url IS NOT NULL
    '''

    deleted = execute_update(cleanup_query, (user_id, user_id))
    print(f'✓ Deleted {deleted} duplicate job records')
else:
    deleted = 0
    print('✓ No duplicates to delete')

# Verify cleanup
total_after = execute_query('SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s', (user_id,))
print(f'\nJobs in DB after cleanup: {total_after[0]["cnt"]}')
print(f'Jobs removed: {total_before[0]["cnt"] - total_after[0]["cnt"]}')

# Check search_country column
print('\n' + '=' * 70)
print('CRITICAL FIX 2: ADD search_country COLUMN')
print('=' * 70)

try:
    execute_update(
        'ALTER TABLE jobs ADD COLUMN IF NOT EXISTS search_country VARCHAR(10)',
        ()
    )
    print('✓ search_country column added/verified')
except Exception as e:
    print(f'ℹ Column status: {str(e)[:80]}')

print('\n' + '=' * 70)
print('SUMMARY')
print('=' * 70)
print(f'✓ Duplicates found and cleaned: {deleted} removed')
print(f'✓ Final job count: {total_after[0]["cnt"]}')
print(f'✓ search_country column ready')
print('\nNext: Update save_jobs.py to prevent duplicates and save search_country')
