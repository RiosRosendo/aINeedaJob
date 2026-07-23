"""Job search and listing endpoints."""

import sys
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from tools.db import execute_query
from api.models.schemas import JobResponse, FitScoreResponse, JobSearchRequest
from api.dependencies import get_user_id
from agents.pipeline import graph, JobState, processing_node

router = APIRouter()

print("JOBS ROUTER LOADED", flush=True)

@router.get("")
async def list_jobs(user_id: str = Depends(get_user_id), limit: int = 50):
    """
    List all jobs for authenticated user with their fit scores.

    Multi-user scoped: returns only jobs for this user.
    Returns both paginated jobs and total count in format:
    {
        "jobs": [...],
        "total_count": <number>
    }
    """
    try:
        # Get paginated jobs (all jobs that have been scored, excluding expired)
        results = execute_query(
            """
            SELECT
                j.id, j.user_id, j.source, j.title, j.company, j.location, j.modality,
                j.salary_min, j.salary_max, j.required_skills, j.nice_to_have_skills,
                j.experience_level, j.description_raw, j.status, j.created_at, j.updated_at,
                fs.score as fit_score, fs.strengths, fs.gaps
            FROM jobs j
            INNER JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
              AND j.expires_at IS NULL
            ORDER BY fs.score DESC, j.created_at DESC
            LIMIT %s
            """,
            (user_id, user_id, limit)
        )

        # Get total count (all scored jobs, excluding expired)
        count_result = execute_query(
            """
            SELECT COUNT(*) as total FROM jobs j
            INNER JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
              AND j.expires_at IS NULL
            """,
            (user_id, user_id)
        )
        total_count = count_result[0]["total"] if count_result else 0

        response = {
            "jobs": results,
            "total_count": total_count
        }
        print(f"[API /jobs] Returning response: jobs={len(results)}, total_count={total_count}", flush=True)
        return response
    except Exception as e:
        print(f"[API /jobs] ERROR: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_agent_logs(user_id: str = Depends(get_user_id), limit: int = 5):
    """
    Get recent agent activity logs for the user.

    Returns the last N entries from agent_logs table with fit scores.
    """
    try:
        results = execute_query(
            """
            SELECT
                l.id, l.agent, l.status, l.details, l.created_at, l.job_id,
                fs.score as fit_score, fs.decision
            FROM agent_logs l
            LEFT JOIN fit_scores fs ON l.job_id = fs.job_id AND fs.user_id = %s
            WHERE l.user_id = %s
            ORDER BY l.created_at DESC
            LIMIT %s
            """,
            (user_id, user_id, limit)
        )
        return results or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-country")
async def get_jobs_by_country(user_id: str = Depends(get_user_id)):
    """
    Get jobs grouped by country with coordinates for world map visualization.

    Returns list of countries with job counts and coordinates:
    [
        {
            "country": "United States",
            "country_code": "us",
            "count": 45,
            "lat": 37.09,
            "lng": -95.71
        },
        ...
    ]
    """
    import traceback
    try:
        print(f"[BY-COUNTRY] Starting for user_id={user_id}", flush=True)

        # Get all jobs for this user with their fit scores (excluding expired, only active verified)
        print(f"[BY-COUNTRY] Querying jobs for user {user_id}", flush=True)
        results = execute_query(
            """
            SELECT j.id, j.location, fs.score as fit_score
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
              AND j.expires_at IS NULL
              AND (
                j.last_verified_at > NOW() - INTERVAL '7 days'
                OR j.created_at > NOW() - INTERVAL '7 days'
              )
            ORDER BY j.created_at DESC
            """,
            (user_id, user_id)
        )
        print(f"[BY-COUNTRY] Query returned {len(results) if results else 0} jobs", flush=True)

        # Group by country
        country_map = {}
        for job in results:
            location = job.get("location")
            if not location:
                continue

            country_code = extract_country_from_location(location)
            if not country_code or country_code not in COUNTRY_COORDS:
                continue

            if country_code not in country_map:
                country_map[country_code] = {
                    "country": COUNTRY_COORDS[country_code]["name"],
                    "country_code": country_code,
                    "count": 0,
                    "lat": COUNTRY_COORDS[country_code]["lat"],
                    "lng": COUNTRY_COORDS[country_code]["lng"],
                }

            country_map[country_code]["count"] += 1

        # Sort by count descending
        result_list = sorted(country_map.values(), key=lambda x: x["count"], reverse=True)

        print(f"[BY-COUNTRY] Found {len(result_list)} countries with jobs for user {user_id}", flush=True)
        return result_list

    except Exception as e:
        print(f"[BY-COUNTRY ERROR] Exception type: {type(e).__name__}", flush=True)
        print(f"[BY-COUNTRY ERROR] Error message: {str(e)}", flush=True)
        print(f"[BY-COUNTRY ERROR] Full traceback:\n{traceback.format_exc()}", flush=True)
        sys.stdout.flush()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@router.get("/by-country/{country_code}")
async def get_jobs_by_country_detail(country_code: str, user_id: str = Depends(get_user_id)):
    """
    Get all jobs for a specific country.

    Returns jobs with title, company, fit_score for the country's job list panel.
    """
    try:
        # Get all jobs for this country (excluding expired, only active verified)
        results = execute_query(
            """
            SELECT j.id, j.title, j.company, j.location, fs.score as fit_score, a.status as app_status
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            LEFT JOIN applications a ON j.id = a.job_id AND a.user_id = %s
            WHERE j.user_id = %s
              AND j.location LIKE %s
              AND j.expires_at IS NULL
              AND (
                j.last_verified_at > NOW() - INTERVAL '7 days'
                OR j.created_at > NOW() - INTERVAL '7 days'
              )
            ORDER BY fs.score DESC NULLS LAST, j.created_at DESC
            LIMIT 20
            """,
            (user_id, user_id, user_id, f"%{country_code.upper()}%")
        )

        return results or []

    except Exception as e:
        print(f"[API /jobs/by-country/{country_code}] ERROR: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=dict)
async def get_job(job_id: str, user_id: str = Depends(get_user_id)):
    """
    Get single job with fit score.

    Validates user owns this job.
    """
    try:
        job_result = execute_query(
            "SELECT * FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )
        if not job_result:
            raise HTTPException(status_code=404, detail="Job not found")

        job = job_result[0]

        # Fetch fit score if it exists
        fit_result = execute_query(
            "SELECT * FROM fit_scores WHERE job_id = %s AND user_id = %s",
            (job_id, user_id)
        )
        fit_score = fit_result[0] if fit_result else None

        return {"job": job, "fit_score": fit_score}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def trigger_job_search(request: JobSearchRequest):
    """
    Trigger job discovery pipeline.

    Searches Adzuna + The Muse, parses jobs, scores against profile.
    Runs asynchronously via LangGraph pipeline.

    TODO: In production, enqueue to task queue (Celery/Bull).
    """
    try:
        user_id = request.user_id

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
            roles=request.roles or [],
            profile={},
            summary={}
        )

        # Run discovery + batch processing pipeline
        result = graph.invoke(state)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        summary = result.get("summary", {})
        return {
            "status": "completed",
            "jobs_found": len(result.get("raw_jobs", [])),
            "jobs_processed": result.get("processed_count", 0),
            "applied": result.get("applied_count", 0),
            "review": result.get("review_count", 0),
            "summary": summary,
            "message": f"Pipeline complete: {summary.get('applied', 0)} to apply, {summary.get('review', 0)} for review"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_jobs(user_id: str = Depends(get_user_id), batch_size: int = 10):
    """
    Process unscored jobs without running discovery.

    Skips job search and goes straight to parsing + scoring existing jobs.
    Useful for batch processing large job queues.

    Args:
        batch_size: Number of jobs to process in this batch (default 10)
    """
    try:
        print(f"[API /process] ENDPOINT CALLED for user {user_id}", flush=True)
        sys.stdout.flush()

        if not user_id:
            raise Exception("user_id required")

        # Get user profile
        profile_result = execute_query(
            "SELECT target_roles, preferred_countries, preferred_modality, salary_min FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )
        if not profile_result:
            raise Exception("User profile not found")

        profile = profile_result[0]

        # Get unprocessed jobs (discovered/parsed without fit_score)
        unprocessed = execute_query(
            """
            SELECT j.id, j.title, j.company, j.description_raw, j.source
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
              AND j.status IN ('discovered', 'parsed')
              AND fs.id IS NULL
            ORDER BY j.created_at DESC
            LIMIT %s
            """,
            (user_id, user_id, batch_size)
        )

        print(f"[API /process] Found {len(unprocessed) if unprocessed else 0} unprocessed jobs for user {user_id}", flush=True)
        sys.stdout.flush()

        if not unprocessed:
            print(f"[API /process] No unprocessed jobs found, returning early", flush=True)
            sys.stdout.flush()
            return {
                "status": "completed",
                "jobs_processed": 0,
                "applied": 0,
                "review": 0,
                "ignored": 0,
                "message": "No unprocessed jobs found"
            }

        # Create pipeline state for processing only
        state = JobState(
            user_id=user_id,
            raw_jobs=[],
            unprocessed_jobs=unprocessed,
            processed_count=0,
            applied_count=0,
            review_count=0,
            ignored_count=0,
            error="",
            roles=profile.get("target_roles", []),
            profile=profile,
            summary={}
        )

        # Run processing node only (skip discovery)
        print(f"[API /process] Calling processing_node with {len(unprocessed)} jobs, roles={state['roles']}", flush=True)
        sys.stdout.flush()
        result = processing_node(state)
        print(f"[API /process] processing_node returned: processed={result.get('processed_count')}, applied={result.get('applied_count')}, review={result.get('review_count')}, ignored={result.get('ignored_count')}", flush=True)
        sys.stdout.flush()

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "completed",
            "jobs_processed": result.get("processed_count", 0),
            "applied": result.get("applied_count", 0),
            "review": result.get("review_count", 0),
            "summary": result.get("summary", {}),
            "message": f"Processed {result.get('processed_count', 0)} jobs"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API /process] EXCEPTION: {str(e)}", flush=True)
        sys.stdout.flush()
        raise HTTPException(status_code=500, detail=str(e))


# Country coordinates for world map
COUNTRY_COORDS = {
    "us": {"name": "United States", "lat": 37.09, "lng": -95.71},
    "ca": {"name": "Canada", "lat": 56.13, "lng": -106.35},
    "mx": {"name": "Mexico", "lat": 23.63, "lng": -102.55},
    "jp": {"name": "Japan", "lat": 36.20, "lng": 138.25},
    "de": {"name": "Germany", "lat": 51.17, "lng": 10.45},
    "fr": {"name": "France", "lat": 46.23, "lng": 2.21},
    "it": {"name": "Italy", "lat": 41.87, "lng": 12.57},
    "ae": {"name": "UAE", "lat": 23.42, "lng": 53.85},
    "cn": {"name": "China", "lat": 35.86, "lng": 104.20},
    "gb": {"name": "United Kingdom", "lat": 55.38, "lng": -3.44},
    "au": {"name": "Australia", "lat": -25.27, "lng": 133.78},
    "in": {"name": "India", "lat": 20.59, "lng": 78.96},
    "sg": {"name": "Singapore", "lat": 1.35, "lng": 103.82},
    "nl": {"name": "Netherlands", "lat": 52.13, "lng": 5.29},
    "es": {"name": "Spain", "lat": 40.46, "lng": -3.75},
}


def extract_country_from_location(location_str: str) -> str:
    """
    Extract country code from location string.

    Supports formats:
    - "City, Country" (e.g., "New York, US")
    - "City, State/Province, Country" (e.g., "Toronto, ON, Canada")
    - "City, County" (assumes US for common US counties)

    Returns lowercase 2-letter country code or None.
    """
    if not location_str:
        return None

    location_lower = location_str.lower().strip()

    # Quick check for explicit country codes or names
    if location_lower in ("remote", "flexible", "hybrid", "on-site", "unknown", "n/a", "not specified"):
        return None

    # Split by comma and analyze
    parts = [p.strip().lower() for p in location_str.split(",")]

    # Try to match against known country names (check each part)
    country_map = {
        "united states": "us",
        "usa": "us",
        "america": "us",
        "us": "us",
        "canada": "ca",
        "ca": "ca",
        "mexico": "mx",
        "mx": "mx",
        "japan": "jp",
        "germany": "de",
        "de": "de",
        "france": "fr",
        "fr": "fr",
        "italy": "it",
        "it": "it",
        "uae": "ae",
        "united arab emirates": "ae",
        "ae": "ae",
        "china": "cn",
        "cn": "cn",
        "uk": "gb",
        "united kingdom": "gb",
        "gb": "gb",
        "australia": "au",
        "au": "au",
        "india": "in",
        "in": "in",
        "singapore": "sg",
        "sg": "sg",
        "netherlands": "nl",
        "nl": "nl",
        "spain": "es",
        "es": "es",
    }

    # Check if any part matches a known country
    for part in parts:
        if part in country_map:
            return country_map[part]

    # US state/territory abbreviations (indicates US location)
    us_states = {
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
        "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
        "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
        "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new hampshire", "new jersey", "new mexico", "new york", "north carolina", "north dakota",
        "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington", "west virginia",
        "wisconsin", "wyoming", "district of columbia", "d.c.", "dc",
        "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il", "in",
        "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv",
        "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn",
        "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
    }

    # Check if any part matches a known US state
    for part in parts:
        if part in us_states:
            return "us"

    # US county patterns (contains "county", "co.", "parish", "borough", etc.)
    # Check for county patterns
    if "county" in location_lower:
        return "us"
    if " co" in location_lower or location_lower.endswith("co"):  # Matches "Co" or " Co"
        return "us"
    if any(pattern in location_lower for pattern in ["parish", "borough", "census"]):
        return "us"

    # Known major US cities (when in doubt)
    us_cities = {
        "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia", "san antonio",
        "san diego", "dallas", "san jose", "austin", "jacksonville", "miami", "denver", "boston",
        "seattle", "detroit", "minneapolis", "kansas city", "san francisco", "atlanta", "austin",
    }

    # Check first part (usually city name)
    if parts and parts[0] in us_cities:
        return "us"

    # Default: if we can't determine, assume None
    # This prevents incorrect country assignments
    return None


