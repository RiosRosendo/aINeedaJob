"""
Logging utilities for aINeedJob agents.

Logs all agent runs to the agent_logs table for audit trail and debugging.
Every agent action is recorded: job discovery, parsing, matching, decision, etc.

Required environment variables:
  - DATABASE_URL: PostgreSQL connection string (handled by db.py)

Example usage:
  from tools.logger import log_agent_run

  log_agent_run(
    user_id='550e8400-e29b-41d4-a716-446655440000',
    agent='job_parsing',
    job_id='550e8400-e29b-41d4-a716-446655440001',
    status='success',
    details={'jobs_parsed': 5, 'parse_errors': 0}
  )
"""

import json
from datetime import datetime
from tools.db import execute_update


def log_agent_run(user_id, agent, job_id=None, status=None, details=None, application_id=None):
    """
    Log an agent run to the agent_logs table.

    Args:
        user_id (str/UUID): User ID
        agent (str): Agent name (job_discovery, job_parsing, job_match, decision,
                     cv_tailoring, application, email_monitoring, follow_up,
                     interview, salary, or career_memory)
        job_id (str/UUID): Job ID (optional)
        status (str): Run status - success, failed, skipped, pending (optional)
        details (dict): Agent-specific metadata as dictionary (optional)
        application_id (str/UUID): Application ID (optional)

    Raises:
        Exception: If logging fails (propagates db error)
    """
    try:
        details_json = json.dumps(details) if details else None

        query = """
            INSERT INTO agent_logs (user_id, agent, job_id, application_id, status, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            str(user_id),
            agent,
            str(job_id) if job_id else None,
            str(application_id) if application_id else None,
            status,
            details_json,
            datetime.utcnow(),
        )

        execute_update(query, params)
    except Exception as e:
        raise Exception(f"Failed to log agent run for {agent}: {str(e)}")
