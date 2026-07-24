"""
Weekly summary agent - generates natural language summaries of user's job search progress.

Fetches data for the past 7 days and uses LLM to create actionable summary.
Stores summaries for historical tracking.
"""

import os
import json
from datetime import datetime, timedelta
from groq import Groq
from tools.db import execute_query, execute_update


def generate_weekly_summary(user_id: str) -> dict:
    """
    Generate a weekly summary of job search activity.

    Returns:
        {
            "summary_text": "narrative summary of the week",
            "stats": {
                "jobs_found": int,
                "jobs_scored": int,
                "applied": int,
                "interviews": int,
                "rejections": int,
                "pending_approval": int
            },
            "top_jobs": [
                {"title": "...", "company": "...", "score": 85, "status": "..."},
                ...
            ],
            "action_items": [
                "Approve 3 pending review jobs",
                "Follow up on rejected applications",
                ...
            ]
        }
    """
    try:
        print(f"[WEEKLY_SUMMARY] Generating summary for user {user_id}", flush=True)

        # Calculate date range: last 7 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        # Fetch stats for the week
        stats = _fetch_weekly_stats(user_id, start_date, end_date)
        top_jobs = _fetch_top_jobs(user_id, start_date, end_date)
        pending_approvals = _fetch_pending_approvals(user_id)

        print(f"[WEEKLY_SUMMARY] Stats: {stats}", flush=True)

        # Generate LLM summary
        summary_text = _generate_llm_summary(user_id, stats, top_jobs, pending_approvals)

        # Generate action items
        action_items = _generate_action_items(stats, pending_approvals)

        result = {
            "summary_text": summary_text,
            "stats": stats,
            "top_jobs": top_jobs,
            "action_items": action_items
        }

        # Save to database
        _save_summary(user_id, result)

        print(f"[WEEKLY_SUMMARY] Summary generated successfully", flush=True)
        return result

    except Exception as e:
        print(f"[WEEKLY_SUMMARY] Error generating summary: {type(e).__name__}: {str(e)}", flush=True)
        raise Exception(f"Failed to generate weekly summary: {str(e)}")


def _fetch_weekly_stats(user_id: str, start_date: datetime, end_date: datetime) -> dict:
    """Fetch statistics for the week."""
    try:
        # Total active jobs (all time, not just this week)
        # Uses same single source of truth as dashboard: SELECT COUNT(*) FROM jobs WHERE user_id=X AND expires_at IS NULL
        total_jobs = execute_query(
            """SELECT COUNT(*) as count FROM jobs
               WHERE user_id = %s AND expires_at IS NULL""",
            (user_id,)
        )

        # Jobs scored this week (only active verified jobs)
        jobs_scored = execute_query(
            """SELECT COUNT(*) as count FROM fit_scores
               WHERE user_id = %s AND created_at >= %s AND created_at <= %s
               AND job_id IN (SELECT id FROM jobs WHERE user_id = %s
                 AND expires_at IS NULL
                 AND (last_verified_at > NOW() - INTERVAL '7 days' OR created_at > NOW() - INTERVAL '7 days'))""",
            (user_id, start_date, end_date, user_id)
        )

        # Applications this week
        applications = execute_query(
            """SELECT status, COUNT(*) as count FROM applications
               WHERE user_id = %s AND created_at >= %s AND created_at <= %s
               GROUP BY status""",
            (user_id, start_date, end_date)
        )

        app_stats = {}
        for app in applications:
            app_stats[app.get('status')] = app.get('count', 0)

        # Total pending approvals (all time, not just this week - matches Approvals page)
        pending_total = execute_query(
            """SELECT COUNT(*) as count FROM applications
               WHERE user_id = %s AND status = 'pending_approval'""",
            (user_id,)
        )
        pending_approval_count = pending_total[0].get('count', 0) if pending_total else 0

        # Emails received this week (interview/offer/rejection)
        emails = execute_query(
            """SELECT status, COUNT(*) as count FROM applications
               WHERE user_id = %s AND updated_at >= %s AND updated_at <= %s
               AND status IN ('interview', 'offer', 'rejected')
               GROUP BY status""",
            (user_id, start_date, end_date)
        )

        email_stats = {}
        for email in emails:
            email_stats[email.get('status')] = email.get('count', 0)

        stats = {
            "jobs_found": total_jobs[0].get('count', 0) if total_jobs else 0,
            "jobs_scored": jobs_scored[0].get('count', 0) if jobs_scored else 0,
            "applied": app_stats.get('applied', 0),
            "interviews": email_stats.get('interview', 0),
            "rejections": email_stats.get('rejected', 0),
            "pending_approval": pending_approval_count
        }

        return stats

    except Exception as e:
        print(f"[WEEKLY_SUMMARY] Error fetching stats: {str(e)}", flush=True)
        return {
            "jobs_found": 0,
            "jobs_scored": 0,
            "applied": 0,
            "interviews": 0,
            "rejections": 0,
            "pending_approval": 0
        }


