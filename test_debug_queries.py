#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from tools.db import execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

# Test the search_country query
print("Testing search_country query...")
try:
    result = execute_query(
        """
        SELECT search_country, COUNT(*) as cnt
        FROM jobs
        WHERE user_id = %s AND expires_at IS NULL AND search_country IS NOT NULL
        GROUP BY search_country
        ORDER BY cnt DESC
        """,
        (user_id,)
    )
    print(f"✓ search_country query works: {len(result)} rows")
except Exception as e:
    print(f"✗ search_country query failed: {e}")

# Test the location extraction query
print("\nTesting location extraction query...")
try:
    result = execute_query(
        """
        SELECT
          CASE
            WHEN location ILIKE %s OR location ILIKE %s THEN 'us'
            WHEN location ILIKE %s OR location = %s THEN 'ca'
            ELSE NULL
          END as country_code,
          COUNT(*) as cnt
        FROM jobs
        WHERE user_id = %s AND expires_at IS NULL AND search_country IS NULL
        GROUP BY country_code
        ORDER BY cnt DESC
        """,
        (user_id,
         '%US%', '%United States%',
         '%Canada%', 'CA')
    )
    print(f"✓ location extraction query works: {len(result)} rows")
    if result:
        for row in result:
            print(f"  {row.get('country_code')}: {row.get('cnt')}")
except Exception as e:
    print(f"✗ location extraction query failed: {e}")

# Test simple Mexico count
print("\nSimple Mexico count...")
try:
    result = execute_query(
        "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND search_country = 'mx' AND expires_at IS NULL",
        (user_id,)
    )
    print(f"✓ Mexico jobs: {result[0]['cnt']}")
except Exception as e:
    print(f"✗ Failed: {e}")
