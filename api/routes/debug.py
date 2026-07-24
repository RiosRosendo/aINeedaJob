"""Debug endpoints for diagnosing system state."""

import sys
from fastapi import APIRouter, Depends, HTTPException
from tools.db import execute_query
from api.dependencies import get_user_id

router = APIRouter()


@router.get("/jobs-by-country")
async def debug_jobs_by_country(user_id: str = Depends(get_user_id)):
    """
    DEBUG ENDPOINT: Show raw breakdown of jobs by search_country and location extraction.

    Returns:
    {
        "total_jobs": <all active jobs>,
        "by_search_country": {
            "us": <count>,
            "mx": <count>,
            ...
        },
        "by_location_extraction": {
            "us": <count>,
            "mx": <count>,
            ...
        },
        "mexico_samples": [
            {"id": "...", "title": "...", "search_country": "mx", "location": "..."},
            ...
        ]
    }
    """
    try:
        print(f"[DEBUG /jobs-by-country] Starting for user_id={user_id}", flush=True)

        # Total active jobs
        total = execute_query(
            "SELECT COUNT(*) as cnt FROM jobs WHERE user_id = %s AND expires_at IS NULL",
            (user_id,)
        )
        total_count = total[0]['cnt'] if total else 0
        print(f"[DEBUG /jobs-by-country] Total active jobs: {total_count}", flush=True)

        # Jobs by search_country (raw counts)
        by_search = execute_query(
            """
            SELECT search_country, COUNT(*) as cnt
            FROM jobs
            WHERE user_id = %s AND expires_at IS NULL AND search_country IS NOT NULL
            GROUP BY search_country
            ORDER BY cnt DESC
            """,
            (user_id,)
        )
        search_country_map = {}
        for row in (by_search or []):
            code = (row.get('search_country') or '').lower()
            search_country_map[code] = row.get('cnt', 0)
        print(f"[DEBUG /jobs-by-country] By search_country: {search_country_map}", flush=True)

        # Jobs by location extraction
        location_extract = execute_query(
            """
            SELECT
              CASE
                WHEN location ILIKE %s OR location ILIKE %s THEN 'us'
                WHEN location ILIKE %s OR location = %s THEN 'ca'
                WHEN location ILIKE %s OR location = %s THEN 'mx'
                WHEN location ILIKE %s OR location = %s THEN 'jp'
                WHEN location ILIKE %s OR location = %s THEN 'it'
                WHEN location ILIKE %s OR location = %s THEN 'fr'
                WHEN location ILIKE %s OR location = %s THEN 'de'
                WHEN location ILIKE %s OR location = %s THEN 'ae'
                WHEN location ILIKE %s OR location = %s THEN 'cn'
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
             '%Canada%', 'CA',
             '%Mexico%', 'MX',
             '%Japan%', 'JP',
             '%Italy%', 'IT',
             '%France%', 'FR',
             '%Germany%', 'DE',
             '%UAE%', 'AE',
             '%China%', 'CN')
        )
        location_map = {}
        for row in (location_extract or []):
            code = (row.get('country_code') or '').lower()
            if code:
                location_map[code] = row.get('cnt', 0)
        print(f"[DEBUG /jobs-by-country] By location extraction: {location_map}", flush=True)

        # Sample Mexico jobs
        mexico_samples = execute_query(
            """
            SELECT id, title, search_country, location
            FROM jobs
            WHERE user_id = %s AND expires_at IS NULL
            AND (search_country = 'mx' OR location ILIKE '%Mexico%' OR location = 'MX')
            LIMIT 3
            """,
            (user_id,)
        )
        mexico_list = []
        for job in (mexico_samples or []):
            mexico_list.append({
                "id": job.get('id'),
                "title": job.get('title'),
                "search_country": job.get('search_country'),
                "location": job.get('location')
            })
        print(f"[DEBUG /jobs-by-country] Mexico samples: {len(mexico_list)} jobs", flush=True)

        sys.stdout.flush()
        return {
            "total_jobs": total_count,
            "by_search_country": search_country_map,
            "by_location_extraction": location_map,
            "mexico_samples": mexico_list
        }

    except Exception as e:
        print(f"[DEBUG /jobs-by-country] ERROR: {str(e)}", flush=True)
        sys.stdout.flush()
        raise HTTPException(status_code=500, detail=str(e))
