"""
Autonomous Cycle orchestrator - self-aware pipeline execution decision-making.

Implements autonomous agent that periodically:
1. Gathers metrics about current pipeline state (discovery, processing, duplication, scores)
2. Asks LLM: "What should we do next?" based on those metrics
3. Executes the LLM's decision (discover, process, cleanup, wait)
4. Reports results back

Uses LangGraph as the orchestration engine for multi-step pipelines:
- LangGraph provides: state management, error handling, retry logic, observability
- Enables streaming, debugging, and monitoring of agent execution
- Separates orchestration logic (LangGraph) from business logic (agents)

This enables 24/7 autonomous operation without hardcoded rules or schedulers.
"""

from agents.state import JobState, SCORE_THRESHOLDS
from agents.discovery_agent import discovery_node
from agents.processing_agent import processing_node
from tools.db import execute_query, execute_update
from tools.llm import call_llm
from tools.agent_metrics import get_metrics_for_llm
from langgraph.graph import StateGraph, END
from datetime import datetime, timezone
import json


def run_autonomous_cycle(user_id: str) -> dict:
    """
    Execute one cycle of autonomous pipeline orchestration.

    Agent Role: AUTONOMOUS CYCLE ORCHESTRATOR in WAT framework

    Self-aware execution loop:
    1. Load user profile (check if setup is complete)
    2. Gather pipeline state (discovery time, unprocessed count, scoring metrics, duplication rate)
    3. Ask LLM: "Based on this state, what action should we take?" (discover/process/cleanup/wait)
    4. Execute LLM's decision with appropriate agent
    5. Return result and reasoning

    Runs on-demand via API endpoints (cron scheduling handled by APScheduler).
    Replaces hardcoded rules with LLM reasoning about pipeline metrics.

    Tools Called:
    - _gather_pipeline_state(): Collect all relevant pipeline metrics
    - _llm_decide_action(): LLM autonomously decides next action
    - _execute_autonomous_action(): Execute discovery/processing/cleanup based on decision

    Args:
        user_id (str): User ID to run cycle for

    Returns:
        dict: {
            action: str,           # what was decided (discover/process/cleanup/wait/skip)
            reasoning: str,        # why LLM chose this action
            priority: int,         # execution priority (1-10)
            result: dict           # result from executing the action
        }
    """
    try:
        print(f"[AUTONOMOUS] Starting autonomous cycle for user {user_id}", flush=True)

        # Check if user profile is complete
        profile_result = execute_query(
            "SELECT target_roles, tech_stack FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not profile_result:
            print(f"[AUTONOMOUS] User profile not found for {user_id}", flush=True)
            return {'action': 'skip', 'reason': 'Profile not found', 'result': {}}

        profile = profile_result[0]
        target_roles = profile.get('target_roles', [])
        tech_stack = profile.get('tech_stack', [])

        # Skip if profile is incomplete
        if not target_roles or not tech_stack:
            print(f"[AUTONOMOUS] Skipping user {user_id} - profile incomplete (roles={len(target_roles) if target_roles else 0}, skills={len(tech_stack) if tech_stack else 0})", flush=True)
            return {
                'action': 'skip',
                'reason': 'Profile incomplete - no target roles or tech stack',
                'result': {}
            }

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
    """
    Gather all metrics about current pipeline state.

    Agent Role: Helper for AUTONOMOUS CYCLE ORCHESTRATOR

    Collects comprehensive metrics used by LLM decision-making:
    - Discovery timing (when was last search, how many unprocessed jobs)
    - Job quality (scoring distribution, average fit score)
    - Source quality (which sources have high match rates)
    - Country distribution (which countries have jobs, priority country underrepresentation)
    - Duplication rate (how many duplicate jobs exist from different sources)

    Tools Called:
    - execute_query(): Fetch metrics from agent_logs, jobs, fit_scores tables

    Args:
        user_id (str): User ID to gather state for

    Returns:
        dict: Comprehensive pipeline state used by _llm_decide_action()
    """
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

    # User profile with priority_country
    profile = execute_query(
        "SELECT target_roles, preferred_countries, priority_country FROM user_profiles WHERE user_id = %s",
        (user_id,)
    )
    user_profile = profile[0] if profile else {}

    # Jobs by search_country to detect if priority country is underrepresented
    country_jobs = execute_query(
        """SELECT search_country, COUNT(*) as count FROM jobs
           WHERE user_id = %s AND expires_at IS NULL AND search_country IS NOT NULL
           GROUP BY search_country ORDER BY count DESC""",
        (user_id,)
    )
    jobs_by_country = {row['search_country']: row['count'] for row in country_jobs} if country_jobs else {}

    # Calculate duplication rate: total jobs / unique (title, company) pairs
    duplication_result = execute_query(
        """SELECT
             COUNT(*) as total_jobs,
             COUNT(DISTINCT LOWER(title) || '|' || LOWER(COALESCE(company, ''))) as unique_jobs
           FROM jobs
           WHERE user_id = %s AND expires_at IS NULL""",
        (user_id,)
    )
    duplication_data = duplication_result[0] if duplication_result else {'total_jobs': 0, 'unique_jobs': 0}
    total_jobs = duplication_data.get('total_jobs', 0)
    unique_jobs = duplication_data.get('unique_jobs', 0)
    duplication_rate = (total_jobs / unique_jobs) if unique_jobs > 0 else 1.0

    # Get agent performance metrics (LLM uses this to autonomously decide strategy)
    agent_metrics = get_metrics_for_llm(user_id)

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
        'priority_country': user_profile.get('priority_country'),
        'jobs_by_country': jobs_by_country,
        'duplication_rate': duplication_rate,
        'total_jobs': total_jobs,
        'unique_jobs': unique_jobs,
        'agent_performance_metrics': agent_metrics,
    }


