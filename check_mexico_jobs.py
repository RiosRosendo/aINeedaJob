#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from tools.db import execute_query

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("CHECKING MEXICO JOBS")
print("=" * 70)

# Check jobs with search_country = 'mx'
mexico_with_search = execute_query(
    "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND search_country = 'mx'",
    (user_id,)
)
print(f"\nJobs with search_country='mx': {mexico_with_search[0]['cnt']}")

# Check jobs with Mexico in location
mexico_in_location = execute_query(
    "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND location ILIKE '%%Mexico%%'",
    (user_id,)
)
print(f"Jobs with 'Mexico' in location: {mexico_in_location[0]['cnt']}")

# Check for MX in location
mx_in_location = execute_query(
    "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND location = 'MX'",
    (user_id,)
)
print(f"Jobs with location='MX': {mx_in_location[0]['cnt']}")

# Show what the by-country query returns for Mexico
mexico_on_map = execute_query(
    """
    WITH country_mapping AS (
      SELECT id, COALESCE(search_country,
        CASE
          WHEN location ILIKE '%%US%%' OR location ILIKE '%%United States%%' THEN 'us'
          WHEN location ILIKE '%%Canada%%' OR location = 'CA' THEN 'ca'
          WHEN location ILIKE '%%Mexico%%' OR location = 'MX' THEN 'mx'
          WHEN location ILIKE '%%Japan%%' OR location = 'JP' THEN 'jp'
          WHEN location ILIKE '%%Italy%%' OR location = 'IT' THEN 'it'
          WHEN location ILIKE '%%France%%' OR location = 'FR' THEN 'fr'
          WHEN location ILIKE '%%Germany%%' OR location = 'DE' THEN 'de'
          WHEN location ILIKE '%%UAE%%' OR location = 'AE' THEN 'ae'
          WHEN location ILIKE '%%China%%' OR location = 'CN' THEN 'cn'
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

if mexico_on_map:
    print(f"\nMexico on map (via by-country query): {mexico_on_map[0]['job_count']} jobs")
else:
    print(f"\nMexico on map: NOT FOUND")

print("\nNote: If search_country is 0, the 26 Mexico jobs from the search")
print("      might not have been saved with search_country='mx'.")
print("      This could be because the discovery pipeline tags jobs AFTER")
print("      they're fetched, but before they're saved.")
