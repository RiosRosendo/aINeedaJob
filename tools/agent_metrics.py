"""
Agent Metrics Collection & Formatting

Autonomous agents use metrics to learn and adapt strategies without hardcoded rules.
Metrics are collected weekly and formatted for LLM consumption.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import json

from tools.db import execute_query, execute_update


def collect_weekly_metrics(user_id: str) -> Dict:
    """
    Aggregate agent_logs and fit_scores into agent_metrics table.

    Called weekly (Sunday 11 PM) to rollup:
    - Source performance (job discovery success rates)
    - Country performance (average scores, interview rates)
    - Role performance (applications, interviews, offers)
    - Application method success
    - Response time tracking

    Returns metrics summary for the week.
    """
    print(f"[METRICS] Starting weekly collection for user {user_id}", flush=True)

    week_of = (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).date()
    week_start = datetime.combine(week_of, datetime.min.time())
    week_end = week_start + timedelta(days=7)

    metrics_collected = 0

    try:
        # 1. SOURCE METRICS: Jobs discovered, scored, success rate
        source_data = execute_query("""
            SELECT j.source, COUNT(*) as discovered,
                   SUM(CASE WHEN fs.score IS NOT NULL THEN 1 ELSE 0 END) as scored,
                   SUM(CASE WHEN fs.score >= 60 THEN 1 ELSE 0 END) as successful_60,
                   SUM(CASE WHEN fs.score >= 85 THEN 1 ELSE 0 END) as successful_85
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
              AND j.created_at >= %s
              AND j.created_at < %s
            GROUP BY j.source
        """, (user_id, user_id, week_start, week_end))

        if source_data:
            for row in source_data:
                source = row.get('source', 'unknown')
                discovered = row.get('discovered', 0)
                scored = row.get('scored', 0)
                successful = row.get('successful_60', 0)

                success_rate = (successful / scored * 100) if scored > 0 else None

                execute_update("""
                    INSERT INTO agent_metrics
                    (user_id, source, source_jobs_discovered, source_jobs_scored,
                     source_success_rate, week_of)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, week_of, source, target_country, target_role)
                    DO UPDATE SET
                        source_jobs_discovered = EXCLUDED.source_jobs_discovered,
                        source_jobs_scored = EXCLUDED.source_jobs_scored,
                        source_success_rate = EXCLUDED.source_success_rate,
                        updated_at = NOW()
                """, (user_id, source, discovered, scored, success_rate, week_of))

                metrics_collected += 1
                print(f"[METRICS] {source}: {discovered} discovered, {scored} scored, "
                      f"{success_rate or 'N/A'}% success", flush=True)

        # 2. COUNTRY METRICS: Average score, success rate, interview rate
        country_data = execute_query("""
            SELECT COALESCE(j.search_country, 'xx') as country,
                   AVG(fs.score)::DECIMAL(5,2) as avg_score,
                   SUM(CASE WHEN fs.score >= 60 THEN 1 ELSE 0 END)::DECIMAL(3,2) /
                   NULLIF(COUNT(*), 0) * 100 as success_rate_60,
                   SUM(CASE WHEN a.status = 'interview' THEN 1 ELSE 0 END)::DECIMAL(3,2) /
                   NULLIF(COUNT(a.id), 0) * 100 as interview_rate
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            LEFT JOIN applications a ON j.id = a.job_id AND a.user_id = %s
            WHERE j.user_id = %s
              AND j.created_at >= %s
              AND j.created_at < %s
            GROUP BY COALESCE(j.search_country, 'xx')
        """, (user_id, user_id, user_id, week_start, week_end))

        if country_data:
            for row in country_data:
                country = row.get('country', 'xx')
                avg_score = row.get('avg_score')
                success_rate = row.get('success_rate_60')
                interview_rate = row.get('interview_rate')

                execute_update("""
                    INSERT INTO agent_metrics
                    (user_id, target_country, country_avg_score, country_success_rate,
                     country_interview_rate, week_of)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, week_of, source, target_country, target_role)
                    DO UPDATE SET
                        country_avg_score = EXCLUDED.country_avg_score,
                        country_success_rate = EXCLUDED.country_success_rate,
                        country_interview_rate = EXCLUDED.country_interview_rate,
                        updated_at = NOW()
                """, (user_id, country, avg_score, success_rate, interview_rate, week_of))

                metrics_collected += 1
                print(f"[METRICS] {country}: avg_score={avg_score}, "
                      f"success={success_rate or 'N/A'}%, interviews={interview_rate or 'N/A'}%",
                      flush=True)

        # 3. ROLE METRICS: Applications sent, interviews, average score
        role_data = execute_query("""
            SELECT j.title,
                   AVG(fs.score)::DECIMAL(5,2) as avg_score,
                   COUNT(DISTINCT a.id) as applications_sent,
                   SUM(CASE WHEN a.status = 'interview' THEN 1 ELSE 0 END) as interviews,
                   SUM(CASE WHEN a.status = 'offer' THEN 1 ELSE 0 END) as offers
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            LEFT JOIN applications a ON j.id = a.job_id AND a.user_id = %s
            WHERE j.user_id = %s
              AND j.created_at >= %s
              AND j.created_at < %s
            GROUP BY j.title
            HAVING COUNT(DISTINCT a.id) > 0 OR COUNT(*) > 2
        """, (user_id, user_id, user_id, week_start, week_end))

        if role_data:
            for row in role_data:
                role = row.get('title', 'unknown')[:100]
                avg_score = row.get('avg_score')
                applications = row.get('applications_sent', 0)
                interviews = row.get('interviews', 0)

                execute_update("""
                    INSERT INTO agent_metrics
                    (user_id, target_role, role_avg_score, role_applications_sent,
                     role_interviews_received, week_of)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, week_of, source, target_country, target_role)
                    DO UPDATE SET
                        role_avg_score = EXCLUDED.role_avg_score,
                        role_applications_sent = EXCLUDED.role_applications_sent,
                        role_interviews_received = EXCLUDED.role_interviews_received,
                        updated_at = NOW()
                """, (user_id, role, avg_score, applications, interviews, week_of))

                metrics_collected += 1
                print(f"[METRICS] {role[:40]}: {avg_score} avg, "
                      f"{applications} apps, {interviews} interviews", flush=True)

        # 4. APPLICATION METHOD METRICS: Form vs Email success rates
        method_data = execute_query("""
            SELECT COALESCE(al.details->>'method', 'unknown') as method,
                   COUNT(*) as total,
                   SUM(CASE WHEN al.status = 'applied' THEN 1 ELSE 0 END) as successful
            FROM agent_logs al
            WHERE al.user_id = %s
              AND al.agent = 'application'
              AND al.created_at >= %s
              AND al.created_at < %s
            GROUP BY COALESCE(al.details->>'method', 'unknown')
        """, (user_id, week_start, week_end))

        if method_data:
            for row in method_data:
                method = row.get('method', 'unknown')
                total = row.get('total', 0)
                successful = row.get('successful', 0)
                success_rate = (successful / total * 100) if total > 0 else None

                execute_update("""
                    INSERT INTO agent_metrics
                    (user_id, application_method, method_success_rate, week_of)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, week_of, source, target_country, target_role)
                    DO UPDATE SET
                        method_success_rate = EXCLUDED.method_success_rate,
                        updated_at = NOW()
                """, (user_id, method, success_rate, week_of))

                metrics_collected += 1
                print(f"[METRICS] Method {method}: {total} attempted, "
                      f"{successful} successful ({success_rate or 'N/A'}%)", flush=True)

        print(f"[METRICS] Weekly collection complete: {metrics_collected} metric rows collected",
              flush=True)

        return {
            "user_id": user_id,
            "week_of": str(week_of),
            "metrics_collected": metrics_collected
        }

    except Exception as e:
        print(f"[METRICS] ERROR: {str(e)}", flush=True)
        return {
            "user_id": user_id,
            "week_of": str(week_of),
            "error": str(e)
        }


def get_metrics_for_llm(user_id: str) -> str:
    """
    Format agent_metrics into a readable text block for LLM consumption.

    LLM uses this to autonomously decide:
    - Which sources to prioritize
    - Which countries to search
    - Which roles to focus on
    - Which application methods work best

    No hardcoded rules - LLM decides based on data patterns.
    """

    # Get metrics from last 4 weeks (rolling window)
    cutoff_date = (datetime.utcnow() - timedelta(days=28)).date()

    metrics = execute_query("""
        SELECT * FROM agent_metrics
        WHERE user_id = %s AND week_of >= %s
        ORDER BY week_of DESC
    """, (user_id, cutoff_date))

    if not metrics:
        return "No metrics available yet. Data will be available after first week of activity."

    # Format into readable sections
    sections = []

    # Source Performance
    sources = {}
    countries = {}
    roles = {}
    methods = {}

    for row in metrics:
        source = row.get('source')
        if source and row.get('source_success_rate'):
            if source not in sources:
                sources[source] = []
            sources[source].append(row.get('source_success_rate'))

        country = row.get('target_country')
        if country and row.get('country_avg_score'):
            if country not in countries:
                countries[country] = []
            countries[country].append(row.get('country_avg_score'))

        role = row.get('target_role')
        if role and row.get('role_avg_score'):
            if role not in roles:
                roles[role] = []
            roles[role].append(row.get('role_avg_score'))

        method = row.get('application_method')
        if method and row.get('method_success_rate'):
            if method not in methods:
                methods[method] = []
            methods[method].append(row.get('method_success_rate'))

    # Build report
    report = "AUTONOMOUS AGENT PERFORMANCE METRICS (Last 4 Weeks)\n"
    report += "=" * 60 + "\n\n"

    if sources:
        report += "JOB SOURCES (Success Rate % for jobs scoring >= 60):\n"
        for source in sorted(sources.keys()):
            rates = [r for r in sources[source] if r is not None]
            if rates:
                avg_rate = sum(rates) / len(rates)
                report += f"  {source}: {avg_rate:.1f}% success\n"
        report += "\n"

    if countries:
        report += "GEOGRAPHIC PERFORMANCE (Average Fit Scores):\n"
        for country in sorted(countries.keys()):
            scores = [s for s in countries[country] if s is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                report += f"  {country}: {avg_score:.1f}% fit\n"
        report += "\n"

    if roles:
        report += "ROLE PERFORMANCE (Average Fit Scores):\n"
        for role in sorted(roles.keys())[:10]:  # Top 10 roles
            scores = [s for s in roles[role] if s is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                report += f"  {role[:40]}: {avg_score:.1f}% fit\n"
        report += "\n"

    if methods:
        report += "APPLICATION METHODS (Success Rate %):\n"
        for method in sorted(methods.keys()):
            rates = [r for r in methods[method] if r is not None]
            if rates:
                avg_rate = sum(rates) / len(rates)
                report += f"  {method}: {avg_rate:.1f}% success\n"
        report += "\n"

    report += "INSTRUCTIONS: Use this data to autonomously decide strategy.\n"
    report += "No hardcoded rules - you decide based on patterns and probabilities."

    return report


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python agent_metrics.py <user_id> [collect|format]")
        sys.exit(1)

    user_id = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "collect"

    if action == "collect":
        result = collect_weekly_metrics(user_id)
        print(f"\nResult: {result}")
    elif action == "format":
        metrics_text = get_metrics_for_llm(user_id)
        print(metrics_text)
