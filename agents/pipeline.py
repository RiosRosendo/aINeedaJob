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
    """Search Adzuna + Muse, save jobs. Output: raw_jobs list."""
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
        adzuna_jobs = search_adzuna(p.get("target_roles"), p.get("preferred_countries"), p.get("salary_min"))
        themuse_jobs = search_themuse(p.get("target_roles"), p.get("preferred_modality"))
        all_jobs = adzuna_jobs + themuse_jobs
        save_jobs(user_id, all_jobs)
        state["raw_jobs"] = all_jobs
        return state
    except Exception as e:
        state["error"] = f"Discovery failed: {str(e)}"
        return state


def parsing_node(state: JobState) -> JobState:
    """Extract structured fields from raw description via LLM. Output: parsed_job dict."""
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
        return state
    except Exception as e:
        state["error"] = f"Parsing failed: {str(e)}"
        return state


def matching_node(state: JobState) -> JobState:
    """Run hard filters, calculate skill overlap, score via LLM. Output: fit_score dict."""
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
        return state
    except Exception as e:
        state["error"] = f"Matching failed: {str(e)}"
        return state


def decision_node(state: JobState) -> JobState:
    """Route based on fit score: apply → cv_tailoring, review → notify, ignore → end."""
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
        update_application(state.get("application_id"), user_id, status)
        return state
    except Exception as e:
        state["error"] = f"Decision failed: {str(e)}"
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
workflow.add_node("decision", decision_node)

# Add edges (linear progression through pipeline)
workflow.add_edge("discovery", "parsing")
workflow.add_edge("parsing", "matching")
workflow.add_edge("matching", "decision")

# Conditional edge after decision based on score
workflow.add_conditional_edges(
    "decision",
    route_by_score,
    {
        "cv_tailoring": "cv_tailoring",  # Placeholder for future node
        "notify_user": "notify_user",    # Placeholder for future node
        "end": END,
    }
)

# Set entry point
workflow.set_entry_point("discovery")

# Compile graph
graph = workflow.compile()
