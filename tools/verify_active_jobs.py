"""
Autonomous job verification agent - checks if job URLs are still active.

Runs weekly to verify jobs 7-30 days old that haven't been marked as expired.
Updates last_verified_at timestamp for active jobs, marks expired ones.
Processes in batches to avoid overwhelming servers.
"""

from tools.db import execute_query, execute_update
from tools.check_job_active import check_job_still_active
from datetime import datetime, timedelta
import json


def verify_active_jobs() -> dict:
    """
    Verify all jobs 7-30 days old for all users.

    Returns:
        {
            "total_checked": int,
            "still_active": int,
            "newly_expired": int,
            "errors": int
        }
    """
    try:
        print("[VERIFY_JOBS] Starting autonomous job verification for all users...", flush=True)

        # Calculate date range: 7-30 days old
        now = datetime.utcnow()
        cutoff_recent = now - timedelta(days=7)  # Less than 7 days ago (too recent)
        cutoff_old = now - timedelta(days=30)    # More than 30 days ago (too old)

        # Fetch jobs 7-30 days old that haven't been marked as expired yet
        jobs_to_verify = execute_query(
            """
            SELECT id, user_id, url, created_at
            FROM jobs
            WHERE created_at >= %s
              AND created_at <= %s
              AND expires_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1000
            """,
            (cutoff_old, cutoff_recent)
        )

        if not jobs_to_verify:
            print("[VERIFY_JOBS] No jobs to verify in the 7-30 day window", flush=True)
            return {
                "total_checked": 0,
                "still_active": 0,
                "newly_expired": 0,
                "errors": 0
            }

        total_jobs = len(jobs_to_verify)
        still_active = 0
        newly_expired = 0
        errors = 0

        print(f"[VERIFY_JOBS] Found {total_jobs} jobs to verify (7-30 days old)", flush=True)

        # Process in batches of 50
        batch_size = 50
        for batch_idx in range(0, total_jobs, batch_size):
            batch = jobs_to_verify[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            batch_total = (total_jobs + batch_size - 1) // batch_size

            print(f"[VERIFY_JOBS] Processing batch {batch_num}/{batch_total} ({len(batch)} jobs)...", flush=True)

            for job in batch:
                job_id = job.get('id')
                user_id = job.get('user_id')
                url = job.get('url')
                created_at = job.get('created_at')

                if not url:
                    print(f"[VERIFY_JOBS] Job {job_id}: No URL, skipping", flush=True)
                    continue

                try:
                    # Check if URL is still active
                    is_active, reason = check_job_still_active(url)

                    if is_active:
                        # Mark as verified
                        execute_update(
                            "UPDATE jobs SET last_verified_at = %s WHERE id = %s",
                            (now, job_id)
                        )

                        # Log to agent_logs
                        try:
                            execute_update(
                                """
                                INSERT INTO agent_logs (user_id, job_id, agent, status, details)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (
                                    user_id,
                                    job_id,
                                    "job_verification",
                                    "success",
                                    json.dumps({"reason": reason, "verified": True})
                                )
                            )
                        except:
                            pass  # Log failure is non-critical

                        still_active += 1
                        print(f"[VERIFY_JOBS] Job {job_id}: ACTIVE (reason: {reason})", flush=True)

                    else:
                        # Mark as expired
                        expires_at = created_at + timedelta(days=30)
                        execute_update(
                            "UPDATE jobs SET expires_at = %s WHERE id = %s",
                            (expires_at, job_id)
                        )

                        # Log to agent_logs
                        try:
                            execute_update(
                                """
                                INSERT INTO agent_logs (user_id, job_id, agent, status, details)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (
                                    user_id,
                                    job_id,
                                    "job_verification",
                                    "expired",
                                    json.dumps({"reason": reason, "verified": False})
                                )
                            )
                        except:
                            pass  # Log failure is non-critical

                        newly_expired += 1
                        print(f"[VERIFY_JOBS] Job {job_id}: EXPIRED (reason: {reason})", flush=True)

                except Exception as e:
                    errors += 1
                    print(f"[VERIFY_JOBS] Job {job_id}: ERROR - {type(e).__name__}: {str(e)}", flush=True)

                    # Log error
                    try:
                        execute_update(
                            """
                            INSERT INTO agent_logs (user_id, job_id, agent, status, details)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                user_id,
                                job_id,
                                "job_verification",
                                "error",
                                json.dumps({"error": str(e)})
                            )
                        )
                    except:
                        pass

        result = {
            "total_checked": total_jobs,
            "still_active": still_active,
            "newly_expired": newly_expired,
            "errors": errors
        }

        print(f"[VERIFY_JOBS] Verification complete: {still_active} active, {newly_expired} newly expired, {errors} errors", flush=True)
        return result

    except Exception as e:
        print(f"[VERIFY_JOBS] FATAL ERROR: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        return {
            "total_checked": 0,
            "still_active": 0,
            "newly_expired": 0,
            "errors": 1
        }
