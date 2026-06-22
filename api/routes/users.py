"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from tools.db import execute_query, execute_update
from api.models.schemas import UserProfileResponse, UserProfileBase
import json

router = APIRouter()


def get_user_id(x_user_id: str = Header(...)) -> str:
    """Extract user ID from request header. SECURITY: Replace with real auth."""
    return x_user_id


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str = Depends(get_user_id)):
    """
    Get user profile.

    Returns user's job preferences, skills, and profile URLs.
    """
    try:
        result = execute_query(
            "SELECT * FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )
        if not result:
            raise HTTPException(status_code=404, detail="User profile not found")

        profile = result[0]
        # Parse JSON fields
        if isinstance(profile.get("target_roles"), str):
            profile["target_roles"] = json.loads(profile["target_roles"])
        if isinstance(profile.get("preferred_countries"), str):
            profile["preferred_countries"] = json.loads(profile["preferred_countries"])
        if isinstance(profile.get("tech_stack"), str):
            profile["tech_stack"] = json.loads(profile["tech_stack"])

        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile")
async def update_user_profile(
    profile: UserProfileBase,
    user_id: str = Depends(get_user_id)
):
    """
    Update user profile.

    Updates job preferences, skills, and profile URLs.
    """
    try:
        # Check if profile exists
        result = execute_query(
            "SELECT id FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        query = """
            UPDATE user_profiles SET
              target_roles = %s,
              preferred_modality = %s,
              preferred_countries = %s,
              salary_min = %s,
              tech_stack = %s,
              cv_base_url = %s,
              github_url = %s,
              linkedin_url = %s,
              updated_at = NOW()
            WHERE user_id = %s
        """

        params = (
            json.dumps(profile.target_roles),
            profile.preferred_modality,
            json.dumps(profile.preferred_countries),
            profile.salary_min,
            json.dumps(profile.tech_stack),
            profile.cv_base_url,
            profile.github_url,
            profile.linkedin_url,
            user_id
        )

        rows = execute_update(query, params)

        if rows == 0:
            # Create new profile if it doesn't exist
            insert_query = """
                INSERT INTO user_profiles
                (user_id, target_roles, preferred_modality, preferred_countries, salary_min, tech_stack, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            insert_params = (
                user_id,
                json.dumps(profile.target_roles),
                profile.preferred_modality,
                json.dumps(profile.preferred_countries),
                profile.salary_min,
                json.dumps(profile.tech_stack)
            )
            execute_update(insert_query, insert_params)

        # Return updated profile
        updated = execute_query(
            "SELECT * FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )
        if updated:
            result = updated[0]
            if isinstance(result.get("target_roles"), str):
                result["target_roles"] = json.loads(result["target_roles"])
            if isinstance(result.get("preferred_countries"), str):
                result["preferred_countries"] = json.loads(result["preferred_countries"])
            if isinstance(result.get("tech_stack"), str):
                result["tech_stack"] = json.loads(result["tech_stack"])
            return result

        raise HTTPException(status_code=500, detail="Failed to update profile")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
