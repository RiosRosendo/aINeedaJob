"""Application management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime, timedelta
from tools.db import execute_query
from tools.update_application import update_application
from tools.create_notification import create_notification
from tools.trigger_agent import trigger_agent
from api.models.schemas import ApplicationResponse, ApplicationApprovalRequest
from api.dependencies import get_user_id

router = APIRouter()


@router.get("", response_model=List[dict])
async def list_applications(user_id: str = Depends(get_user_id), limit: int = 50):
    """
    List all applications for user with job details.

    Multi-user scoped: returns only applications for this user.
    Deduplicates by job title + description hash to handle duplicate job listings.
    Shows only the most recent application per unique job.
    """
    import hashlib

    try:
        results = execute_query(
            """
            SELECT
                a.id, a.job_id, a.user_id, a.status, a.cv_version_url, a.cover_letter_url,
                a.applied_at, a.created_at, a.updated_at,
                j.title as job_title, j.company as job_company,
                COALESCE(LEFT(j.description_raw, 100), '') as desc_preview,
                fs.score as fit_score, fs.decision, fs.strengths, fs.gaps
            FROM applications a
            LEFT JOIN jobs j ON a.job_id = j.id
            LEFT JOIN fit_scores fs ON fs.job_id = a.job_id AND fs.user_id = a.user_id
            WHERE a.user_id = %s
            ORDER BY a.job_id DESC, a.created_at DESC
            """,
            (user_id,)
        )

        # Deduplicate by title + description hash (handles duplicate job listings)
        seen_jobs = {}
        deduped = []

        for app in results:
            job_id = app.get('job_id')
            title = app.get('job_title', '')
            desc_preview = app.get('desc_preview', '')

            # Create hash of title + description to identify duplicate jobs
            job_hash = hashlib.md5((title + desc_preview).encode()).hexdigest()

            if job_hash not in seen_jobs:
                seen_jobs[job_hash] = True
                # Remove desc_preview before returning (internal field only)
                app_clean = {k: v for k, v in app.items() if k != 'desc_preview'}
                deduped.append(app_clean)

        return deduped[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: str, user_id: str = Depends(get_user_id)):
    """
    Get single application.

    Validates user owns this application.
    """
    try:
        result = execute_query(
            "SELECT * FROM applications WHERE id = %s AND user_id = %s",
            (application_id, user_id)
        )
        if not result:
            raise HTTPException(status_code=404, detail="Application not found")
        return result[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{application_id}/approve")
async def approve_application(
    application_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    User approves a review-tier job (score 60-84).

    Updates Application status and triggers CV Tailoring Agent.
    """
    try:
        # Verify application exists and user owns it
        result = execute_query(
            "SELECT job_id, status FROM applications WHERE id = %s AND user_id = %s",
            (application_id, user_id)
        )
        if not result:
            raise HTTPException(status_code=404, detail="Application not found")

        app = result[0]
        if app.get("status") != "pending_approval":
            raise HTTPException(status_code=400, detail="Application not in pending_approval status")

        # Update status
        update_application(application_id, user_id, "pending_application")

        # Trigger CV Tailoring Agent
        job_id = app.get("job_id")
        trigger_agent("cv_tailoring", user_id, job_id, application_id)

        return {"status": "approved", "message": "CV tailoring triggered"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{application_id}/dismiss")
async def dismiss_application(
    application_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    User dismisses a review-tier job.

    Updates Application status to ignored.
    """
    try:
        # Verify application exists
        result = execute_query(
            "SELECT status FROM applications WHERE id = %s AND user_id = %s",
            (application_id, user_id)
        )
        if not result:
            raise HTTPException(status_code=404, detail="Application not found")

        app = result[0]
        if app.get("status") != "pending_approval":
            raise HTTPException(status_code=400, detail="Application not in pending_approval status")

        # Update status to ignored
        update_application(application_id, user_id, "ignored")

        return {"status": "dismissed", "message": "Application marked as ignored"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