def _llm_decide_action(user_id: str, state: dict) -> dict:
    """
    LLM autonomously decides what action to take based on pipeline state.

    Agent Role: Helper for AUTONOMOUS CYCLE ORCHESTRATOR

    Uses Groq LLM to reason about pipeline metrics and decide next action.
    NO hardcoded rules - LLM evaluates duplication rate, discovery time, job backlog, etc.

    Tools Called:
    - call_llm(): Groq LLM for action decision

    Args:
        user_id (str): User ID (for logging)
        state (dict): Pipeline state from _gather_pipeline_state()

    Returns:
        dict: {
            action: str,       # "run_discovery" | "run_processing" | "run_cleanup" | "try_new_sources" | "wait"
            reasoning: str,    # why LLM chose this action
            priority: int      # execution priority (1-10)
        }
    """
    scoring = state['scoring_metrics']
    sources = state['sources']
    source_quality = state['source_quality']
    jobs_by_country = state.get('jobs_by_country', {})
    priority_country = state.get('priority_country')
    duplication_rate = state.get('duplication_rate', 1.0)
    total_jobs = state.get('total_jobs', 0)
    unique_jobs = state.get('unique_jobs', 0)

    source_list = '\n'.join([f"  - {src}: {cnt} jobs (quality: {source_quality.get(src, 0):.1f}%)"
                             for src, cnt in sources.items()]) if sources else "  (none)"

    # Build country distribution summary
    country_dist = '\n'.join([f"  - {country.upper()}: {cnt} jobs" for country, cnt in sorted(jobs_by_country.items(), key=lambda x: -x[1])]) if jobs_by_country else "  (no country-specific jobs tracked)"

    priority_info = f"\n- PRIORITY COUNTRY: {priority_country.upper()}" if priority_country else ""

    prompt = f"""You are an autonomous job search pipeline manager.

Analyze this pipeline state and decide the NEXT ACTION.

CURRENT STATE:
- Target roles: {state['target_roles']}
- Preferred countries: {state['preferred_countries']}{priority_info}
- Hours since last discovery: {state['hours_since_discovery']:.1f}
- Unprocessed jobs waiting: {state['unprocessed_count']}
- Total active jobs in system: {state['total_active_jobs']}

JOBS BY COUNTRY (Active Jobs):
{country_dist}

DUPLICATE DETECTION:
- Total jobs: {total_jobs}
- Unique by (title, company): {unique_jobs}
- Duplication rate: {duplication_rate:.2f}x (1.0 = no duplicates, 2.0 = every unique job appears twice)

SCORING RESULTS (Last 48 hours):
- Jobs scored: {scoring['total_scored']}
- Applied tier (85+): {scoring['applied_count']} ({scoring['applied_pct']:.1f}%)
- Review tier (60-84): {scoring['review_count']} ({scoring['review_pct']:.1f}%)
- Ignored tier (<60): {scoring['ignored_count']} ({scoring['ignored_pct']:.1f}%)
- Average score: {scoring['avg_score']:.1f}

ACTIVE SOURCES:
{source_list}

Analyze the pipeline state and decide the best action. Consider:
- Number of unprocessed jobs vs recently discovered jobs
- Time since last discovery
- Job quality metrics (relevance rates, scoring rates)
- Priority country job distribution
- Duplication rate

IMPORTANT: Always prefer action over waiting.
- If unprocessed_count > 100 → run_processing is almost always correct
- If hours_since_discovery > 24 → run_discovery is needed
- Only choose 'wait' if everything is caught up AND discovery was recent (< 6 hours)
- The system should be constantly working, not waiting
- When in doubt, run_processing to clear the backlog

Make an autonomous decision based on the data provided.

Return ONLY valid JSON (no markdown). Action MUST be exactly one of these strings:
{{
  "action": "run_discovery" | "run_processing" | "run_cleanup" | "try_new_sources" | "wait",
  "reasoning": "brief explanation of why this action",
  "priority": integer 1-10
}}"""

    try:
        response = call_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        decision = json.loads(response)

        # Normalize action name in case LLM returns shorthand
        action = decision.get('action', 'wait')
        action_map = {'discovery': 'run_discovery', 'processing': 'run_processing', 'cleanup': 'run_cleanup'}
        decision['action'] = action_map.get(action, action)

        # Override: if LLM chose 'wait' but backlog is huge (>500), force run_processing
        if decision['action'] == 'wait' and state.get('unprocessed_count', 0) > 500:
            print(f"[AUTONOMOUS] Override: huge backlog ({state['unprocessed_count']} unprocessed), forcing run_processing despite LLM 'wait'", flush=True)
            decision['action'] = 'run_processing'
            decision['reasoning'] = f"Override: massive backlog ({state['unprocessed_count']} jobs) requires immediate processing"

        print(f"[AUTONOMOUS] LLM decided: {decision['action']} (priority: {decision.get('priority', 5)})", flush=True)
        return decision

    except Exception as e:
        print(f"[AUTONOMOUS] LLM decision failed: {str(e)}, defaulting to wait", flush=True)
        return {'action': 'wait', 'reasoning': f'Error: {str(e)}', 'priority': 1}


