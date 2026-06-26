"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from tools.db import execute_query, execute_update
from api.models.schemas import UserProfileResponse, UserProfileBase
from api.dependencies import get_user_id
import json

router = APIRouter()


@router.get("/profile", response_model=dict)
async def get_user_profile(user_id: str = Depends(get_user_id)):
    """
    Get user profile.

    Returns user's job preferences, skills, and profile URLs.
    Auto-creates default profile if not found.
    """
    try:
        result = execute_query(
            "SELECT * FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        # If profile doesn't exist, create a default one
        if not result:
            print(f"Profile not found for user {user_id}, creating default...")
            try:
                # Check if user exists, create if not
                user_result = execute_query(
                    "SELECT id FROM users WHERE id = %s",
                    (user_id,)
                )
                if not user_result:
                    print(f"User not found, creating user {user_id}...")
                    execute_update(
                        "INSERT INTO users (id, email, password_hash, name, email_verified, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                        (user_id, f"{user_id}@example.com", "dev_placeholder", user_id, True, True)
                    )
                    print(f"User {user_id} created successfully")

                # Create default profile
                print(f"Creating default profile for user {user_id}...")
                execute_update(
                    """
                    INSERT INTO user_profiles
                    (user_id, target_roles, preferred_modality, preferred_countries, salary_min, tech_stack)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, '["AI Engineer"]', "remote", '["us"]', 100000, '["Python", "AWS"]')
                )
                print(f"Profile created for user {user_id}")

                # Fetch the newly created profile
                result = execute_query(
                    "SELECT * FROM user_profiles WHERE user_id = %s",
                    (user_id,)
                )
            except Exception as create_err:
                print(f"Error creating profile: {create_err}")
                raise

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create or retrieve profile")

        profile = result[0]
        return profile
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_user_profile: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


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
        print(f"[API PROFILE] Update request for user {user_id}")
        print(f"[API PROFILE] Payload: target_roles={profile.target_roles}, modality={profile.preferred_modality}, countries={profile.preferred_countries}, salary_min={profile.salary_min}")
        print(f"[API PROFILE] Tech stack: {profile.tech_stack}")
        # Check if user exists, create if not
        user_result = execute_query(
            "SELECT id FROM users WHERE id = %s",
            (user_id,)
        )

        if not user_result:
            # Create user first (required for foreign key constraint)
            execute_update(
                "INSERT INTO users (id, email, password_hash, name, email_verified, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, f"{user_id}@example.com", "dev_placeholder", user_id, True, True)
            )

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
        print(f"[API PROFILE] Error updating profile: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
