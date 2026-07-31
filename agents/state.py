"""
Pipeline state dataclass and type definitions.

Shared state object passed between all pipeline nodes in the WAT (Workflows, Agents, Tools) framework.
Every agent (Discovery, Processing, Autonomous Cycle) reads and writes to JobState.
"""

from typing import TypedDict

# ============================================================================
# SCORE THRESHOLDS - Centralized configuration for job matching decisions
# ============================================================================
# These thresholds define the 3-tier decision system:
# - auto_apply (≥85): High confidence match, auto-submit application
# - review (60-84): Medium confidence, user reviews before applying
# - ignore (<60): Low relevance, skip this job
SCORE_THRESHOLDS = {
    "auto_apply": 85,      # Score >= 85: automatically apply
    "review": 60,          # Score 60-84: notify user for approval
    "ignore": 0            # Score < 60: ignore (not used in comparisons)
}


class JobState(TypedDict):
    """
    Pipeline state tracking job discovery and batch processing.

    Passed between discovery_node() → processing_node() in LangGraph workflow.
    Also used by autonomous_cycle to track execution results.

    Attributes:
        user_id (str): User identifier for multi-user scoping (primary key for all DB ops)
        raw_jobs (list): Jobs discovered in current discovery_node run
        unprocessed_jobs (list): Jobs waiting to be parsed/scored (status='discovered' or 'parsed' without fit_score)
        processed_count (int): Number of jobs successfully parsed and scored in processing_node
        applied_count (int): Number of jobs routed to auto-apply (score >= 85)
        review_count (int): Number of jobs routed to user approval (score 60-84)
        ignored_count (int): Number of jobs ignored (score < 60 or filtered)
        error (str): Error message if node failed
        roles (list): User's target job roles (e.g., ["AI Engineer", "Robotics Engineer"])
        profile (dict): User profile from user_profiles table (target_roles, preferred_countries, salary_min, etc.)
        summary (dict): Final summary stats after processing (total_processed, applied, review, ignored)
    """
    user_id: str
    raw_jobs: list
    unprocessed_jobs: list
    processed_count: int
    applied_count: int
    review_count: int
    ignored_count: int
    error: str
    roles: list
    profile: dict
    summary: dict


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

    Agent Role: Helper for Discovery Agent

    Converts user-friendly country names ("united states", "mexico") to Adzuna API
    country codes ("us", "mx"). Handles fuzzy matching and direct codes.

    Args:
        country_name (str): Country name or code (e.g., "United States", "us", "mexico")

    Returns:
        str: Adzuna country code (e.g., "us", "mx") or None if not recognized
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

    return None
