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

# Re-export for backward compatibility
__all__ = [
    'JobState',
    'COUNTRY_CODE_MAP',
    'map_country_to_adzuna_code',
    'discovery_node',
    'verification_node',
    'processing_node',
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
workflow.add_node("processing", processing_node)

# Add edges: Discovery → Verification → Processing → END
workflow.add_edge("discovery", "verification")
workflow.add_edge("verification", "processing")
workflow.add_edge("processing", END)

# Set entry point
workflow.set_entry_point("discovery")

# Compile graph
graph = workflow.compile()
