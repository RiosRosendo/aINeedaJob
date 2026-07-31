"""Update application status and optional fields."""

from datetime import datetime
from tools.db import execute_update

VALID_STATUSES = {
    'pending_approval',
    'pending_application',
    'applied',
    'ignored',
    'job_expired',
    'requires_manual',
    'documents_ready',
}


def update_application(application_id, user_id, status, extra_fields=None):
    """Update application status and optional fields."""
    try:
        if status not in VALID_STATUSES:
            raise Exception(f"Invalid status: {status}")
        extra_fields = extra_fields or {}
        set_clauses = ["status = %s"]
        params = [status]
        field_map = {
            'applied_at': 'applied_at',
            'cv_version_url': 'cv_version_url',
            'cover_letter_url': 'cover_letter_url',
            'last_followup_at': 'last_followup_at',
            'followup_count': 'followup_count'
        }
        for key, col in field_map.items():
            if extra_fields.get(key) is not None:
                set_clauses.append(f"{col} = %s")
                params.append(extra_fields[key])
        params.extend([str(application_id), str(user_id)])
        query = f"UPDATE applications SET {', '.join(set_clauses)} WHERE id = %s AND user_id = %s"
        rows = execute_update(query, tuple(params))

        if rows == 0:
            raise Exception(f"Application {application_id} not found or user mismatch")

        print(f"[UPDATE_APP] Status updated to {status} for application {application_id}")

    except Exception as e:
        print(f"[UPDATE_APP] Error: {str(e)}")
        raise Exception(f"Failed to update application: {str(e)}")
