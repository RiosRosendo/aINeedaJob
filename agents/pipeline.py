"""
LangGraph pipeline orchestrating the V1 job search workflow.

Routes jobs through: Discovery → Parsing → Matching → Decision
Each agent node calls corresponding tools and updates state.
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
    """Pipeline state tracking job through discovery, parsing, matching, decision."""
    user_id: str
    job_id: str
    application_id: str
    raw_jobs: list
    parsed_job: dict
    fit_score: dict
    decision: str
    error: str


def discovery_node(state: JobState) -> JobState:
    """Search Adzuna + Muse, save jobs. Output: raw_jobs list and first job_id."""
    print(f"[DISCOVERY] State at start: user_id={state.get('user_id')}, job_id={state.get('job_id')}")
    try:
        user_id = state.get("user_id")
        if not user_id:
            raise Exception("user_id required")
        profile_result = execute_query(
            "SELECT target_roles, preferred_countries, preferred_modality, salary_min FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )
        if not profile_result:
            raise Exception("User profile not found")
        p = profile_result[0]
        print(f"[DISCOVERY] Profile: {p}")
        adzuna_jobs = search_adzuna(p.get("target_roles"), p.get("preferred_countries"), p.get("salary_min"))
        print(f"[DISCOVERY] Adzuna jobs found: {len(adzuna_jobs)}")
        themuse_jobs = search_themuse(p.get("target_roles"), p.get("preferred_modality"))
        print(f"[DISCOVERY] Muse jobs found: {len(themuse_jobs)}")
        all_jobs = adzuna_jobs + themuse_jobs
        save_result = save_jobs(user_id, all_jobs)
        print(f"[DISCOVERY] Save result: {save_result}")
        state["raw_jobs"] = all_jobs

        # Extract first saved job_id from database for processing through pipeline
        saved = execute_query(
            "SELECT id FROM jobs WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        print(f"[DISCOVERY] DB query result: {saved}")
        if saved:
            state["job_id"] = str(saved[0]["id"])
            print(f"[DISCOVERY] job_id set to: {state['job_id']}")

        print(f"[DISCOVERY] State at end: user_id={state.get('user_id')}, job_id={state.get('job_id')}")
        return state
    except Exception as e:
        state["error"] = f"Discovery failed: {str(e)}"
        return state


def parsing_node(state: JobState) -> JobState:
    """Extract structured fields from raw description via LLM. Output: parsed_job dict."""
    print(f"[PARSING] State at start: user_id={state.get('user_id')}, job_id={state.get('job_id')}")
    try:
        job_id, user_id = state.get("job_id"), state.get("user_id")
        if not job_id or not user_id:
            raise Exception("job_id and user_id required")
        job_result = execute_query("SELECT description_raw FROM jobs WHERE id = %s AND user_id = %s", (job_id, user_id))
        if not job_result:
            raise Exception("Job not found")
        parsed = parse_job(job_id, user_id, job_result[0].get("description_raw", ""))
        update_job(job_id, user_id, parsed)
        state["parsed_job"] = parsed
        print(f"[PARSING] State at end: user_id={state.get('user_id')}, job_id={state.get('job_id')}")
        return state
    except Exception as e:
        state["error"] = f"Parsing failed: {str(e)}"
        print(f"[PARSING] State at error: user_id={state.get('user_id')}, job_id={state.get('job_id')}, error={e}")
        return state


def matching_node(state: JobState) -> JobState:
    """Run hard filters, calculate skill overlap, score via LLM. Output: fit_score dict."""
    print(f"[MATCHING] State at start: user_id={state.get('user_id')}, job_id={state.get('job_id')}")
    try:
        job_id, user_id = state.get("job_id"), state.get("user_id")
        if not job_id or not user_id:
            raise Exception("job_id and user_id required")
        job_result = execute_query("SELECT * FROM jobs WHERE id = %s AND user_id = %s", (job_id, user_id))
        if not job_result:
            raise Exception("Job not found")
        profile_result = execute_query("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
        if not profile_result:
            raise Exception("User profile not found")
        fit_score = score_job(job_id, user_id, job_result[0], profile_result[0])
        save_fit_score(job_id, user_id, fit_score)
        state["fit_score"] = fit_score
        state["decision"] = fit_score.get("decision")
        print(f"[MATCHING] State at end: user_id={state.get('user_id')}, job_id={state.get('job_id')}, decision={state.get('decision')}")
        return state
    except Exception as e:
        state["error"] = f"Matching failed: {str(e)}"
        print(f"[MATCHING] State at error: user_id={state.get('user_id')}, job_id={state.get('job_id')}, error={e}")
        return state


def decision_node(state: JobState) -> JobState:
    """Route based on fit score: apply → cv_tailoring, review → notify, ignore → end."""
    print(f"[DECISION_ROUTER] State at start: user_id={state.get('user_id')}, job_id={state.get('job_id')}")
    try:
        job_id, user_id = state.get("job_id"), state.get("user_id")
        if not job_id or not user_id:
            raise Exception("job_id and user_id required")
        fit_score = state.get("fit_score", {})
        decision, score = fit_score.get("decision", "ignore"), fit_score.get("score", 0)
        if decision == "apply":
            status = "pending_application"
            trigger_agent("cv_tailoring", user_id, job_id)
        elif decision == "review":
            status = "pending_approval"
            create_notification(user_id, "approval_required",
                              f"Job matching {score}% needs approval", job_id,
                              datetime.utcnow() + timedelta(hours=48))
        else:
            status = "ignored"

        # Create application record first (INSERT ... RETURNING id)
        app_result = execute_query(
            "INSERT INTO applications (job_id, user_id, status) VALUES (%s, %s, %s) RETURNING id",
            (job_id, user_id, status)
        )
        if app_result:
            application_id = str(app_result[0]["id"])
            print(f"[DECISION_ROUTER] Created application: {application_id}")
            state["application_id"] = application_id
        else:
            raise Exception("Failed to create application record")
        print(f"[DECISION_ROUTER] State at end: user_id={state.get('user_id')}, job_id={state.get('job_id')}, status={status}")
        return state
    except Exception as e:
        state["error"] = f"Decision failed: {str(e)}"
        print(f"[DECISION_ROUTER] State at error: user_id={state.get('user_id')}, job_id={state.get('job_id')}, error={e}")
        return state


def cv_tailoring_node(state: JobState) -> JobState:
    """Placeholder for V2: CV tailoring agent (auto-apply path)."""
    print(f"[V2 PLACEHOLDER] CV Tailoring Agent - Job ID: {state.get('job_id')}")
    return state


def notify_user_node(state: JobState) -> JobState:
    """Placeholder for V2: Notify user for approval (review path)."""
    print(f"[V2 PLACEHOLDER] Notify User Agent - Job ID: {state.get('job_id')}")
    return state


def route_by_score(state: JobState) -> Literal["cv_tailoring", "notify_user", "end"]:
    """
    Route next step based on fit score.

    - score >= 85 → "cv_tailoring" (auto-apply path)
    - score 60-84 → "notify_user" (review path)
    - score < 60 → "end" (ignore path)
    """
    if state.get("error"):
        return "end"

    fit_score = state.get("fit_score", {})
    score = fit_score.get("score", 0)

    if score >= 85:
        return "cv_tailoring"
    elif score >= 60:
        return "notify_user"
    else:
        return "end"


# Build the StateGraph
workflow = StateGraph(JobState)

# Add nodes
workflow.add_node("discovery", discovery_node)
workflow.add_node("parsing", parsing_node)
workflow.add_node("matching", matching_node)
workflow.add_node("decision_router", decision_node)
workflow.add_node("cv_tailoring", cv_tailoring_node)
workflow.add_node("notify_user", notify_user_node)

# Add edges (linear progression through pipeline)
workflow.add_edge("discovery", "parsing")
workflow.add_edge("parsing", "matching")
workflow.add_edge("matching", "decision_router")

# Conditional edge after decision_router based on score
workflow.add_conditional_edges(
    "decision_router",
    route_by_score,
    {
        "cv_tailoring": "cv_tailoring",
        "notify_user": "notify_user",
        "end": END,
    }
)

# Placeholder nodes terminate to END (V2 will replace these with real logic)
workflow.add_edge("cv_tailoring", END)
workflow.add_edge("notify_user", END)

# Set entry point
workflow.set_entry_point("discovery")

# Compile graph
graph = workflow.compile()
