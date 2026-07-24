"""Compute job-to-profile fit score using hard filters and LLM. Returns score dict with decision."""

import json
from tools.llm import call_llm
from tools.logger import log_agent_run


def score_job(job_id, user_id, job_data, user_profile):
    """Score job against profile. Returns {score, decision, strengths, gaps, summary}."""
    try:
        # Run hard filters first (modality, salary, location)
        filter_result = _run_hard_filters(job_data, user_profile)
        if filter_result:
            return filter_result

        # Call LLM with raw data - let it handle skill evaluation
        score_data = _score_with_llm(job_data, user_profile)

        # Validate output
        _validate_score_output(score_data)

        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='job_match',
            status='success',
            details={'score': score_data.get('score'), 'decision': score_data.get('decision')}
        )

        return score_data

    except Exception as e:
        log_agent_run(
            user_id=user_id,
            job_id=job_id,
            agent='job_match',
            status='failed',
            details={'error': str(e)}
        )
        raise Exception(f"Job scoring failed: {str(e)}")


def _run_hard_filters(job_data, user_profile):
    """Run hard filters on objective constraints. Return early if filter fails, else None."""
    user_modality = user_profile.get('preferred_modality', 'remote')
    job_modality = job_data.get('modality', 'unknown')
    if user_modality != 'unknown' and job_modality != 'unknown':
        if user_modality == 'remote' and job_modality != 'remote':
            return {'score': 0, 'decision': 'ignore', 'strengths': [], 'gaps': [], 'summary': 'Modality mismatch'}
        if user_modality == 'hybrid' and job_modality == 'on-site':
            return {'score': 0, 'decision': 'ignore', 'strengths': [], 'gaps': [], 'summary': 'Modality mismatch'}
    user_salary_min = user_profile.get('salary_min')
    job_salary_max = job_data.get('salary_max')
    if user_salary_min and job_salary_max and job_salary_max < user_salary_min:
        return {'score': 0, 'decision': 'ignore', 'strengths': [], 'gaps': [], 'summary': 'Salary below minimum'}
    user_countries = user_profile.get('preferred_countries', [])
    job_location = job_data.get('location', '')
    if user_countries and job_location:
        if not any(country.lower() in job_location.lower() for country in user_countries):
            return {'score': 0, 'decision': 'ignore', 'strengths': [], 'gaps': [], 'summary': 'Country mismatch'}
    return None


def _score_with_llm(job_data, user_profile, retry=True):
    """Call LLM to evaluate fit. Pass raw data and let LLM handle skill matching."""
    prompt = f"""You are a career advisor evaluating job fit.
Return only a JSON object with no extra text.

User Profile:
- Skills: {user_profile.get('tech_stack', [])}
- Target Roles: {user_profile.get('target_roles', [])}
- Preferred Modality: {user_profile.get('preferred_modality')}
- Preferred Countries: {user_profile.get('preferred_countries', [])}
- Minimum Salary: ${user_profile.get('salary_min')}

Job Details:
- Title: {job_data.get('title')}
- Company: {job_data.get('company')}
- Required Skills: {job_data.get('required_skills', [])}
- Nice to Have: {job_data.get('nice_to_have_skills', [])}
- Experience Level: {job_data.get('experience_level')}
- Modality: {job_data.get('modality')}
- Location: {job_data.get('location')}
- Salary: ${job_data.get('salary_min', 'N/A')} - ${job_data.get('salary_max', 'N/A')}

Evaluate fit considering:
- Title/role alignment with target roles
- Skill match (including semantic understanding: LangGraph = agent orchestration, OpenCV = computer vision, etc.)
  * Match skills by meaning across languages:
    - "Traitement d'image" or "Image Processing" = Computer Vision/Image Processing
    - "Systèmes embarqués" or "Embedded Systems" = same concept in French/English
    - "Logiciel embarqué" or "Embedded Software" = same concept
    - "Développeur" or "Developer/Engineer" = same role type
  * Evaluate skills autonomously based on semantic meaning, not exact text match
- Experience level fit
- Salary expectations

Return:
{{
  "score": integer (0-100),
  "decision": "apply" | "review" | "ignore",
  "strengths": [list of 2-3 strengths],
  "gaps": [list of 2-3 gaps],
  "summary": "one sentence explanation"
}}

Decision rules:
- score >= 85 → "apply"
- score 60-84 → "review"
- score < 60 → "ignore"
"""

    try:
        response = call_llm(prompt)
        print(f"[SCORE] {job_data.get('title')} @ {job_data.get('company')}: {response[:100]}")
        return json.loads(response)
    except json.JSONDecodeError:
        if not retry:
            raise Exception("LLM returned invalid JSON twice")
        response = call_llm(prompt + "\n\nIMPORTANT: Return ONLY valid JSON.")
        print(f"[SCORE RETRY] {response[:100]}")
        return json.loads(response)


def _validate_score_output(score_data):
    """Validate LLM output."""
    if not isinstance(score_data.get('score'), int) or not (0 <= score_data['score'] <= 100):
        raise Exception("score must be integer 0-100")

    if score_data.get('decision') not in {'apply', 'review', 'ignore'}:
        raise Exception("decision must be apply, review, or ignore")

    if not isinstance(score_data.get('strengths'), list):
        score_data['strengths'] = []
    if not isinstance(score_data.get('gaps'), list):
        score_data['gaps'] = []
