"""Summary endpoints - weekly summaries, trends, statistics."""

from fastapi import APIRouter, Depends, HTTPException
from tools.db import execute_query
from tools.weekly_summary import generate_weekly_summary
from api.dependencies import get_user_id

router = APIRouter()


@router.get("/weekly")
async def get_weekly_summary(user_id: str = Depends(get_user_id)):
    """
    Get the most recent weekly summary for the user.

    If no summary exists, generates one on demand.
    Returns summary with stats, top jobs, and action items.
    """
    try:
        # Try to fetch most recent summary
        result = execute_query(
            """SELECT id, summary_text, stats, top_jobs, action_items, created_at
               FROM weekly_summaries
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (user_id,)
        )

        if result:
            summary = result[0]
            return {
                "status": "success",
                "summary": {
                    "id": summary.get('id'),
                    "summary_text": summary.get('summary_text'),
                    "stats": summary.get('stats'),
                    "top_jobs": summary.get('top_jobs'),
                    "action_items": summary.get('action_items'),
                    "created_at": summary.get('created_at').isoformat() if summary.get('created_at') else None
                }
            }

        # No summary exists, generate one on demand
        print(f"[SUMMARY] No existing summary for user {user_id}, generating on demand", flush=True)
        summary_data = generate_weekly_summary(user_id)

        return {
            "status": "success",
            "summary": {
                "summary_text": summary_data.get('summary_text'),
                "stats": summary_data.get('stats'),
                "top_jobs": summary_data.get('top_jobs'),
                "action_items": summary_data.get('action_items'),
                "created_at": None  # Just generated
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SUMMARY] Error fetching weekly summary: {type(e).__name__}: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to get weekly summary: {str(e)}")


@router.post("/weekly/regenerate")
async def regenerate_weekly_summary(user_id: str = Depends(get_user_id)):
    """
    Force regenerate the weekly summary, creating a new one immediately.

    Used by the frontend "Generate now" button.
    """
    try:
        print(f"[SUMMARY] Regenerating weekly summary for user {user_id}", flush=True)
        summary_data = generate_weekly_summary(user_id)

        return {
            "status": "success",
            "summary": {
                "summary_text": summary_data.get('summary_text'),
                "stats": summary_data.get('stats'),
                "top_jobs": summary_data.get('top_jobs'),
                "action_items": summary_data.get('action_items'),
                "created_at": None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SUMMARY] Error regenerating weekly summary: {type(e).__name__}: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to regenerate summary: {str(e)}")
