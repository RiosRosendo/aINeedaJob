"""
Check if a job listing is still active by verifying the URL is reachable and not 404.

Uses both HTTP HEAD requests (fast) and fallback to full page fetch if needed.
Looks for "job closed", "no longer available", "expired", etc. in page content.
"""

import requests
from typing import Tuple


def check_job_still_active(job_url: str) -> Tuple[bool, str]:
    """
    Check if a job URL is still active and listing is available.

    Args:
        job_url: The full URL of the job listing

    Returns:
        (is_active: bool, reason: str)
        is_active=True if job is still available
        is_active=False if job is expired/closed/404
        reason: brief explanation ("404", "closed", "available", etc.)
    """
    if not job_url:
        return False, "no_url"

    try:
        print(f"[JOB_CHECK] Checking if job is still active: {job_url[:50]}...", flush=True)

        # First try: HEAD request (fast, minimal data)
        try:
            head_response = requests.head(job_url, timeout=5, allow_redirects=True)

            if head_response.status_code == 404:
                print(f"[JOB_CHECK] Job returned 404 - EXPIRED", flush=True)
                return False, "404"

            if head_response.status_code >= 500:
                print(f"[JOB_CHECK] Server error {head_response.status_code} - cannot determine", flush=True)
                return True, "server_error"  # Assume active on server error (temporary)

            if head_response.status_code >= 400:
                print(f"[JOB_CHECK] HTTP {head_response.status_code} - EXPIRED", flush=True)
                return False, f"http_{head_response.status_code}"

            if head_response.status_code == 200:
                print(f"[JOB_CHECK] Job returned 200 - ACTIVE", flush=True)
                return True, "available"

        except requests.exceptions.Timeout:
            print(f"[JOB_CHECK] HEAD request timed out, trying GET", flush=True)
            pass  # Fall through to GET request

        # Second try: Full GET request (if HEAD failed or for content check)
        get_response = requests.get(job_url, timeout=10)

        if get_response.status_code == 404:
            print(f"[JOB_CHECK] Job returned 404 - EXPIRED", flush=True)
            return False, "404"

        if get_response.status_code >= 500:
            print(f"[JOB_CHECK] Server error {get_response.status_code}", flush=True)
            return True, "server_error"

        if get_response.status_code >= 400:
            print(f"[JOB_CHECK] HTTP {get_response.status_code} - EXPIRED", flush=True)
            return False, f"http_{get_response.status_code}"

        # Check page content for "job closed" indicators
        content = get_response.text.lower()

        closed_indicators = [
            "job closed",
            "no longer available",
            "expired",
            "position filled",
            "this position",
            "has been closed",
            "application period",
            "job has expired",
            "this job is no longer",
            "closing date has passed",
        ]

        for indicator in closed_indicators:
            if indicator in content:
                print(f"[JOB_CHECK] Found '{indicator}' in page - EXPIRED", flush=True)
                return False, "closed_indicator"

        if get_response.status_code == 200:
            print(f"[JOB_CHECK] Job is ACTIVE (200, no closed indicators)", flush=True)
            return True, "available"

        return True, "unknown_status"

    except requests.exceptions.ConnectionError:
        print(f"[JOB_CHECK] Connection error - assuming active (temp network issue)", flush=True)
        return True, "connection_error"

    except requests.exceptions.Timeout:
        print(f"[JOB_CHECK] Timeout - assuming active (temp timeout)", flush=True)
        return True, "timeout"

    except Exception as e:
        print(f"[JOB_CHECK] Error checking job: {type(e).__name__}: {str(e)}", flush=True)
        return True, f"error_{type(e).__name__}"
