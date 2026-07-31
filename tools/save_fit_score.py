"""
Save job fit score to database and update job status to 'scored'.

Inserts FitScore record with score, decision, strengths, gaps, summary.
Updates job status from 'parsed' to 'scored'.

Uses tools/db.py and tools/logger.py.

Example usage:
  from tools.save_fit_score import save_fit_score

  save_fit_score(
    job_id='550e8400-...',
    user_id='550e8400-...',
    fit_score_data={
      'score': 85,
      'decision': 'apply',
      'strengths': ['Strong Python skills', 'Remote role'],
      'gaps': ['No Kubernetes experience'],
      'summary': 'Excellent fit for your profile'
    }
  )
"""

import json
from tools.db import execute_update


def save_fit_score(job_id, user_id, fit_score_data):
    """Save fit score to database and update job status to 'scored'."""
    try:
        # Insert FitScore record
        query = """
            INSERT INTO fit_scores (job_id, user_id, score, decision, strengths, gaps, summary, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """

        params = (
            str(job_id),
            str(user_id),
            fit_score_data.get('score'),
            fit_score_data.get('decision'),
            json.dumps(fit_score_data.get('strengths', [])),
            json.dumps(fit_score_data.get('gaps', [])),
            fit_score_data.get('summary'),
        )

        execute_update(query, params)

        # Update job status to 'scored'
        update_query = "UPDATE jobs SET status = 'scored' WHERE id = %s AND user_id = %s"
        execute_update(update_query, (str(job_id), str(user_id)))

        print(f"[SAVE_FIT_SCORE] Saved score {fit_score_data.get('score')} for job {job_id} ({fit_score_data.get('decision')})")

    except Exception as e:
        print(f"[SAVE_FIT_SCORE] Error: {str(e)}")
        raise Exception(f"Failed to save fit score: {str(e)}")
