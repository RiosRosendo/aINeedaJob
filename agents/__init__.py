"""
aINeedJob Agents Package

LangGraph-based orchestration of the V1 job search pipeline.

Pipeline flow:
  Discovery → Parsing → Matching → Decision → CV Tailoring / Notification / End

Each agent node calls corresponding deterministic tools and updates shared state.
"""

from agents.pipeline import graph, JobState

__all__ = ["graph", "JobState"]