def _execute_autonomous_action(user_id: str, action: str, state: dict) -> dict:
    """
    Execute the action decided by LLM.

    Agent Role: Helper for AUTONOMOUS CYCLE ORCHESTRATOR

    Routes execution to appropriate agent based on LLM decision:
    - run_discovery: Execute discovery_node() to find new jobs
    - run_processing: Execute processing_node() to parse/score unprocessed jobs
    - run_cleanup: Execute _execute_cleanup() to remove duplicates
    - try_new_sources: Not yet implemented (would add more job boards)
    - wait: Do nothing, cycle completes

    Tools Called:
    - _execute_discovery() / _execute_processing() / _execute_cleanup()

    Args:
        user_id (str): User ID to execute action for
        action (str): Action decided by LLM
        state (dict): Pipeline state from _gather_pipeline_state()

    Returns:
        dict: Result from executed action (jobs_discovered, jobs_processed, etc.)
    """
    print(f"[AUTONOMOUS] Executing action: {action}", flush=True)

    if action == 'run_discovery':
        return _execute_discovery(user_id)
    elif action == 'run_processing':
        return _execute_processing(user_id, state)
    elif action == 'run_cleanup':
        return _execute_cleanup(user_id)
    elif action == 'try_new_sources':
        return _execute_try_new_sources(user_id, state)
    else:
        return {'action': 'wait', 'reason': 'cycle complete, monitoring'}


