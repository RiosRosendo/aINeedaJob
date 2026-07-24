#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from tools.db import execute_update, execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("STEP 1: BACKFILL search_country FOR LEGACY JOBS")
print("=" * 70)
print()

# Define country patterns
countries = [
    ('us', 'United States', ['%united states%', '%, US', '%, USA', '%California%', '%New York%', '%Texas%']),
    ('ca', 'Canada', ['%canada%', '%ontario%', '%toronto%', '%vancouver%']),
    ('fr', 'France', ['%france%', '%paris%']),
    ('de', 'Germany', ['%germany%', '%deutschland%', '%berlin%', '%munich%']),
    ('mx', 'Mexico', ['%mexico%', '%ciudad de mexico%', '%monterrey%', '%guadalajara%']),
    ('it', 'Italy', ['%italy%', '%italia%', '%rome%', '%milan%']),
]

total_updated = 0

for code, name, patterns in countries:
    # Build WHERE clause with OR conditions for each pattern
    or_conditions = ' OR '.join(['location ILIKE %s'] * len(patterns))

    query = f"""
    UPDATE jobs
    SET search_country = %s
    WHERE user_id = %s
    AND search_country IS NULL
    AND ({or_conditions})
    """

    try:
        # Prepare parameters: code, user_id, then all patterns
        params = [code, user_id] + patterns
        execute_update(query, params)

        # Get count of jobs now with this search_country
        count_result = execute_query(
            "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND search_country = %s",
            (user_id, code)
        )
        count = count_result[0]['cnt'] if count_result else 0

        print(f"✓ {name} ({code:>2s}): {count:>4d} jobs tagged")
    except Exception as e:
        print(f"✗ {name} ({code:>2s}): ERROR - {str(e)}")

print()

# Show breakdown
print("=" * 70)
print("BREAKDOWN AFTER BACKFILL")
print("=" * 70)
print()

breakdown = execute_query(
    """
    SELECT search_country, COUNT(*) as cnt
    FROM jobs
    WHERE user_id = %s AND expires_at IS NULL
    GROUP BY search_country
    ORDER BY cnt DESC
    """,
    (user_id,)
)

if breakdown:
    grand_total = sum(row['cnt'] for row in breakdown)
    for row in breakdown:
        code = row.get('search_country') or 'NULL'
        count = row.get('cnt')
        pct = (count / grand_total * 100) if grand_total > 0 else 0
        print(f"  {code:>4s}: {count:>5d} jobs ({pct:>5.1f}%)")

    print()
    print(f"TOTAL ACTIVE JOBS: {grand_total}")
