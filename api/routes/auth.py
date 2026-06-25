"""Authentication endpoints (register, login, refresh token)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from tools.db import execute_query, execute_update
from api.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
import uuid

router = APIRouter()


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    name: str = None


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user with email and password.

    Returns JWT tokens for immediate authentication.
    """
    try:
        # Check if email already exists
        existing = execute_query(
            "SELECT id FROM users WHERE email = %s",
            (request.email,)
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(request.password)

        execute_update(
            """
            INSERT INTO users (id, email, password_hash, name, email_verified, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, request.email, hashed_password, request.name or request.email.split("@")[0], True, True)
        )

        # Create default profile
        execute_update(
            """
            INSERT INTO user_profiles
            (user_id, target_roles, preferred_modality, preferred_countries, salary_min, tech_stack)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, '[]', 'remote', '[]', None, '[]')
        )

        # Create tokens
        access_token = create_access_token(data={"sub": user_id})
        refresh_token = create_refresh_token(data={"sub": user_id})

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.

    Returns JWT tokens for authentication.
    """
    try:
        # Find user by email
        result = execute_query(
            "SELECT id, password_hash FROM users WHERE email = %s",
            (request.email,)
        )

        if not result:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = result[0]
        user_id = user.get("id")
        password_hash = user.get("password_hash")

        # Verify password
        if not verify_password(request.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create tokens
        access_token = create_access_token(data={"sub": user_id})
        refresh_token = create_refresh_token(data={"sub": user_id})

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(refresh_token_str: str):
    """
    Refresh access token using refresh token.

    Takes a valid refresh token and returns a new access token.
    """
    try:
        payload = verify_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Create new access token
        access_token = create_access_token(data={"sub": user_id})

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user_id=user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")
