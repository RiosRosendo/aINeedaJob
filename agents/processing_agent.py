"""
Processing Agent - batch job parsing, scoring, and decision routing.

Handles the Processing phase of the WAT pipeline:
- Filters out irrelevant titles (before expensive LLM calls)
- Parses job descriptions (extract salary, skills, location, etc.)
- Scores jobs against user profile (0-100 fit score)
- Checks work eligibility (visa requirements, remote eligibility)
- Routes jobs to three tiers: auto-apply (85+), user review (60-84), ignore (<60)

Processes up to 30 jobs per batch to balance throughput vs rate limits.
"""

from datetime import datetime, timedelta
from agents.state import JobState, SCORE_THRESHOLDS
from tools.db import execute_query, execute_update
from tools.llm import call_llm
from tools.parse_job import parse_job
from tools.update_job import update_job
from tools.score_job import score_job
from tools.save_fit_score import save_fit_score
from tools.check_eligibility import check_work_eligibility
from tools.create_notification import create_notification
from tools.apply_job import apply_for_job_sync
from tools.verify_active_jobs import check_job_still_active
import time
import json

BATCH_DELAY = 0.5  # Seconds between jobs to avoid rate limiting


def _perform_llm_driven_cleanup(job_id: str, user_id: str, job_data: dict) -> None:
    """
    LLM autonomously decides cleanup actions for expired jobs.

    Evaluates job context (application status, user interaction) and decides:
    - Should fit_scores be deleted?
    - Should applications be deleted or kept for tracking?
    - What additional cleanup is needed?

    Tools Called:
    - call_llm(): Groq LLM for cleanup decision
    - execute_update(): Execute cleanup actions

    Args:
        job_id (str): Job ID that expired
        user_id (str): User ID who discovered the job
        job_data (dict): Job data from discovery
    """
    try:
        # Fetch job and application context
        job_full = execute_query("SELECT * FROM jobs WHERE id = %s AND user_id = %s", (job_id, user_id))
        application = execute_query(
            "SELECT status FROM applications WHERE job_id = %s AND user_id = %s ORDER BY created_at DESC LIMIT 1",
            (job_id, user_id)
        )
        fit_score = execute_query(
            "SELECT score, decision FROM fit_scores WHERE job_id = %s AND user_id = %s",
            (job_id, user_id)
        )

        job_info = job_full[0] if job_full else {}
        app_status = application[0]['status'] if application else None
        fit_info = fit_score[0] if fit_score else {}

        prompt = f"""You are an autonomous job database cleanup manager.

A job posting has been verified as EXPIRED (no longer available).

JOB CONTEXT:
- Job ID: {job_id}
- Title: {job_info.get('title', 'unknown')}
- Company: {job_info.get('company', 'unknown')}

APPLICATION CONTEXT:
- Application Status: {app_status or 'none'}
- Fit Score: {fit_info.get('score', 'N/A')}
- Fit Decision: {fit_info.get('decision', 'N/A')}

CLEANUP DECISION:
Should we clean up this job's data? Consider:
- If user applied/has application: KEEP application for tracking (don't delete)
- If no application or status is pending: can DELETE application
- Always evaluate fit_scores: keep if relevant to user's search, delete if low relevance
- Expired jobs themselves are already marked expires_at = NOW()

Return ONLY valid JSON (no markdown):
{{
  "delete_fit_scores": boolean,  # true if fit_scores should be deleted, false to keep
  "delete_applications": boolean,  # true if pending applications should be deleted
  "reason": "brief explanation"
}}"""

        response = call_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        decision = json.loads(response)

        print(f"[CLEANUP] Job {job_id}: LLM decided - fit_scores={decision.get('delete_fit_scores')}, apps={decision.get('delete_applications')}", flush=True)

        # Execute cleanup decisions
        if decision.get('delete_fit_scores'):
            try:
                execute_update("DELETE FROM fit_scores WHERE job_id = %s", (job_id,))
                print(f"[CLEANUP] Job {job_id}: Deleted fit_scores", flush=True)
            except Exception as e:
                print(f"[CLEANUP] Job {job_id}: Failed to delete fit_scores - {str(e)}", flush=True)

        if decision.get('delete_applications'):
            try:
                # Only delete pending applications, keep applied/in-review/offer
                execute_update(
                    "DELETE FROM applications WHERE job_id = %s AND status IN ('pending_approval', 'pending_application')",
                    (job_id,)
                )
                print(f"[CLEANUP] Job {job_id}: Deleted pending applications", flush=True)
            except Exception as e:
                print(f"[CLEANUP] Job {job_id}: Failed to delete applications - {str(e)}", flush=True)

    except Exception as e:
        print(f"[CLEANUP] Job {job_id}: LLM cleanup decision failed - {str(e)}", flush=True)


