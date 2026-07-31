"""Create user notification for job search events."""

from datetime import datetime
from tools.db import execute_update


def create_notification(user_id, type, message, job_id=None, expires_at=None):
    """Insert notification record. Raises exception if insert fails."""
    try:
        query = """
            INSERT INTO notifications (user_id, job_id, type, message, is_read, expires_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """

        params = (
            str(user_id),
            str(job_id) if job_id else None,
            type,
            message,
            False,
            expires_at,
        )

        execute_update(query, params)
        print(f"[NOTIFICATION] Created: type={type}, user={user_id}, job={job_id}")

    except Exception as e:
        print(f"[NOTIFICATION] Error: {str(e)}")
        raise Exception(f"Failed to create notification: {str(e)}")
