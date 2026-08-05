"""
LangGraph pipeline orchestrating the V1 job search workflow.

Refactored: Imports from focused agent modules instead of monolithic implementation.
Maintains backward compatibility with existing code that imports from pipeline.

Architecture:
- agents/state.py: JobState type and country mappings
- agents/discovery_agent.py: Discovery phase (search all job boards)
- agents/processing_agent.py: Processing phase (parse, score, decide)
- agents/autonomous_cycle.py: Self-aware cycle orchestration

Workflow: Discovery → Processing → Summary
"""

from langgraph.graph import StateGraph, END
from tools.agent_metrics import get_metrics_for_llm

# Import from refactored modules
from agents.state import JobState, map_country_to_adzuna_code, COUNTRY_CODE_MAP
from agents.discovery_agent import discovery_node, _translate_roles_for_country
from agents.processing_agent import processing_node, verification_node, _is_title_relevant, _mark_as_ignored
from agents.autonomous_cycle import (
    run_autonomous_cycle,
    _gather_pipeline_state,
    _llm_decide_action,
    _execute_autonomous_action,
    _execute_discovery,
    _execute_processing,
    _execute_cleanup,
    _hours_since
)

# Metrics node: Reads agent performance data before processing
def metrics_node(state: JobState) -> JobState:
    """
    Metrics node: Enriches state with agent performance metrics.

    LLM uses this data to autonomously decide:
    - Which sources are performing best
    - Which countries/regions to prioritize
    - Which roles have highest success rates
    - Which application methods work best

    No hardcoded rules - LLM analyzes patterns and decides strategy.
    """
    user_id = state.get("user_id")
    if not user_id:
        return state

    try:
        agent_metrics = get_metrics_for_llm(user_id)
        state["agent_performance_metrics"] = agent_metrics
        print(f"[METRICS] Metrics loaded for {user_id}", flush=True)
    except Exception as e:
        print(f"[METRICS] Error loading metrics: {str(e)}", flush=True)
        state["agent_performance_metrics"] = "Metrics unavailable"

    return state


# Re-export for backward compatibility
__all__ = [
    'JobState',
    'COUNTRY_CODE_MAP',
    'map_country_to_adzuna_code',
    'discovery_node',
    'verification_node',
    'processing_node',
    'metrics_node',
    '_translate_roles_for_country',
    '_is_title_relevant',
    '_mark_as_ignored',
    'run_autonomous_cycle',
    '_gather_pipeline_state',
    '_llm_decide_action',
    '_execute_autonomous_action',
    '_execute_discovery',
    '_execute_processing',
    '_execute_cleanup',
    '_hours_since',
    'graph',
    'workflow',
]


# Build the StateGraph
workflow = StateGraph(JobState)

# Add nodes
workflow.add_node("discovery", discovery_node)
workflow.add_node("verification", verification_node)
workflow.add_node("metrics", metrics_node)
workflow.add_node("processing", processing_node)

# Add edges: Discovery → Verification → Metrics → Processing → END
workflow.add_edge("discovery", "verification")
workflow.add_edge("verification", "metrics")
workflow.add_edge("metrics", "processing")
workflow.add_edge("processing", END)

# Set entry point
workflow.set_entry_point("discovery")

# Compile graph
graph = workflow.compile()
