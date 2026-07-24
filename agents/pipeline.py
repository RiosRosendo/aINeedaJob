"""
LangGraph pipeline orchestrating the V1 job search workflow.

Batch processing: Discovery → Process ALL unprocessed jobs → Summary
Processes all unprocessed jobs with title filtering to avoid irrelevant results.
"""

from typing import TypedDict, Literal
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from tools.db import execute_query, execute_update
from tools.search_adzuna import search_adzuna
from tools.search_themuse import search_themuse
from tools.search_jobicy import search_jobicy_jobs
from tools.search_remotive import search_remotive_jobs
from tools.search_occ import search_occ_for_mexico
from tools.save_jobs import save_jobs
from tools.check_job_active import check_job_still_active
from tools.check_eligibility import check_work_eligibility
from tools.parse_job import parse_job
from tools.update_job import update_job
from tools.score_job import score_job
from tools.save_fit_score import save_fit_score
from tools.update_application import update_application
from tools.create_notification import create_notification
from tools.trigger_agent import trigger_agent
from tools.llm import call_llm
from tools.apply_job import apply_for_job_sync
import asyncio
import time

BATCH_DELAY = 0.5  # Seconds to wait between processing each job to avoid rate limits


# Country name to Adzuna country code mappings
COUNTRY_CODE_MAP = {
    "united states": "us",
    "us": "us",
    "usa": "us",
    "america": "us",
    "canada": "ca",
    "germany": "de",
    "france": "fr",
    "japan": "jp",
    "mexico": "mx",
    "italy": "it",
    "uae": "ae",
    "united arab emirates": "ae",
    "china": "cn",
    "uk": "gb",
    "united kingdom": "gb",
    "australia": "au",
    "india": "in",
    "singapore": "sg",
    "netherlands": "nl",
    "spain": "es",
}


def map_country_to_adzuna_code(country_name: str) -> str:
    """
    Map country name or code to Adzuna country code.

    Returns the Adzuna code if found, otherwise returns the input (for direct codes like 'us').
    If country not supported by Adzuna, returns None gracefully.
    """
    if not country_name:
        return None

    normalized = country_name.lower().strip()
    code = COUNTRY_CODE_MAP.get(normalized)

    # If not in map, assume it's already a valid code (2-letter code)
    if code:
        return code
    elif len(normalized) == 2:
        return normalized.lower()

    return None  # Country not recognized


class JobState(TypedDict):
    """Pipeline state tracking job discovery and batch processing."""
    user_id: str
    raw_jobs: list
    unprocessed_jobs: list  # All jobs to process
    processed_count: int
    applied_count: int
    review_count: int
    ignored_count: int
    error: str
    roles: list
    profile: dict
    summary: dict


