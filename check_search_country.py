#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from tools.db import execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

result = execute_query(
    """
    SELECT search_country, COUNT(*) as total
    FROM jobs
    WHERE user_id = %s
    AND expires_at IS NULL
    GROUP BY search_country
    ORDER BY total DESC
    """,
    (user_id,)
)

print("=" * 70)
print("JOBS BY SEARCH_COUNTRY (Discovery Pipeline Tagging)")
print("=" * 70)
print()

if result:
    total_jobs = sum(row['total'] for row in result)
    print(f"Total jobs with search_country: {total_jobs}")
    print()
    for row in result:
        code = row.get('search_country')
        count = row.get('total')
        pct = (count / total_jobs * 100) if total_jobs > 0 else 0
        print(f"  {code or 'NULL':>4s}: {count:>5d} jobs ({pct:>5.1f}%)")

    # Check for jobs without search_country
    no_search = execute_query(
        """
        SELECT COUNT(*) as cnt FROM jobs
        WHERE user_id = %s AND expires_at IS NULL AND search_country IS NULL
        """,
        (user_id,)
    )
    if no_search:
        null_count = no_search[0]['cnt']
        print()
        print(f"  NULL : {null_count:>5d} jobs (no search_country set)")
        grand_total = total_jobs + null_count
        print()
        print(f"TOTAL ACTIVE JOBS: {grand_total}")
else:
    print("No results found")
