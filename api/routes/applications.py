"""Application management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List
from datetime import datetime, timedelta
from tools.db import execute_query
from tools.update_application import update_application
from tools.create_notification import create_notification
from tools.trigger_agent import trigger_agent
from api.models.schemas import ApplicationResponse, ApplicationApprovalRequest

router = APIRouter()


def get_user_id(x_user_id: str = Header(...)) -> str:
    """Extract user ID from request header. SECURITY: Replace with real auth."""
    return x_user_id


@router.get("", response_model=List[ApplicationResponse])
async def list_applications(user_id: str = Depends(get_user_id), limit: int = 50):
    """
    List all applications for user.

    Multi-user scoped: returns only applications for this user.
    """
    try:
        results = execute_query(
            "SELECT * FROM applications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit)
        )
        return results
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
