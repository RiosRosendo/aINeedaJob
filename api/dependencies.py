"""FastAPI dependencies for authentication and user scoping."""

from fastapi import HTTPException, Header
from api.auth_utils import verify_token
from typing import Optional


async def get_user_id_from_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract user_id from JWT Bearer token in Authorization header.

    Raises 401 if token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    # Expected format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = parts[1]
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return user_id


# For backward compatibility during migration, also support x-user-id header
# (This should be removed once all endpoints are updated)
async def get_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    """
    Get user_id from JWT token (preferred) or x-user-id header (deprecated).

    During migration, supports both. Eventually remove x-user-id support.
    """
    if authorization:
        return await get_user_id_from_token(authorization)

    if x_user_id:
        # Deprecated: x-user-id header should not be used in production
        # This is only for backward compatibility during migration
        return x_user_id

    raise HTTPException(status_code=401, detail="Missing or invalid authentication")
