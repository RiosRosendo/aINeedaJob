"""Gmail OAuth integration and email management."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import os
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus
import requests
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load environment variables from .env (override=True to override empty vars)
load_dotenv(override=True)

from api.dependencies import get_user_id
from tools.db import execute_query, execute_update

router = APIRouter()

# Google OAuth configuration
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:3000/api/gmail/callback")

# Debug: Log if credentials are loaded
print(f"[GMAIL] GMAIL_CLIENT_ID loaded: {bool(GMAIL_CLIENT_ID)}", flush=True)
print(f"[GMAIL] GMAIL_CLIENT_SECRET loaded: {bool(GMAIL_CLIENT_SECRET)}", flush=True)
print(f"[GMAIL] REDIRECT_URI loaded: {bool(REDIRECT_URI)}", flush=True)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


@router.get("/auth")
async def gmail_auth(user_id: str = Depends(get_user_id)):
    """
    Get Google OAuth authorization URL.

    Returns the URL for user to click to authorize Gmail access.
    """
    print(f"[GMAIL AUTH] Request from user {user_id}", flush=True)
    print(f"[GMAIL AUTH] GMAIL_CLIENT_ID: {GMAIL_CLIENT_ID}", flush=True)
    print(f"[GMAIL AUTH] GMAIL_CLIENT_SECRET: {GMAIL_CLIENT_SECRET[:20] if GMAIL_CLIENT_SECRET else None}...", flush=True)
    print(f"[GMAIL AUTH] REDIRECT_URI: {REDIRECT_URI}", flush=True)

    if not GMAIL_CLIENT_ID:
        error_msg = "Google OAuth not configured. GMAIL_CLIENT_ID missing in .env file."
        print(f"[GMAIL AUTH] ERROR: {error_msg}", flush=True)
        raise HTTPException(status_code=500, detail=error_msg)

    if not GMAIL_CLIENT_SECRET:
        error_msg = "Google OAuth not configured. GMAIL_CLIENT_SECRET missing in .env file."
        print(f"[GMAIL AUTH] ERROR: {error_msg}", flush=True)
        raise HTTPException(status_code=500, detail=error_msg)

    if not REDIRECT_URI:
        error_msg = "Google OAuth not configured. GMAIL_REDIRECT_URI missing in .env file."
        print(f"[GMAIL AUTH] ERROR: {error_msg}", flush=True)
        raise HTTPException(status_code=500, detail=error_msg)

    # Create authorization URL
    params = {
        "client_id": GMAIL_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id,  # Pass user_id as state for verification
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    print(f"[GMAIL AUTH] Generated auth URL for user {user_id}")

    return {
        "status": "success",
        "auth_url": auth_url
    }


@router.get("/callback")
async def gmail_callback(code: str, state: str):
    """
    Handle Google OAuth callback.

    Exchange authorization code for access/refresh tokens.
    Save tokens to database.
    Redirect to profile page.
    """
    from fastapi.responses import RedirectResponse

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    user_id = state  # state contains user_id from /auth request

    try:
        print(f"[GMAIL CALLBACK] Processing callback for user {user_id}")

        # Exchange authorization code for tokens
        token_data = {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        }

        response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        if response.status_code != 200:
            print(f"[GMAIL CALLBACK] Error from Google: {response.text}")
            raise Exception(f"Failed to exchange code for tokens: {response.text}")

        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)

        # Calculate token expiry
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        # Create Credentials object for Gmail API calls
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URL,
            client_id=GMAIL_CLIENT_ID,
            client_secret=GMAIL_CLIENT_SECRET
        )

        # Get user's email from Google
        user_email = _get_gmail_email(credentials)
        if not user_email:
            raise Exception("Failed to retrieve Gmail email address")

        print(f"[GMAIL CALLBACK] Got email: {user_email}")

        # Save tokens to database
        execute_update(
            """
            INSERT INTO gmail_tokens (user_id, access_token, refresh_token, token_expiry, email)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
              access_token = EXCLUDED.access_token,
              refresh_token = EXCLUDED.refresh_token,
              token_expiry = EXCLUDED.token_expiry,
              email = EXCLUDED.email,
              updated_at = NOW()
            """,
            (user_id, access_token, refresh_token, token_expiry, user_email)
        )

        print(f"[GMAIL CALLBACK] Tokens saved for user {user_id}")

        # Redirect to profile page (frontend will reload and show connected status)
        frontend_url = os.getenv("APP_BASE_URL", "http://localhost:3000")
        redirect_url = f"{frontend_url}/profile?gmail_connected=true"
        print(f"[GMAIL CALLBACK] Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        print(f"[GMAIL CALLBACK] ERROR: {type(e).__name__}: {str(e)}")
        frontend_url = os.getenv("APP_BASE_URL", "http://localhost:3000")
        error_url = f"{frontend_url}/profile?gmail_error={str(e)[:50]}"
        return RedirectResponse(url=error_url, status_code=302)


@router.get("/status")
async def gmail_status(user_id: str = Depends(get_user_id)):
    """
    Check if user has connected Gmail.

    Returns: { connected: bool, email: str | null, expires_at: datetime | null }
    """
    try:
        result = execute_query(
            """
            SELECT email, token_expiry FROM gmail_tokens WHERE user_id = %s
            """,
            (user_id,)
        )

        if result and result[0].get('email'):
            token_data = result[0]
            return {
                "status": "success",
                "connected": True,
                "email": token_data.get('email'),
                "expires_at": token_data.get('token_expiry')
            }
        else:
            return {
                "status": "success",
                "connected": False,
                "email": None,
                "expires_at": None
            }

    except Exception as e:
        print(f"[GMAIL STATUS] ERROR: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check Gmail status: {str(e)}")


@router.post("/disconnect")
async def gmail_disconnect(user_id: str = Depends(get_user_id)):
    """
    Disconnect Gmail from user account.

    Revokes access token and removes stored tokens from database.
    """
    try:
        print(f"[GMAIL DISCONNECT] Disconnecting Gmail for user {user_id}")

        # Get current access token
        result = execute_query(
            "SELECT access_token FROM gmail_tokens WHERE user_id = %s",
            (user_id,)
        )

        if result:
            access_token = result[0].get('access_token')
            if access_token:
                try:
                    # Revoke the access token
                    requests.post(
                        "https://oauth2.googleapis.com/revoke",
                        data={"token": access_token}
                    )
                    print(f"[GMAIL DISCONNECT] Access token revoked")
                except Exception as e:
                    print(f"[GMAIL DISCONNECT] Warning: Failed to revoke token: {str(e)}")

        # Delete tokens from database
        execute_update(
            "DELETE FROM gmail_tokens WHERE user_id = %s",
            (user_id,)
        )

        print(f"[GMAIL DISCONNECT] Gmail disconnected for user {user_id}")

        return {
            "status": "success",
            "message": "Gmail disconnected successfully"
        }

    except Exception as e:
        print(f"[GMAIL DISCONNECT] ERROR: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect Gmail: {str(e)}")


def _get_gmail_email(credentials: Credentials) -> Optional[str]:
    """
    Get user's email from Gmail API using Google's official client library.

    Uses Gmail API to retrieve the authenticated user's email address.
    """
    try:
        # Build Gmail service with credentials
        service = build('gmail', 'v1', credentials=credentials)

        # Get user profile (email)
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')

        if email:
            print(f"[GMAIL EMAIL] Retrieved email: {email}")
            return email
        else:
            print(f"[GMAIL EMAIL] No email found in profile")
            return None

    except Exception as e:
        print(f"[GMAIL EMAIL] ERROR: {type(e).__name__}: {str(e)}")
        return None


def get_gmail_tokens(user_id: str) -> Optional[dict]:
    """
    Retrieve stored Gmail tokens for a user.

    Returns: { access_token, refresh_token, token_expiry, email } or None
    """
    try:
        result = execute_query(
            "SELECT access_token, refresh_token, token_expiry, email FROM gmail_tokens WHERE user_id = %s",
            (user_id,)
        )

        if result:
            return result[0]
        return None

    except Exception as e:
        print(f"[GMAIL TOKENS] ERROR: {type(e).__name__}: {str(e)}")
        return None


def refresh_gmail_token(user_id: str) -> Optional[str]:
    """
    Refresh expired Gmail access token using refresh token.

    Returns new access_token or None if refresh fails.
    """
    try:
        tokens = get_gmail_tokens(user_id)
        if not tokens or not tokens.get('refresh_token'):
            print(f"[GMAIL REFRESH] No refresh token for user {user_id}")
            return None

        refresh_token = tokens.get('refresh_token')

        # Request new access token
        token_data = {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        if response.status_code != 200:
            print(f"[GMAIL REFRESH] Error: {response.text}")
            return None

        new_tokens = response.json()
        new_access_token = new_tokens.get("access_token")
        expires_in = new_tokens.get("expires_in", 3600)
        new_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        # Update database
        execute_update(
            """
            UPDATE gmail_tokens
            SET access_token = %s, token_expiry = %s, updated_at = NOW()
            WHERE user_id = %s
            """,
            (new_access_token, new_token_expiry, user_id)
        )

        print(f"[GMAIL REFRESH] Token refreshed for user {user_id}")
        return new_access_token

    except Exception as e:
        print(f"[GMAIL REFRESH] ERROR: {type(e).__name__}: {str(e)}")
        return None


@router.get("/check")
async def check_emails(user_id: str = Depends(get_user_id)):
    """
    Manually trigger email monitoring for the user.

    Checks Gmail inbox for replies from companies where user has applied.
    Returns list of emails found and their classified statuses.
    """
    try:
        print(f"[GMAIL CHECK] Manual email check requested by user {user_id}", flush=True)

        from tools.monitor_email import check_gmail_for_replies

        # Run email monitoring
        result = check_gmail_for_replies(user_id)

        if result.get("error"):
            print(f"[GMAIL CHECK] Error: {result['error']}", flush=True)
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "status": "success",
            "checked_at": result["checked_at"].isoformat(),
            "emails_found": result["emails_found"],
            "statuses_updated": result["statuses_updated"],
            "emails": result["emails"]
        }

    except Exception as e:
        print(f"[GMAIL CHECK] ERROR: {type(e).__name__}: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Email check failed: {str(e)}")
