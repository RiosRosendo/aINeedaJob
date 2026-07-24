"""Application management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime, timedelta
from tools.db import execute_query, execute_update
from tools.update_application import update_application
from tools.create_notification import create_notification
from tools.trigger_agent import trigger_agent
from tools.tailor_cv import tailor_cv_for_job, get_tailored_cv
from tools.apply_job import apply_for_job_sync
from api.models.schemas import ApplicationResponse, ApplicationApprovalRequest
from api.dependencies import get_user_id

router = APIRouter()


@router.get("", response_model=List[dict])
async def list_applications(user_id: str = Depends(get_user_id), limit: int = 50):
    """
    List all applications for user with job details.

    Multi-user scoped: returns only applications for this user.
    Always returns ALL pending_approval items first, regardless of limit.
    Then fills remaining slots up to limit with other statuses.
    """
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
            ORDER BY CASE WHEN a.status = 'pending_approval' THEN 0 ELSE 1 END,
                     a.created_at DESC
            """,
            (user_id,)
        )

        deduped = []
        for app in results:
            app_clean = {k: v for k, v in app.items() if k != 'desc_preview'}
            deduped.append(app_clean)

        # Separate pending_approval from other statuses
        pending = [app for app in deduped if app.get('status') == 'pending_approval']
        others = [app for app in deduped if app.get('status') != 'pending_approval']

        # Return all pending_approval items, then fill remaining slots with others
        result = pending + others[:max(0, limit - len(pending))]
        return result
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

    Updates Application status and triggers CV Tailoring.
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

        job_id = app.get("job_id")

        # Update status
        update_application(application_id, user_id, "pending_application")

        # Trigger CV Tailoring (generate tailored CV for this job)
        try:
            print(f"[APPROVE] Tailoring CV for job {job_id}, user {user_id}", flush=True)
            tailored = tailor_cv_for_job(user_id, job_id)
            print(f"[APPROVE] CV tailoring successful: {tailored.get('status')}", flush=True)
        except Exception as e:
            print(f"[APPROVE] CV tailoring failed: {type(e).__name__}: {str(e)}", flush=True)
            # Log error but don't fail the approval - CV tailoring is a best-effort enhancement

        return {
            "status": "approved",
            "message": "Application approved and CV tailoring triggered"
        }

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


@router.post("/{application_id}/auto-apply")
async def auto_apply_for_job(
    application_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Manually trigger autonomous application for an approved job.

    Calls the Application Agent to attempt applying via form or email.
    Returns the application method and result.
    """
    try:
        print(f"[AUTO_APPLY] Endpoint called for application {application_id}, user {user_id}", flush=True)

        # Verify application exists and user owns it
        app_result = execute_query(
            "SELECT id, job_id, status FROM applications WHERE id = %s AND user_id = %s",
            (application_id, user_id)
        )
        if not app_result:
            raise HTTPException(status_code=404, detail="Application not found")

        app = app_result[0]
        job_id = app.get("job_id")

        # Get job URL
        job_result = execute_query(
            "SELECT url FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )
        if not job_result or not job_result[0].get('url'):
            raise HTTPException(status_code=400, detail="Job URL not found")

        job_url = job_result[0].get('url')

        print(f"[AUTO_APPLY] Attempting to apply for job {job_id}, URL: {job_url}", flush=True)

        # Call Application Agent
        apply_result = apply_for_job_sync(user_id, job_id, application_id, job_url, None)

        print(f"[AUTO_APPLY] Result: {apply_result}", flush=True)

        # Update application status based on result
        new_status = apply_result.get("status", "requires_manual")
        execute_update(
            "UPDATE applications SET status = %s, updated_at = NOW() WHERE id = %s",
            (new_status, application_id)
        )

        # Return result directly from apply_for_job_sync()
        return {
            "status": "success",
            "result": {
                "status": apply_result.get("status"),
                "method": apply_result.get("method"),
                "action": apply_result.get("action"),
                "what_i_tried": apply_result.get("what_i_tried"),
                "why_i_need_help": apply_result.get("why_i_need_help"),
                "error": apply_result.get("error")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTO_APPLY] Error: {type(e).__name__}: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Auto-apply failed: {str(e)}")


@router.get("/tailored/{job_id}")
async def get_tailored_cv_endpoint(
    job_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get the tailored CV for a specific job.

    Returns the AI-generated tailored CV with:
    - Professional summary targeted to the job
    - Highlighted skills matching job requirements
    - Relevant projects with tailoring explanations
    - Notes about what was tailored and why

    Returns 404 if no tailored CV exists for this job.
    """
    try:
        # Verify user owns this job
        job_check = execute_query(
            "SELECT id FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )
        if not job_check:
            raise HTTPException(status_code=404, detail="Job not found")

        # Get tailored CV
        tailored = get_tailored_cv(user_id, job_id)

        if not tailored:
            raise HTTPException(
                status_code=404,
                detail="Tailored CV not found for this job. Approve the application to generate one."
            )

        return tailored

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}/interview-prep")
async def get_interview_prep(
    application_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get interview preparation materials for an application.

    Returns:
    - 10 likely interview questions
    - Key talking points
    - Company research summary
    """
    try:
        import json

        # Verify user owns this application
        app_check = execute_query(
            "SELECT job_id FROM applications WHERE id = %s AND user_id = %s",
            (application_id, user_id)
        )
        if not app_check:
            raise HTTPException(status_code=404, detail="Application not found")

        # Get interview prep
        prep_result = execute_query(
            "SELECT questions, talking_points, company_research, created_at FROM interview_prep WHERE application_id = %s",
            (application_id,)
        )

        if not prep_result:
            raise HTTPException(
                status_code=404,
                detail="Interview prep not available yet. Prep materials are generated when interview is confirmed."
            )

        prep = prep_result[0]

        # Parse JSON fields
        questions = prep.get("questions", [])
        talking_points = prep.get("talking_points", [])

        if isinstance(questions, str):
            questions = json.loads(questions) if questions else []
        if isinstance(talking_points, str):
            talking_points = json.loads(talking_points) if talking_points else []

        return {
            "questions": questions,
            "talking_points": talking_points,
            "company_research": prep.get("company_research", ""),
            "generated_at": prep.get("created_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