def _execute_discovery(user_id: str) -> dict:
    """
    Execute discovery and processing phases using LangGraph orchestration.

    Creates JobState and invokes the full LangGraph pipeline:
    discovery_node → processing_node → END

    LangGraph provides:
    - State management: JobState passed between nodes
    - Error handling: Exceptions in nodes are caught and logged
    - Observability: Pipeline execution can be streamed/debugged
    - Retry logic: Can be added via LangGraph config (future)

    Processes all discovered jobs through the pipeline in one cycle.
    """
    try:
        # Import here to avoid circular imports
        from agents.pipeline import graph

        profile_result = execute_query(
            "SELECT target_roles, preferred_countries, preferred_modality, salary_min FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not profile_result:
            return {'error': 'User profile not found'}

        profile = profile_result[0]
        target_roles = profile.get('target_roles', [])

        # Skip users without target roles configured
        if not target_roles:
            print(f"[AUTONOMOUS] Skipping user {user_id}: no target_roles configured", flush=True)
            return {'error': 'User has no target_roles configured', 'action': 'wait'}

        initial_state = JobState(
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

        # Invoke the full LangGraph pipeline: discovery → processing → END
        # This runs discovery_node to find jobs, then processing_node to score them
        print(f"[AUTONOMOUS] Invoking LangGraph pipeline for user {user_id}", flush=True)
        result = graph.invoke(initial_state)

        discovered = len(result.get('raw_jobs', []))
        processed = result.get('processed_count', 0)
        applied = result.get('applied_count', 0)
        review = result.get('review_count', 0)

        print(f"[AUTONOMOUS] LangGraph pipeline complete: {discovered} discovered, {processed} processed, {applied} applied, {review} review", flush=True)

        return {
            'action': 'run_discovery',
            'jobs_discovered': discovered,
            'jobs_processed': processed,
            'jobs_applied': applied,
            'jobs_review': review,
            'success': True
        }

    except Exception as e:
        print(f"[AUTONOMOUS] LangGraph pipeline failed: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return {'action': 'run_discovery', 'error': str(e), 'success': False}


def _execute_processing(user_id: str, state: dict) -> dict:
    """
    Execute processing phase for this user using LangGraph orchestration.

    Creates a processing-only LangGraph pipeline (single node, no discovery):
    processing_node → END

    LangGraph benefits for this phase:
    - Isolates processing from discovery (can be called independently)
    - Manages state through parsing → scoring → decision routing
    - Provides structured error handling for each job in the batch
    - Enables streaming results as jobs are processed

    Uses 30-job batch limit to balance throughput vs rate limiting.
    """
    try:
        profile_result = execute_query(
            "SELECT target_roles, preferred_countries FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not profile_result:
            return {'error': 'User profile not found'}

        profile = profile_result[0]
        target_roles = profile.get('target_roles', [])

        # Skip users without target roles configured
        if not target_roles:
            print(f"[AUTONOMOUS] Skipping processing for user {user_id}: no target_roles configured", flush=True)
            return {'error': 'User has no target_roles configured', 'action': 'wait'}

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

        # Create a processing-only LangGraph pipeline (single node)
        process_workflow = StateGraph(JobState)
        process_workflow.add_node("processing", processing_node)
        process_workflow.add_edge("processing", END)
        process_workflow.set_entry_point("processing")
        process_graph = process_workflow.compile()

        initial_state = JobState(
            user_id=user_id,
            raw_jobs=[],
            unprocessed_jobs=unprocessed_jobs,
            processed_count=0,
            applied_count=0,
            review_count=0,
            ignored_count=0,
            error="",
            roles=target_roles,
            profile=profile,
            summary={}
        )

        # Invoke the processing-only LangGraph pipeline
        print(f"[AUTONOMOUS] Invoking LangGraph processing pipeline for user {user_id}", flush=True)
        result = process_graph.invoke(initial_state)

        processed = result.get('processed_count', 0)
        applied = result.get('applied_count', 0)
        review = result.get('review_count', 0)

        print(f"[AUTONOMOUS] LangGraph processing pipeline complete: {processed} processed, {applied} applied, {review} review", flush=True)

        return {
            'action': 'run_processing',
            'jobs_processed': processed,
            'jobs_applied': applied,
            'jobs_review': review,
            'success': True
        }

    except Exception as e:
        print(f"[AUTONOMOUS] LangGraph processing pipeline failed: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return {'action': 'run_processing', 'error': str(e), 'success': False}


def _execute_cleanup(user_id: str) -> dict:
    """
    Execute cleanup phase: remove duplicate jobs, keeping only the most recent per title+company.

    Deletes jobs where duplicate (title, company) pairs exist, keeping the newest version.
    """
    try:
        # Count duplicates before cleanup
        count_before = execute_query(
            "SELECT COUNT(*) as count FROM jobs WHERE user_id = %s AND expires_at IS NULL",
            (user_id,)
        )
        total_before = count_before[0]['count'] if count_before else 0

        # Delete duplicates, keeping most recent per (title, company)
        cleanup_query = """
        DELETE FROM jobs
        WHERE user_id = %s
        AND id NOT IN (
          SELECT DISTINCT ON (LOWER(title), LOWER(COALESCE(company, ''))) id
          FROM jobs
          WHERE user_id = %s AND expires_at IS NULL
          ORDER BY LOWER(title), LOWER(COALESCE(company, '')), created_at DESC
        )
        """
        execute_update(cleanup_query, (user_id, user_id))

        # Count after cleanup
        count_after = execute_query(
            "SELECT COUNT(*) as count FROM jobs WHERE user_id = %s AND expires_at IS NULL",
            (user_id,)
        )
        total_after = count_after[0]['count'] if count_after else 0
        deleted = total_before - total_after

        print(f"[AUTONOMOUS] Cleanup complete: deleted {deleted} duplicates ({total_before} → {total_after} unique jobs)", flush=True)

        return {
            'action': 'run_cleanup',
            'duplicates_deleted': deleted,
            'jobs_before': total_before,
            'jobs_after': total_after,
            'success': True
        }

    except Exception as e:
        print(f"[AUTONOMOUS] Cleanup failed: {str(e)}", flush=True)
        return {'action': 'run_cleanup', 'error': str(e), 'success': False}


def _execute_try_new_sources(user_id: str, state: dict) -> dict:
    """
    Let LLM suggest new search term variations based on performance metrics.

    Agent Role: Helper for AUTONOMOUS CYCLE ORCHESTRATOR

    Autonomously decides what new search variations to try:
    - Different role variations (e.g., "AI Engineer" → "Machine Learning Engineer", "Data Scientist")
    - Search in different languages for priority country
    - Adjust search terms based on agent_metrics performance (which sources/roles underperform)

    No hardcoded sources - LLM decides what to try based on:
    - Current target_roles and performance data
    - Priority country and geographic metrics
    - Agent metrics showing which sources have high relevance/success rates
    - Discovered job title variations that didn't match initial search

    Args:
        user_id (str): User ID to suggest new sources for
        state (dict): Pipeline state from _gather_pipeline_state()

    Returns:
        dict: Result with suggested_variations and discovery result
    """
    try:
        from tools.llm import call_llm
        import json

        profile_result = execute_query(
            "SELECT target_roles, preferred_countries FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not profile_result:
            return {'error': 'User profile not found'}

        profile = profile_result[0]
        target_roles = profile.get('target_roles', [])
        priority_country = profile.get('preferred_countries', [''])[0]

        # Get agent metrics to inform LLM about performance
        metrics_result = execute_query(
            """
            SELECT source, target_role, target_country, source_success_rate, country_success_rate, role_avg_score
            FROM agent_metrics
            WHERE user_id = %s
            ORDER BY week_of DESC
            LIMIT 4
            """,
            (user_id,)
        )

        metrics_data = [dict(row) for row in metrics_result] if metrics_result else []

        prompt = f"""Based on the user's job search performance data, suggest new search term variations to try.

User's Target Roles: {target_roles}
Priority Country: {priority_country}

Recent Performance Metrics (last 4 weeks):
{json.dumps(metrics_data, indent=2) if metrics_data else 'No metrics data yet'}

Autonomously decide what new search variations might improve discovery:
1. Different role variations (synonyms, related titles)
2. Variations for priority country (different keywords in local language or regional terms)
3. Adjustments based on performance data (if some sources underperform, try new terms for those areas)

Return ONLY valid JSON (no markdown):
{{
  "suggested_variations": [
    {{"original_role": "AI Engineer", "variation": "Machine Learning Engineer", "reason": "Broader ML-focused companies"}},
    {{"original_role": "AI Engineer", "variation": "Data Scientist", "reason": "Overlapping skill set"}}
  ],
  "language_variations": ["Machine Learning Ingénieur"] if priority_country is French, etc.
}}"""

        response = call_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(response)

        print(f"[AUTONOMOUS] LLM suggested {len(suggestions.get('suggested_variations', []))} new search variations", flush=True)

        # Execute discovery with suggested new terms (merged with original roles)
        new_roles = target_roles.copy()
        for var in suggestions.get('suggested_variations', []):
            if var.get('variation') not in new_roles:
                new_roles.append(var['variation'])

        print(f"[AUTONOMOUS] Running discovery with expanded roles: {new_roles}", flush=True)

        # Create temporary profile with expanded roles for this discovery run
        temp_profile = profile.copy()
        temp_profile['target_roles'] = new_roles

        initial_state = JobState(
            user_id=user_id,
            raw_jobs=[],
            unprocessed_jobs=[],
            processed_count=0,
            applied_count=0,
            review_count=0,
            ignored_count=0,
            error="",
            roles=new_roles,
            profile=temp_profile,
            summary={}
        )

        # Import here to avoid circular imports
        from agents.pipeline import graph

        result = graph.invoke(initial_state)
        discovered = len(result.get('raw_jobs', []))

        return {
            'action': 'try_new_sources',
            'suggested_variations': suggestions.get('suggested_variations', []),
            'jobs_discovered_with_new_terms': discovered,
            'success': True
        }

    except Exception as e:
        print(f"[AUTONOMOUS] try_new_sources failed: {str(e)}", flush=True)
        return {'action': 'try_new_sources', 'error': str(e), 'success': False}


def _hours_since(dt) -> float:
    """
    Calculate hours since a datetime.

    Helper for _gather_pipeline_state().

    Args:
        dt (datetime): Datetime to calculate hours since

    Returns:
        float: Hours since datetime, or 999 if dt is None
    """
    if not dt:
        return 999
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    return delta.total_seconds() / 3600
