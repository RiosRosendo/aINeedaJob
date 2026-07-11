"""
LangGraph pipeline orchestrating the V1 job search workflow.

Batch processing: Discovery → Process ALL unprocessed jobs → Summary
Processes all unprocessed jobs with title filtering to avoid irrelevant results.
"""

from typing import TypedDict, Literal
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from tools.db import execute_query
from tools.search_adzuna import search_adzuna
from tools.search_themuse import search_themuse
from tools.save_jobs import save_jobs
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
                        jobs = search_adzuna(roles, country_code, p.get("salary_min"))
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
        all_jobs = adzuna_jobs + themuse_jobs

        save_result = save_jobs(user_id, all_jobs)
        state["raw_jobs"] = all_jobs
        print(f"[DISCOVERY] Searched countries: {searched_countries}")
        if skipped_countries:
            print(f"[DISCOVERY] Skipped countries: {skipped_countries}")
        print(f"[DISCOVERY] Jobs: Adzuna={len(adzuna_jobs)}, Muse={len(themuse_jobs)}, Total={len(all_jobs)}")
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
        prompt = f"""Is this job title relevant to these target roles?

Job Title: {title}
Target Roles: {roles_str}

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
    """Mark job as ignored without scoring."""
    try:
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
                # If parsing fails (e.g., groq not available), skip this job
                print(f"[PROCESS DEBUG] Job {job_id}: SKIP - parse failed: {str(e)[:60]}")
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

            # DECIDE: Route based on score
            decision = fit_score.get("decision", "ignore")
            score = fit_score.get("score", 0)

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
                execute_query(
                    "UPDATE applications SET status = %s WHERE id = %s",
                    (status, application_id)
                )
                print(f"[DECISION] Job {job_id} → {status} (score: {score}%)")

            elif decision == "review":
                status = "pending_approval"
                # Update application status for review tier
                execute_query(
                    "UPDATE applications SET status = %s WHERE id = %s",
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
                execute_query(
                    "UPDATE applications SET status = %s WHERE id = %s",
                    (status, application_id)
                )
                state["ignored_count"] += 1
                print(f"[DECISION] Job {job_id} → {status} (score: {score}%)")

        except Exception as e:
            print(f"[PROCESS DEBUG] Job {job_id}: SKIP - unexpected error: {str(e)[:80]}")
            state["ignored_count"] += 1

    # Create summary
    state["summary"] = {
        "total_processed": state["processed_count"],
        "applied": state["applied_count"],
        "review": state["review_count"],
    }

    print(f"[PROCESS DEBUG] Breakdown: processed={state['processed_count']}, applied={state['applied_count']}, review={state['review_count']}, ignored={state['ignored_count']}")
    print(f"[PROCESSING COMPLETE] Summary: {state['summary']}")
    return state


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