def verification_node(state: JobState) -> JobState:
    """
    Autonomous job verification node in LangGraph pipeline.

    Agent Role: VERIFICATION NODE in WAT framework

    Verifies that discovered job URLs are still active before processing:
    1. Reads unprocessed jobs from discovery_node
    2. For each job not verified in last 24 hours: checks if URL is active
    3. Marks dead jobs as expired (expires_at = NOW())
    4. Returns only active jobs to processing_node

    No hardcoded rules - LangGraph manages flow, verification is deterministic.

    Tools Called:
    - check_job_still_active(): HTTP check if URL responds with job content
    - execute_update(): Mark expired jobs in database

    Args:
        state (JobState): Pipeline state with raw_jobs from discovery_node

    Returns:
        JobState: Updated state with only active jobs in unprocessed_jobs
    """
    user_id = state.get("user_id")
    raw_jobs = state.get("raw_jobs", [])

    if not user_id or not raw_jobs:
        print(f"[VERIFICATION] No jobs to verify")
        state["unprocessed_jobs"] = []
        return state

    now = datetime.utcnow()
    active_jobs = []
    expired_count = 0
    urls_checked = 0
    max_url_checks = 5  # Rate limit: max 5 URL checks per batch to avoid overwhelming job boards

    print(f"[VERIFICATION] Verifying {len(raw_jobs)} jobs for user {user_id}", flush=True)

    for job_data in raw_jobs:
        job_id = job_data.get("id")
        url = job_data.get("url")
        last_verified = job_data.get("last_verified_at")

        # Skip if verified in last 24 hours
        if last_verified:
            hours_since_verified = (now - last_verified).total_seconds() / 3600 if hasattr(last_verified, 'total_seconds') else (now - last_verified.replace(tzinfo=None)).total_seconds() / 3600
            if hours_since_verified < 24:
                print(f"[VERIFICATION] Job {job_id}: SKIP - verified {hours_since_verified:.1f}h ago", flush=True)
                active_jobs.append(job_data)
                continue

        # Check if URL is still active
        if not url:
            print(f"[VERIFICATION] Job {job_id}: SKIP - no URL", flush=True)
            active_jobs.append(job_data)
            continue

        # Rate limit: skip URL check if already checked max_url_checks
        if urls_checked >= max_url_checks:
            print(f"[VERIFICATION] Job {job_id}: SKIP - rate limit reached ({urls_checked}/{max_url_checks})", flush=True)
            active_jobs.append(job_data)
            continue

        try:
            urls_checked += 1
            is_active, reason = check_job_still_active(url)

            if is_active:
                print(f"[VERIFICATION] Job {job_id}: ACTIVE (reason: {reason})", flush=True)
                # Update last_verified_at
                try:
                    execute_update(
                        "UPDATE jobs SET last_verified_at = %s WHERE id = %s",
                        (now, job_id)
                    )
                except:
                    pass
                active_jobs.append(job_data)
            else:
                print(f"[VERIFICATION] Job {job_id}: EXPIRED (reason: {reason})", flush=True)
                # Mark as expired
                try:
                    execute_update(
                        "UPDATE jobs SET expires_at = %s WHERE id = %s",
                        (now, job_id)
                    )
                except:
                    pass

                # LLM decides cleanup actions based on job context
                _perform_llm_driven_cleanup(job_id, user_id, job_data)
                expired_count += 1

        except Exception as e:
            print(f"[VERIFICATION] Job {job_id}: ERROR - {type(e).__name__}: {str(e)}", flush=True)
            # On error, assume active and let processing handle it
            active_jobs.append(job_data)

    print(f"[VERIFICATION] Complete: {len(active_jobs)} active, {expired_count} expired, {urls_checked} URL checks performed", flush=True)
    state["unprocessed_jobs"] = active_jobs
    return state


