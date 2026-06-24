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
    """Search Adzuna + Muse, save jobs, get all unprocessed jobs for batch processing."""
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

        # Search all job boards
        adzuna_jobs = []
        preferred_countries = p.get("preferred_countries", ["US"])
        if isinstance(preferred_countries, list) and len(preferred_countries) > 0:
            for country in preferred_countries:
                jobs = search_adzuna(roles, country.lower(), p.get("salary_min"))
                adzuna_jobs.extend(jobs)
        else:
            adzuna_jobs = search_adzuna(roles, "us", p.get("salary_min"))

        themuse_jobs = search_themuse(roles, p.get("preferred_modality"))
        all_jobs = adzuna_jobs + themuse_jobs

        save_result = save_jobs(user_id, all_jobs)
        state["raw_jobs"] = all_jobs
        print(f"[DISCOVERY] Jobs: Adzuna={len(adzuna_jobs)}, Muse={len(themuse_jobs)}, Total={len(all_jobs)}")
        print(f"[DISCOVERY] Save result: {save_result}")

        # Get ALL unprocessed jobs (discovered/parsed without fit_score)
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
    """Check if job title contains keywords from target roles."""
    if not title or not roles:
        return True

    title_lower = title.lower()
    # Extract keywords from roles (first word, e.g. "Robotics Engineer" → "robotics")
    keywords = set()
    for role in roles:
        words = role.lower().split()
        keywords.update(words)

    # Check if any keyword appears in title
    for keyword in keywords:
        if keyword in title_lower:
            return True

    return False


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
    """Batch process all unprocessed jobs: filter → parse → score → decide."""
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
    print(f"[PROCESSING] Processing {len(unprocessed)} jobs for user {user_id}")

    profile_full = execute_query("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
    if not profile_full:
        state["error"] = "User profile not found"
        return state

    for job_data in unprocessed:
        job_id = job_data.get("id")
        title = job_data.get("title")

        try:
            # FILTER: Check if title is relevant
            if not _is_title_relevant(title, roles):
                print(f"[FILTER] Skipping '{title}' - title not relevant to {roles}")
                _mark_as_ignored(job_id, user_id)
                state["ignored_count"] += 1
                continue

            # PARSE: Extract structured fields from description
            print(f"[PARSING] Job {job_id}: '{title}'")
            try:
                parsed = parse_job(job_id, user_id, job_data.get("description_raw", ""))
                update_job(job_id, user_id, parsed)
            except Exception as e:
                # If parsing fails (e.g., groq not available), skip this job
                print(f"[PARSE SKIPPED] Job {job_id}: {str(e)[:60]}")
                state["ignored_count"] += 1
                continue

            # SCORE: Calculate fit score
            job_full = execute_query("SELECT * FROM jobs WHERE id = %s AND user_id = %s", (job_id, user_id))
            if not job_full:
                continue

            print(f"[SCORING] Job {job_id}")
            fit_score = score_job(job_id, user_id, job_full[0], profile_full[0])
            save_fit_score(job_id, user_id, fit_score)

            # DECIDE: Route based on score
            decision = fit_score.get("decision", "ignore")
            score = fit_score.get("score", 0)

            if decision == "apply":
                status = "pending_application"
                trigger_agent("cv_tailoring", user_id, job_id)
                state["applied_count"] += 1
            elif decision == "review":
                status = "pending_approval"
                create_notification(user_id, "approval_required",
                                  f"Job matching {score}% needs approval", job_id,
                                  datetime.utcnow() + timedelta(hours=48))
                state["review_count"] += 1
            else:
                status = "ignored"
                state["ignored_count"] += 1

            # Create application record
            app_result = execute_query(
                "INSERT INTO applications (job_id, user_id, status) VALUES (%s, %s, %s) RETURNING id",
                (job_id, user_id, status)
            )
            if app_result:
                print(f"[DECISION] Job {job_id} → {status} (score: {score}%)")
            else:
                print(f"[ERROR] Failed to create application for job {job_id}")

            state["processed_count"] += 1

        except Exception as e:
            print(f"[JOB ERROR] Job {job_id}: {e}")
            state["ignored_count"] += 1

    # Create summary
    state["summary"] = {
        "total_processed": state["processed_count"],
        "applied": state["applied_count"],
        "review": state["review_count"],
        "ignored": state["ignored_count"],
    }

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
