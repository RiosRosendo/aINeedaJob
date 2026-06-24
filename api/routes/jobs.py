"""Job search and listing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List
from tools.db import execute_query
from api.models.schemas import JobResponse, FitScoreResponse, JobSearchRequest
from agents.pipeline import graph, JobState

router = APIRouter()


def get_user_id(x_user_id: str = Header(...)) -> str:
    """Extract user ID from request header. SECURITY: Replace with real auth."""
    return x_user_id


@router.get("", response_model=List[dict])
async def list_jobs(user_id: str = Depends(get_user_id), limit: int = 50):
    """
    List all jobs for authenticated user with their fit scores.

    Multi-user scoped: returns only jobs for this user.
    """
    try:
        results = execute_query(
            """
            SELECT
                j.id, j.user_id, j.source, j.title, j.company, j.location, j.modality,
                j.salary_min, j.salary_max, j.required_skills, j.nice_to_have_skills,
                j.experience_level, j.description_raw, j.status, j.created_at, j.updated_at,
                fs.score as fit_score
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
            ORDER BY j.created_at DESC
            LIMIT %s
            """,
            (user_id, user_id, limit)
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_agent_logs(user_id: str = Depends(get_user_id), limit: int = 5):
    """
    Get recent agent activity logs for the user.

    Returns the last N entries from agent_logs table.
    """
    try:
        results = execute_query(
            """
            SELECT id, agent, status, details, created_at
            FROM agent_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit)
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
            "ignored": result.get("ignored_count", 0),
            "summary": summary,
            "message": f"Pipeline complete: {summary.get('applied', 0)} to apply, {summary.get('review', 0)} for review"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
