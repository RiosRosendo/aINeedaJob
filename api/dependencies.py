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


# Primary dependency: Extract user_id from JWT token
# Fallback: Also accepts x-user-id header for backward compatibility
async def get_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    """
    Extract user_id from JWT token payload (preferred method).

    The JWT token contains the user_id in the 'sub' (subject) claim.
    This is the authoritative source of user identity.

    Falls back to x-user-id header for backward compatibility during migration.

    Args:
        authorization: JWT Bearer token in "Bearer <token>" format
        x_user_id: Deprecated fallback header

    Returns:
        user_id extracted from JWT token's 'sub' claim

    Raises:
        401: If no valid token or user_id header provided
    """
    # Primary: Extract from JWT token
    if authorization:
        return await get_user_id_from_token(authorization)

    # Fallback: Use x-user-id header (deprecated)
    if x_user_id:
        return x_user_id

    raise HTTPException(status_code=401, detail="Missing or invalid authentication")
