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
        # Get paginated jobs
        results = execute_query(
            """
            SELECT
                j.id, j.user_id, j.source, j.title, j.company, j.location, j.modality,
                j.salary_min, j.salary_max, j.required_skills, j.nice_to_have_skills,
                j.experience_level, j.description_raw, j.status, j.created_at, j.updated_at,
                fs.score as fit_score, fs.strengths, fs.gaps
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
            ORDER BY j.created_at DESC
            LIMIT %s
            """,
            (user_id, user_id, limit)
        )

        # Get total count
        count_result = execute_query(
            "SELECT COUNT(*) as total FROM jobs WHERE user_id = %s",
            (user_id,)
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