def discovery_node(state: JobState) -> JobState:
    """Search Adzuna + Muse for ALL preferred countries, save jobs, get unprocessed for batch processing."""
    print(f"[DISCOVERY] Starting for user_id={state.get('user_id')}")
    try:
        user_id = state.get("user_id")
        if not user_id:
            raise Exception("user_id required")

        # Get profile
        profile_result = execute_query(
            "SELECT target_roles, preferred_countries, preferred_modality, salary_min FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )
        if not profile_result:
            raise Exception("User profile not found")
        p = profile_result[0]
        state["profile"] = p
        print(f"[DISCOVERY] Profile loaded: {len(p.get('target_roles', []))} roles")

        # Use roles from request if provided, otherwise use profile roles
        roles = state.get("roles") or p.get("target_roles")
        state["roles"] = roles

        # Search ALL preferred countries
        adzuna_jobs = []
        preferred_countries = p.get("preferred_countries", [])
        searched_countries = []
        skipped_countries = []

        if isinstance(preferred_countries, list) and len(preferred_countries) > 0:
            for country_name in preferred_countries:
                country_code = map_country_to_adzuna_code(country_name)

                if country_code:
                    try:
                        print(f"[DISCOVERY] Searching {country_name} ({country_code})")

                        # Search with English roles
                        jobs_en = search_adzuna(roles, country_code, p.get("salary_min"))

                        # Autonomously detect country language and translate roles
                        local_roles = _translate_roles_for_country(roles, country_code)

                        # If translations are different from English, also search with local language
                        jobs_local = []
                        if local_roles and local_roles != roles:
                            jobs_local = search_adzuna(local_roles, country_code, p.get("salary_min"))
                            print(f"[DISCOVERY] {country_name} ({country_code}): Adzuna English={len(jobs_en)}, Adzuna Local={len(jobs_local)}")
                        else:
                            print(f"[DISCOVERY] {country_name} ({country_code}): Adzuna English={len(jobs_en)} (no local translation needed)")

                        jobs = jobs_en + jobs_local

                        # For Mexico, also search OCC Mundial (Mexico's biggest job board)
                        jobs_occ = []
                        if country_code.lower() == "mx":
                            print(f"[DISCOVERY] Searching OCC Mundial for Mexico (translated roles: {local_roles})")
                            jobs_occ = search_occ_for_mexico(local_roles if local_roles else roles)
                            print(f"[DISCOVERY] OCC Mundial found {len(jobs_occ)} jobs")
                            jobs = jobs + jobs_occ
                            print(f"[DISCOVERY] {country_name} ({country_code}): Adzuna+OCC total={len(jobs)}")

                        # Tag each job with the country it was discovered from
                        for job in jobs:
                            job['search_country'] = country_code.lower()

                        adzuna_jobs.extend(jobs)
                        searched_countries.append(f"{country_name} ({country_code})")
                    except Exception as e:
                        print(f"[DISCOVERY] Error searching {country_name}: {str(e)}")
                        skipped_countries.append(country_name)
                else:
                    print(f"[DISCOVERY] Country '{country_name}' not supported by Adzuna, skipping")
                    skipped_countries.append(country_name)
        else:
            print(f"[DISCOVERY] No preferred countries configured, skipping Adzuna search")

        # Search Muse (global, no country filtering needed)
        themuse_jobs = search_themuse(roles, p.get("preferred_modality"))

        # Search Jobicy (free API, no auth, remote jobs only)
        jobicy_jobs = []
        try:
            jobicy_jobs = search_jobicy_jobs(roles, count=50)
        except Exception as e:
            print(f"[DISCOVERY] Jobicy search error: {str(e)}")
            # Continue with other sources if Jobicy fails

        # Search Remotive (free API, no auth, remote jobs only)
        remotive_jobs = []
        try:
            remotive_jobs = search_remotive_jobs(roles, limit=50)
        except Exception as e:
            print(f"[DISCOVERY] Remotive search error: {str(e)}")
            # Continue with other sources if Remotive fails

        # Combine all jobs and save with their search_country context
        all_jobs = adzuna_jobs + themuse_jobs + jobicy_jobs + remotive_jobs

        # save_jobs will use search_country from job objects (set during Adzuna search)
        # Global jobs (Muse, Jobicy, Remotive) won't have search_country set
        save_result = save_jobs(user_id, all_jobs)
        state["raw_jobs"] = all_jobs
        print(f"[DISCOVERY] Searched countries: {searched_countries}")
        if skipped_countries:
            print(f"[DISCOVERY] Skipped countries: {skipped_countries}")
        print(f"[DISCOVERY] Jobs: Adzuna={len(adzuna_jobs)}, Muse={len(themuse_jobs)}, Jobicy={len(jobicy_jobs)}, Remotive={len(remotive_jobs)}, Total={len(all_jobs)}")
        print(f"[DISCOVERY] Save result: {save_result}")

        # Get ALL unprocessed jobs for this user (discovered/parsed without fit_score for this user)
        # This scopes jobs to the user's own records. If the same job URL exists for another user,
        # they have their own separate job record and fit_score - no cross-user deduplication.
        unprocessed = execute_query(
            """
            SELECT j.id, j.title, j.company, j.description_raw, j.source
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
              AND j.status IN ('discovered', 'parsed')
              AND fs.id IS NULL
            ORDER BY j.created_at DESC
            """,
            (user_id, user_id)
        )
        state["unprocessed_jobs"] = unprocessed or []
        print(f"[DISCOVERY] Found {len(state['unprocessed_jobs'])} unprocessed jobs")

        return state
    except Exception as e:
        state["error"] = f"Discovery failed: {str(e)}"
        return state


def _translate_roles_for_country(roles: list, country_code: str) -> list:
    """
    Translate English job roles to the primary language of a country.

    Works for any country by auto-detecting the primary language and translating roles.
    No hardcoded translations - uses LLM for all language pairs.
    """
    if not roles or not country_code:
        return []

    try:
        roles_str = ", ".join(roles)
        prompt = f"""You are a job market expert. Translate these English job roles to the PRIMARY professional language used in job postings for {country_code.upper()}.

First, identify the primary job-search language for {country_code.upper()}, then translate the roles to that language.

English roles: {roles_str}

Return ONLY the translated roles as a comma-separated list. No explanations, no language names, no parentheses.

Translated roles:"""

        response = call_llm(prompt).strip()
        translated_roles = [r.strip() for r in response.split(',') if r.strip()]

        print(f"[TRANSLATION] Country: {country_code}, English roles: {roles}")
        print(f"[TRANSLATION] {country_code.upper()} roles: {translated_roles}")
        return translated_roles

    except Exception as e:
        print(f"[TRANSLATION] Error translating for {country_code}: {str(e)}, falling back to English")
        return roles


def _is_title_relevant(title: str, roles: list) -> bool:
    """
    Check if job title is relevant to target roles using LLM.

    Language-agnostic approach: works for English, Spanish, French, German, Japanese, etc.
    Uses LLM to understand context and semantic relevance, not just keyword matching.
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
    """Mark job as ignored without scoring. Updates status to 'scored' so it won't be reprocessed."""
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


def processing_node(state: JobState) -> JobState:
    """Batch process all unprocessed jobs: filter → parse → score → decide.

    Important: Jobs are user-scoped. The same job URL can exist for multiple users
    with different fit_scores, applications, and processing status. This allows
    sharing of job catalog across users while maintaining per-user evaluations.
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

    # Limit to first 10 jobs for efficiency (process in batches in production)
    unprocessed = unprocessed[:10]
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

            # FILTER: Check if title is relevant
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
                import json
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
            if score >= 85:
                decision = "apply"
            elif score >= 60:
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


def run_autonomous_cycle(user_id: str) -> dict:
    """
    Self-aware autonomous pipeline cycle.

    Analyzes current state and decides next action without hardcoded rules.
    LLM autonomously determines what to do based on pipeline metrics.

    Returns: {action, reasoning, priority, result}
    """
    try:
        print(f"[AUTONOMOUS] Starting autonomous cycle for user {user_id}", flush=True)

        # Gather current state
        state = _gather_pipeline_state(user_id)

        # LLM decides what to do
        decision = _llm_decide_action(user_id, state)

        # Execute the decision
        action = decision.get('action', 'wait')
        result = _execute_autonomous_action(user_id, action, state)

        return {
            'action': action,
            'reasoning': decision.get('reasoning', ''),
            'priority': decision.get('priority', 5),
            'result': result
        }

    except Exception as e:
        print(f"[AUTONOMOUS] ERROR: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return {'action': 'error', 'error': str(e), 'result': {}}


def _gather_pipeline_state(user_id: str) -> dict:
    """Gather all metrics about current pipeline state."""
    # Last discovery time
    last_discovery_log = execute_query(
        """SELECT created_at FROM agent_logs
           WHERE user_id = %s AND agent = 'job_discovery' AND status = 'success'
           ORDER BY created_at DESC LIMIT 1""",
        (user_id,)
    )
    last_discovery = last_discovery_log[0]['created_at'] if last_discovery_log else None
    hours_since_discovery = _hours_since(last_discovery) if last_discovery else 999

    # Unprocessed jobs
    unprocessed_result = execute_query(
        "SELECT COUNT(*) as count FROM jobs WHERE user_id = %s AND status = 'discovered'",
        (user_id,)
    )
    unprocessed_count = unprocessed_result[0]['count'] if unprocessed_result else 0

    # Total active jobs
    total_result = execute_query(
        "SELECT COUNT(*) as count FROM jobs WHERE user_id = %s AND expires_at IS NULL",
        (user_id,)
    )
    total_active = total_result[0]['count'] if total_result else 0

    # Recent scoring metrics (past 48 hours)
    scoring_result = execute_query(
        """SELECT
             COUNT(*) as total_scored,
             SUM(CASE WHEN score >= 85 THEN 1 ELSE 0 END) as applied_count,
             SUM(CASE WHEN score >= 60 AND score < 85 THEN 1 ELSE 0 END) as review_count,
             SUM(CASE WHEN score < 60 THEN 1 ELSE 0 END) as ignored_count,
             AVG(score) as avg_score
           FROM fit_scores
           WHERE user_id = %s AND created_at > NOW() - INTERVAL '48 hours'""",
        (user_id,)
    )

    if scoring_result and scoring_result[0]['total_scored']:
        scoring = scoring_result[0]
        total = scoring['total_scored']
        applied_pct = (scoring['applied_count'] / total * 100) if total > 0 else 0
        review_pct = (scoring['review_count'] / total * 100) if total > 0 else 0
        ignored_pct = (scoring['ignored_count'] / total * 100) if total > 0 else 0
    else:
        scoring = {
            'total_scored': 0,
            'applied_count': 0,
            'review_count': 0,
            'ignored_count': 0,
            'avg_score': 0
        }
        applied_pct = review_pct = ignored_pct = 0

    # Source quality
    from tools.db import get_source_quality_metrics
    source_quality = get_source_quality_metrics(user_id)

    # Job sources
    sources_result = execute_query(
        """SELECT source, COUNT(*) as count FROM jobs
           WHERE user_id = %s AND expires_at IS NULL
           GROUP BY source ORDER BY count DESC""",
        (user_id,)
    )
    sources = {row['source']: row['count'] for row in sources_result} if sources_result else {}

    # User profile
    profile = execute_query(
        "SELECT target_roles, preferred_countries FROM user_profiles WHERE user_id = %s",
        (user_id,)
    )
    user_profile = profile[0] if profile else {}

    return {
        'last_discovery_time': last_discovery,
        'hours_since_discovery': hours_since_discovery,
        'unprocessed_count': unprocessed_count,
        'total_active_jobs': total_active,
        'scoring_metrics': {
            'total_scored': scoring['total_scored'],
            'applied_count': scoring['applied_count'],
            'review_count': scoring['review_count'],
            'ignored_count': scoring['ignored_count'],
            'avg_score': scoring['avg_score'],
            'applied_pct': applied_pct,
            'review_pct': review_pct,
            'ignored_pct': ignored_pct,
        },
        'source_quality': source_quality,
        'sources': sources,
        'target_roles': user_profile.get('target_roles', []),
        'preferred_countries': user_profile.get('preferred_countries', []),
    }


def _llm_decide_action(user_id: str, state: dict) -> dict:
    """LLM autonomously decides what action to take based on pipeline state."""
    from tools.llm import call_llm
    import json

    scoring = state['scoring_metrics']
    sources = state['sources']
    source_quality = state['source_quality']

    source_list = '\n'.join([f"  - {src}: {cnt} jobs (quality: {source_quality.get(src, 0):.1f}%)"
                             for src, cnt in sources.items()]) if sources else "  (none)"

    prompt = f"""You are an autonomous job search pipeline manager.

Analyze this pipeline state and decide the NEXT ACTION.

CURRENT STATE:
- Target roles: {state['target_roles']}
- Preferred countries: {state['preferred_countries']}
- Hours since last discovery: {state['hours_since_discovery']:.1f}
- Unprocessed jobs waiting: {state['unprocessed_count']}
- Total active jobs in system: {state['total_active_jobs']}

SCORING RESULTS (Last 48 hours):
- Jobs scored: {scoring['total_scored']}
- Applied tier (85+): {scoring['applied_count']} ({scoring['applied_pct']:.1f}%)
- Review tier (60-84): {scoring['review_count']} ({scoring['review_pct']:.1f}%)
- Ignored tier (<60): {scoring['ignored_count']} ({scoring['ignored_pct']:.1f}%)
- Average score: {scoring['avg_score']:.1f}

ACTIVE SOURCES:
{source_list}

DECISION LOGIC:
- If unprocessed_count > 30 → PROCESS first (don't discover more until caught up)
- If unprocessed_count == 0 AND hours_since_discovery > 24 → DISCOVER
- If hours_since_discovery < 2 → PROCESS (give recent discovery time to complete)
- If all sources have quality < 10% → WAIT (sources not working, try again later)
- If applied_pct < 5% AND review_pct < 10% → TRY_NEW_SOURCES (low match rate)
- If everything current and processed → WAIT

Return ONLY valid JSON (no markdown):
{{
  "action": "run_discovery" | "run_processing" | "try_new_sources" | "wait",
  "reasoning": "brief explanation of why this action",
  "priority": integer 1-10
}}"""

    try:
        response = call_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        decision = json.loads(response)

        print(f"[AUTONOMOUS] LLM decided: {decision['action']} (priority: {decision.get('priority', 5)})", flush=True)
        return decision

    except Exception as e:
        print(f"[AUTONOMOUS] LLM decision failed: {str(e)}, defaulting to wait", flush=True)
        return {'action': 'wait', 'reasoning': f'Error: {str(e)}', 'priority': 1}


def _execute_autonomous_action(user_id: str, action: str, state: dict) -> dict:
    """Execute the action decided by LLM."""
    print(f"[AUTONOMOUS] Executing action: {action}", flush=True)

    if action == 'run_discovery':
        return _execute_discovery(user_id)
    elif action == 'run_processing':
        return _execute_processing(user_id, state)
    elif action == 'try_new_sources':
        print("[AUTONOMOUS] try_new_sources not yet implemented, waiting instead", flush=True)
        return {'action': 'wait', 'reason': 'new_sources_not_implemented'}
    else:
        return {'action': 'wait', 'reason': 'cycle complete, monitoring'}


def _execute_discovery(user_id: str) -> dict:
    """Execute discovery phase for this user across all preferred countries."""
    try:
        profile_result = execute_query(
            "SELECT target_roles, preferred_countries, preferred_modality, salary_min FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not profile_result:
            return {'error': 'User profile not found'}

        profile = profile_result[0]
        target_roles = profile.get('target_roles', ['AI Engineer'])

        state = JobState(
            user_id=user_id,
            raw_jobs=[],
            unprocessed_jobs=[],
            processed_count=0,
            applied_count=0,
            review_count=0,
            ignored_count=0,
            error="",
            roles=target_roles,
            profile=profile,
            summary={}
        )

        # Run ONLY discovery_node (not the full graph which includes processing)
        result = discovery_node(state)

        discovered = len(result.get('raw_jobs', []))
        print(f"[AUTONOMOUS] Discovery complete: {discovered} new jobs found", flush=True)

        return {
            'action': 'run_discovery',
            'jobs_discovered': discovered,
            'success': True
        }

    except Exception as e:
        print(f"[AUTONOMOUS] Discovery failed: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return {'action': 'run_discovery', 'error': str(e), 'success': False}


def _execute_processing(user_id: str, state: dict) -> dict:
    """Execute processing phase for this user."""
    try:
        profile_result = execute_query(
            "SELECT target_roles, preferred_countries FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not profile_result:
            return {'error': 'User profile not found'}

        profile = profile_result[0]

        # Fetch unprocessed jobs (status='discovered')
        unprocessed_result = execute_query(
            """SELECT id, title, description_raw FROM jobs
               WHERE user_id = %s AND status = 'discovered'
               LIMIT 100""",
            (user_id,)
        )
        unprocessed_jobs = [dict(row) for row in unprocessed_result] if unprocessed_result else []

        print(f"[AUTONOMOUS] Found {len(unprocessed_jobs)} unprocessed jobs for processing", flush=True)

        if not unprocessed_jobs:
            print(f"[AUTONOMOUS] No unprocessed jobs, nothing to process", flush=True)
            return {
                'action': 'run_processing',
                'jobs_processed': 0,
                'jobs_applied': 0,
                'jobs_review': 0,
                'success': True
            }

        process_state = JobState(
            user_id=user_id,
            raw_jobs=[],
            unprocessed_jobs=unprocessed_jobs,
            processed_count=0,
            applied_count=0,
            review_count=0,
            ignored_count=0,
            error="",
            roles=profile.get('target_roles', ['AI Engineer']),
            profile=profile,
            summary={}
        )

        result = processing_node(process_state)

        processed = result.get('processed_count', 0)
        applied = result.get('applied_count', 0)
        review = result.get('review_count', 0)

        print(f"[AUTONOMOUS] Processing complete: {processed} jobs processed, {applied} applied, {review} review", flush=True)

        return {
            'action': 'run_processing',
            'jobs_processed': processed,
            'jobs_applied': applied,
            'jobs_review': review,
            'success': True
        }

    except Exception as e:
        print(f"[AUTONOMOUS] Processing failed: {str(e)}", flush=True)
        return {'action': 'run_processing', 'error': str(e), 'success': False}


def _hours_since(dt) -> float:
    """Calculate hours since a datetime."""
    if not dt:
        return 999
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    return delta.total_seconds() / 3600


# Build the StateGraph
workflow = StateGraph(JobState)

# Add nodes
workflow.add_node("discovery", discovery_node)
workflow.add_node("processing", processing_node)

# Add edges: Discovery → Processing → END
workflow.add_edge("discovery", "processing")
workflow.add_edge("processing", END)

# Set entry point
workflow.set_entry_point("discovery")

# Compile graph
graph = workflow.compile()