def _fetch_top_jobs(user_id: str, start_date: datetime, end_date: datetime) -> list:
    """Fetch top 3 jobs by score this week (only active verified jobs)."""
    try:
        results = execute_query(
            """SELECT j.title, j.company, fs.score, a.status
               FROM jobs j
               LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
               LEFT JOIN applications a ON j.id = a.job_id AND a.user_id = %s
               WHERE j.user_id = %s AND j.created_at >= %s AND j.created_at <= %s
               AND j.expires_at IS NULL
               AND (j.last_verified_at > NOW() - INTERVAL '7 days' OR j.created_at > NOW() - INTERVAL '7 days')
               ORDER BY fs.score DESC
               LIMIT 3""",
            (user_id, user_id, user_id, start_date, end_date)
        )

        top_jobs = []
        for job in results:
            top_jobs.append({
                "title": job.get('title', 'Unknown'),
                "company": job.get('company', 'Unknown'),
                "score": job.get('score') or 0,
                "status": job.get('status', 'pending')
            })

        return top_jobs

    except Exception as e:
        print(f"[WEEKLY_SUMMARY] Error fetching top jobs: {str(e)}", flush=True)
        return []


def _fetch_pending_approvals(user_id: str) -> int:
    """Fetch count of pending approval jobs."""
    try:
        result = execute_query(
            """SELECT COUNT(*) as count FROM applications
               WHERE user_id = %s AND status = 'pending_approval'""",
            (user_id,)
        )
        return result[0].get('count', 0) if result else 0

    except Exception as e:
        print(f"[WEEKLY_SUMMARY] Error fetching pending approvals: {str(e)}", flush=True)
        return 0


def _generate_llm_summary(user_id: str, stats: dict, top_jobs: list, pending_approvals: int) -> str:
    """Generate natural language summary using Groq LLM."""
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""You are a helpful career coach. Summarize this week's job search activity in a friendly, encouraging tone.

WEEKLY STATISTICS (showing only verified active jobs, excluding expired listings):
- Active jobs discovered: {stats.get('jobs_found', 0)}
- Active jobs scored: {stats.get('jobs_scored', 0)}
- Jobs applied to: {stats.get('applied', 0)}
- Interviews scheduled: {stats.get('interviews', 0)}
- Rejections: {stats.get('rejections', 0)}
- Pending your approval: {stats.get('pending_approval', 0)}

NOTE: The system autonomously verifies job freshness weekly and removes expired listings (> 30 days old or 404 URLs). This keeps your pipeline clean and focused on real opportunities.

TOP JOBS THIS WEEK:
{_format_top_jobs(top_jobs)}

Write a 2-3 sentence summary that:
1. Acknowledges the week's activity with verified active jobs
2. Highlights any wins (applications, interviews, etc.)
3. Mentions job verification/cleanup if relevant
4. Is encouraging and positive

Keep it concise and actionable."""

        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )

        summary = response.choices[0].message.content.strip()
        print(f"[WEEKLY_SUMMARY] Generated summary: {summary[:100]}...", flush=True)
        return summary

    except Exception as e:
        print(f"[WEEKLY_SUMMARY] Error generating LLM summary: {str(e)}", flush=True)
        # Fallback summary
        return f"This week, you discovered {stats.get('jobs_found', 0)} jobs, applied to {stats.get('applied', 0)}, and have {stats.get('pending_approval', 0)} jobs awaiting your approval. Keep up the momentum!"


def _format_top_jobs(top_jobs: list) -> str:
    """Format top jobs for LLM prompt."""
    if not top_jobs:
        return "No jobs scored this week yet."

    formatted = []
    for job in top_jobs:
        formatted.append(f"- {job['title']} at {job['company']} (Fit: {job['score']}%)")

    return "\n".join(formatted)


def _generate_action_items(stats: dict, pending_approvals: int) -> list:
    """Generate actionable recommendations."""
    items = []

    if pending_approvals > 0:
        items.append(f"Review and approve {pending_approvals} pending jobs that match your criteria")

    if stats.get('interviews', 0) > 0:
        items.append(f"Prepare for {stats['interviews']} upcoming interview(s)")

    if stats.get('rejections', 0) > 0:
        items.append(f"Review feedback from {stats['rejections']} rejection(s) to improve future applications")

    if stats.get('applied', 0) == 0 and stats.get('jobs_found', 0) > 0:
        items.append("Apply to more jobs - browse your pending approvals and increase your application rate")

    if not items:
        items.append("Keep searching! Browse new job opportunities and continue building your pipeline")

    return items


def _save_summary(user_id: str, summary_data: dict):
    """Save summary to database."""
    try:
        query = """
            INSERT INTO weekly_summaries (user_id, summary_text, stats, top_jobs, action_items, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        params = (
            user_id,
            summary_data.get('summary_text'),
            json.dumps(summary_data.get('stats', {})),
            json.dumps(summary_data.get('top_jobs', [])),
            json.dumps(summary_data.get('action_items', []))
        )

        execute_update(query, params)
        print(f"[WEEKLY_SUMMARY] Summary saved to database", flush=True)

    except Exception as e:
        print(f"[WEEKLY_SUMMARY] Error saving summary: {str(e)}", flush=True)
        # Don't raise - summary generation was successful, just couldn't save
