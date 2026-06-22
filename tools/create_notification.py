"""Create user notification for job search events. Uses db.py and logger.py."""

from datetime import datetime
from tools.db import execute_update
from tools.logger import log_agent_run


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

        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='decision',
            status='success',
            details={'notification_type': type}
        )

    except Exception as e:
        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='decision',
            status='failed',
            details={'error': str(e)}
        )
        raise Exception(f"Failed to create notification: {str(e)}")
