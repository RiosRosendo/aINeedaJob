"""
Trigger the next agent in the pipeline.

Currently: logs to agent_logs and prints to console.
Future: will connect to Celery task queue for async execution.

Example usage:
  from tools.trigger_agent import trigger_agent

  trigger_agent(
    agent_name='cv_tailoring',
    user_id='550e8400-...',
    job_id='550e8400-...',
    application_id='550e8400-...'
  )
"""

from datetime import datetime
from tools.logger import log_agent_run


def trigger_agent(agent_name, user_id, job_id, application_id=None):
    """
    Trigger the next agent in the pipeline.

    Args:
        agent_name (str): Name of agent to trigger (cv_tailoring, application, etc.)
        user_id (str): User ID
        job_id (str): Job ID
        application_id (str): Application ID (optional)

    Note:
        In V1, this logs and prints. In V2, will queue async Celery task.
    """
    try:
        # Log the trigger
        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            application_id=application_id,
            agent='trigger',
            status='triggered',
            details={'target_agent': agent_name}
        )

        # Print to console for visibility
        print(f"[{datetime.utcnow().isoformat()}] TRIGGER: {agent_name}")
        print(f"  user_id={user_id}, job_id={job_id}, application_id={application_id}")

        # TODO: In V2, enqueue Celery task here
        # from celery import app
        # app.send_task(f'agents.{agent_name}', args=[user_id, job_id, application_id])

    except Exception as e:
        print(f"[ERROR] Failed to trigger {agent_name}: {str(e)}")
        raise Exception(f"Failed to trigger agent {agent_name}: {str(e)}")