def processing_node(state: JobState) -> JobState:
    """
    Batch process all unprocessed jobs: filter → parse → score → decide → route.

    Agent Role: PROCESSING AGENT in WAT framework

    Executes the scoring pipeline on up to 30 unprocessed jobs per batch:
    1. Skip checks: already scored? expired? irrelevant title?
    2. Parse job description (extract structured data)
    3. Score against user profile (0-100)
    4. Check work eligibility (visa, remote suitability)
    5. Route to three tiers based on score:
       - 85+: auto-apply (attempt to submit via Workable/Ashby APIs)
       - 60-84: pending_approval (notify user for manual review)
       - <60: ignored (skip entirely)
    6. Create application records with current status

    Important: Jobs are user-scoped. The same job URL can exist for multiple users
    with different fit_scores, applications, and processing status. This allows
    sharing of job catalog across users while maintaining per-user evaluations.

    Tools Called:
    - _is_title_relevant(): LLM title filtering (before parse/score LLM calls)
    - parse_job(): Groq LLM for structured extraction
    - update_job(): Save parsed fields to jobs table
    - score_job(): Groq LLM for fit scoring
    - save_fit_score(): Insert/update fit_scores table
    - check_work_eligibility(): LLM-based visa/eligibility assessment
    - apply_for_job_sync(): Workable/Ashby API submission (for auto-apply tier)
    - create_notification(): Insert user-in-the-loop notification

    Args:
        state (JobState): Pipeline state with unprocessed_jobs, user_id, profile, roles

    Returns:
        JobState: Updated state with processed/applied/review/ignored counts and summary
    """
    user_id = state.get("user_id")
    unprocessed = state.get("unprocessed_jobs", [])
    profile = state.get("profile")
    roles = state.get("roles", [])

    state["processed_count"] = 0
    state["applied_count"] = 0
    state["review_count"] = 0
    state["ignored_count"] = 0

    if not user_id or not unprocessed:
        print(f"[PROCESSING] No jobs to process")
        state["summary"] = {
            "total_processed": 0,
            "applied": 0,
            "review": 0,
            "ignored": 0,
        }
        return state

    # Limit to batch_size from state, default 30 to prevent hanging on large queues
    batch_size = state.get('batch_size', 30)
    unprocessed = unprocessed[:batch_size]
    print(f"[PROCESS DEBUG] Found {len(unprocessed)} unprocessed jobs for user {user_id}")
    print(f"[PROCESSING] Processing {len(unprocessed)} jobs for user {user_id}")

    profile_full = execute_query("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
    if not profile_full:
        state["error"] = "User profile not found"
        return state

    for job_data in unprocessed:
        job_id = job_data.get("id")
        title = job_data.get("title")

        try:
            # CHECK: Skip if already scored
            existing_score = execute_query(
                "SELECT id FROM fit_scores WHERE job_id = %s AND user_id = %s",
                (job_id, user_id)
            )
            if existing_score:
                print(f"[PROCESS DEBUG] Job {job_id}: SKIP - already scored")
                continue

            # CHECK: Skip if job is expired (older than 30 days)
            job_created = job_data.get("created_at")
            if job_created:
                now = datetime.utcnow()
                job_age_days = (now - job_created).days if hasattr(job_created, 'days') else (now - job_created.replace(tzinfo=None)).days
                if job_age_days > 30:
                    print(f"[PROCESS DEBUG] Job {job_id}: SKIP - expired (created {job_age_days} days ago)")
                    # Mark as expired and scored in database
                    try:
                        execute_update(
                            "UPDATE jobs SET expires_at = %s, status = 'scored' WHERE id = %s",
                            (job_created + timedelta(days=30), job_id)
                        )
                    except:
                        pass
                    state["ignored_count"] += 1
                    continue

            # FILTER: Check if title is relevant (before any LLM scoring calls)
            if not _is_title_relevant(title, roles):
                print(f"[PROCESS DEBUG] Job {job_id}: SKIP - title '{title}' not relevant to {roles}")
                _mark_as_ignored(job_id, user_id)
                state["ignored_count"] += 1
                continue

            # PARSE: Extract structured fields from description
            print(f"[PARSING] Job {job_id}: '{title}'")
            try:
                parsed = parse_job(job_id, user_id, job_data.get("description_raw", ""), original_title=title)
                update_job(job_id, user_id, parsed)
            except Exception as e:
                # If parsing fails (e.g., groq not available), mark as processed and skip
                print(f"[PROCESS DEBUG] Job {job_id}: SKIP - parse failed: {str(e)[:60]}")
                # Mark as processed so it won't be retried endlessly
                try:
                    execute_update(
                        "UPDATE jobs SET status = 'scored' WHERE id = %s AND user_id = %s",
                        (job_id, user_id)
                    )
                except Exception:
                    pass
                state["ignored_count"] += 1
                continue

            # SCORE: Calculate fit score
            job_full = execute_query("SELECT * FROM jobs WHERE id = %s AND user_id = %s", (job_id, user_id))
            if not job_full:
                print(f"[PROCESS DEBUG] Job {job_id}: SKIP - job not found in database")
                continue

            print(f"[SCORING] Job {job_id}")
            fit_score = score_job(job_id, user_id, job_full[0], profile_full[0])
            save_fit_score(job_id, user_id, fit_score)

            # Job successfully scored - count as processed
            state["processed_count"] += 1

            # CHECK: Work eligibility for on-site positions
            print(f"[ELIGIBILITY] Checking work eligibility for job {job_id}")
            eligibility_result = check_work_eligibility(user_id, job_id)

            # Store eligibility info on job record
            eligibility_note = {
                "eligible": eligibility_result.get("eligible"),
                "confidence": eligibility_result.get("confidence"),
                "reason": eligibility_result.get("reason"),
                "visa_required": eligibility_result.get("visa_required"),
                "visa_type": eligibility_result.get("visa_type"),
                "recommendation": eligibility_result.get("recommendation")
            }

            # Update job with eligibility info
            try:
                execute_update(
                    "UPDATE jobs SET eligibility_note = %s WHERE id = %s",
                    (json.dumps(eligibility_note), job_id)
                )
            except Exception as e:
                print(f"[ELIGIBILITY] Warning - could not save eligibility note: {str(e)}", flush=True)

            # Adjust fit score if not eligible or visa required
            if not eligibility_result.get("eligible"):
                print(f"[ELIGIBILITY] Job {job_id}: NOT ELIGIBLE - reducing score to 0")
                fit_score["score"] = 0
                fit_score["decision"] = "ignore"
                # Update the saved fit score
                execute_update(
                    "UPDATE fit_scores SET score = %s, decision = %s WHERE job_id = %s AND user_id = %s",
                    (0, "ignore", job_id, user_id)
                )
            elif eligibility_result.get("visa_required"):
                # Reduce score by 20 points if visa is required (adds complexity)
                original_score = fit_score.get("score", 0)
                reduced_score = max(0, original_score - 20)
                print(f"[ELIGIBILITY] Job {job_id}: Visa required - reducing score from {original_score} to {reduced_score}")
                fit_score["score"] = reduced_score
                execute_update(
                    "UPDATE fit_scores SET score = %s WHERE job_id = %s AND user_id = %s",
                    (reduced_score, job_id, user_id)
                )

            # DECIDE: Route based on score
            decision = fit_score.get("decision", "ignore")
            score = fit_score.get("score", 0)

            # Override decision based on score thresholds (score always determines routing)
            if score >= SCORE_THRESHOLDS["auto_apply"]:
                decision = "apply"
            elif score >= SCORE_THRESHOLDS["review"]:
                decision = "review"
            else:
                decision = "ignore"

            # Create application record first
            app_result = execute_query(
                "INSERT INTO applications (job_id, user_id, status) VALUES (%s, %s, %s) RETURNING id",
                (job_id, user_id, "pending_application")
            )

            if not app_result:
                print(f"[ERROR] Failed to create application for job {job_id}")
                state["ignored_count"] += 1
                continue

            application_id = app_result[0].get('id')

            if decision == "apply":
                # Get job URL for application
                job_url_result = execute_query(
                    "SELECT url FROM jobs WHERE id = %s",
                    (job_id,)
                )
                job_url = job_url_result[0].get('url') if job_url_result else None

                if job_url:
                    try:
                        print(f"[AUTO_APPLY] Starting auto-apply for job {job_id}")
                        # Attempt autonomous application
                        apply_result = apply_for_job_sync(user_id, job_id, application_id, job_url, None)

                        if apply_result.get("status") == "applied":
                            status = "applied"
                            print(f"[AUTO_APPLY] Success for job {job_id}: {apply_result.get('method')}")
                        else:
                            status = "requires_manual"
                            print(f"[AUTO_APPLY] Manual required for job {job_id}: {apply_result.get('action')}")

                        state["applied_count"] += 1

                    except Exception as e:
                        print(f"[AUTO_APPLY] Error for job {job_id}: {str(e)}")
                        status = "requires_manual"
                        state["applied_count"] += 1
                else:
                    print(f"[AUTO_APPLY] No URL found for job {job_id}, marking as pending")
                    status = "pending_application"
                    state["applied_count"] += 1

                # Update application status
                execute_update(
                    "UPDATE applications SET status = %s, updated_at = NOW() WHERE id = %s",
                    (status, application_id)
                )
                print(f"[DECISION] Job {job_id} → {status} (score: {score}%)")

            elif decision == "review":
                status = "pending_approval"
                # Update application status for review tier
                execute_update(
                    "UPDATE applications SET status = %s, updated_at = NOW() WHERE id = %s",
                    (status, application_id)
                )
                create_notification(user_id, "approval_required",
                                  f"Job matching {score}% needs approval", job_id,
                                  datetime.utcnow() + timedelta(hours=48))
                state["review_count"] += 1
                print(f"[DECISION] Job {job_id} → {status} (score: {score}%)")

            else:
                status = "ignored"
                # Update application status for ignored tier
                execute_update(
                    "UPDATE applications SET status = %s, updated_at = NOW() WHERE id = %s",
                    (status, application_id)
                )
                state["ignored_count"] += 1
                print(f"[DECISION] Job {job_id} → {status} (score: {score}%)")

            # Small delay between jobs to avoid rate limiting
            time.sleep(BATCH_DELAY)

        except Exception as e:
            print(f"[PROCESS DEBUG] Job {job_id}: SKIP - unexpected error: {str(e)[:80]}")
            state["ignored_count"] += 1
            # Still delay even on error
            time.sleep(BATCH_DELAY)

    # Create summary
    state["summary"] = {
        "total_processed": state["processed_count"],
        "applied": state["applied_count"],
        "review": state["review_count"],
    }

    print(f"[PROCESS DEBUG] Breakdown: processed={state['processed_count']}, applied={state['applied_count']}, review={state['review_count']}, ignored={state['ignored_count']}")
    print(f"[PROCESSING COMPLETE] Summary: {state['summary']}")
    return state


def _is_title_relevant(title: str, roles: list) -> bool:
    """
    Check if job title is relevant to target roles using LLM.

    Agent Role: Helper for PROCESSING AGENT

    Performs fast LLM-based title filtering BEFORE expensive parse/score calls.
    Filters out clearly irrelevant jobs to save API calls and throughput.

    Language-agnostic: works for English, Spanish, French, German, Japanese, etc.
    Uses LLM to understand semantic relevance, not just keyword matching.

    Tools Called:
    - call_llm(): Groq LLM for title relevance assessment

    Args:
        title (str): Job title from job posting
        roles (list): User's target roles (e.g., ["AI Engineer", "Robotics Engineer"])

    Returns:
        bool: True if title is relevant to target roles, False if clearly irrelevant
    """
    if not title or not roles:
        return True

    try:
        roles_str = ", ".join(roles)
        prompt = f"""Is this job title DIRECTLY relevant to robotics, embedded systems, computer vision, AI/ML engineering, or autonomous systems?

Job Title: {title}
Target Roles: {roles_str}

STRICT RULES:
- REJECT generic engineering titles: Controls Engineer, Process Engineer, Manufacturing Engineer, Quality Engineer, Civil Engineer, Mechanical Engineer, Industrial Engineer, Systems Engineer (unless robotics-specific)
- REJECT titles containing: Controls, Process, Manufacturing, Quality, Civil, Industrial, Facilities, Operations
- ACCEPT titles containing: Robotics, Embedded, Autonomous, Vision, AI, ML, ROS, Computer Vision, Deep Learning, Neural, Firmware
- Abbreviations: Sr., Sr, Senior must still meet strict rules (Sr. Controls Engineer = NO, Sr. Robotics Engineer = YES)

Answer only YES or NO."""

        response = call_llm(prompt).strip().upper()

        # Check if response starts with YES
        is_relevant = response.startswith("YES")

        print(f"[TITLE_RELEVANCE] '{title}' → {response} (relevant={is_relevant})")

        return is_relevant

    except Exception as e:
        print(f"[TITLE_RELEVANCE] LLM error for '{title}': {str(e)}, defaulting to True")
        # On error, assume relevant (better to parse and score than skip)
        return True


def _mark_as_ignored(job_id: str, user_id: str) -> bool:
    """
    Mark job as ignored without scoring.

    Agent Role: Helper for PROCESSING AGENT

    Immediately marks a job with status='scored' so it won't appear in future
    unprocessed queries. Also creates application and fit_score records with
    ignored status for audit trail.

    Used when title filtering rejects a job before any LLM parsing/scoring calls.

    Tools Called:
    - execute_update(): Mark job status='scored' and eligibility info
    - execute_query(): Create ignored application and fit_score records

    Args:
        job_id (str): Job ID to mark as ignored
        user_id (str): User ID (for scoping)

    Returns:
        bool: True if successfully marked, False if error
    """
    try:
        # Update job status to 'scored' so it won't appear in unprocessed jobs query again
        execute_update(
            "UPDATE jobs SET status = 'scored' WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

        # Create application with ignored status
        try:
            execute_query(
                "INSERT INTO applications (job_id, user_id, status) VALUES (%s, %s, %s)",
                (job_id, user_id, "ignored")
            )
        except Exception:
            # Application already exists, skip
            pass

        # Create fit_score with 0 score
        try:
            execute_query(
                """
                INSERT INTO fit_scores (job_id, user_id, score, decision, strengths, gaps)
                VALUES (%s, %s, 0, %s, %s, %s)
                """,
                (job_id, user_id, "ignore", [], [])
            )
        except Exception:
            # Fit score already exists, skip
            pass

        return True
    except Exception as e:
        print(f"[ERROR] Failed to mark job {job_id} as ignored: {e}")
        return False
