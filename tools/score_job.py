"""Compute job-to-profile fit score using hard filters and LLM. Returns score dict with decision."""

import json
from tools.llm import call_llm
from tools.logger import log_agent_run


def score_job(job_id, user_id, job_data, user_profile):
    """Score job against profile. Returns {score, decision, strengths, gaps, summary}."""
    try:
        # Run hard filters first
        filter_result = _run_hard_filters(job_data, user_profile)
        if filter_result:
            return filter_result

        # If required_skills is empty, skip LLM and evaluate by title match only
        required_skills = job_data.get('required_skills', [])
        print(f"[SCORE DEBUG] job_title='{job_data.get('title')}', required_skills={required_skills}, type={type(required_skills)}, bool={bool(required_skills)}")
        if not required_skills:
            print(f"[SCORE] Job '{job_data.get('title')}' has empty required_skills, evaluating by title match only")
            score_data = _evaluate_by_title_match(job_data, user_profile)
        else:
            # Calculate skill overlap
            matched_skills = list(
                set(required_skills) & set(user_profile.get('tech_stack', []))
            )
            missing_skills = list(
                set(required_skills) - set(user_profile.get('tech_stack', []))
            )
            bonus_skills = list(
                set(job_data.get('nice_to_have_skills', [])) & set(user_profile.get('tech_stack', []))
            )

            # Score via LLM
            score_data = _score_with_llm(job_data, user_profile, matched_skills, missing_skills, bonus_skills)

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


def _evaluate_by_title_match(job_data, user_profile):
    """Evaluate job by title match only (for jobs with empty required_skills)."""
    job_title = job_data.get('title', '').lower()
    target_roles = user_profile.get('target_roles', [])

    # Extract keywords from target roles
    role_keywords = set()
    for role in target_roles:
        role_keywords.update(role.lower().split())

    # Add common role keywords
    common_keywords = {'robotics', 'ai', 'engineer', 'computer vision', 'python', 'ml', 'machine learning'}
    role_keywords.update(common_keywords)

    # Check if any keyword appears in job title
    title_has_keyword = any(keyword in job_title for keyword in role_keywords)

    if title_has_keyword:
        print(f"[TITLE MATCH] Job '{job_data.get('title')}' title matches keywords. Score=50, decision='review'")
        return {
            'score': 50,
            'decision': 'review',
            'strengths': ['Job title matches target roles'],
            'gaps': ['Required skills not listed'],
            'summary': 'Job title aligns with target roles. Unable to evaluate skills as they were not listed in the posting.'
        }
    else:
        print(f"[TITLE NO MATCH] Job '{job_data.get('title')}' title does not match target keywords. Score=0, decision='ignore'")
        return {
            'score': 0,
            'decision': 'ignore',
            'strengths': [],
            'gaps': ['Required skills not listed', 'Job title does not match target roles'],
            'summary': 'Job posting did not list required skills and title does not match target roles.'
        }


def _run_hard_filters(job_data, user_profile):
    """Run hard filters. Return early match dict if filter fails, else None."""
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


def _score_with_llm(job_data, user_profile, matched_skills, missing_skills, bonus_skills, retry=True):
    """Call LLM to compute fit score."""
    # Check if required_skills is empty
    has_required_skills = bool(job_data.get('required_skills', []))

    # Adjust weights if skills data is missing
    if not has_required_skills:
        weights_desc = """
Compute a fit score from 0 to 100 based on:
- Role alignment and title match (50% weight) - evaluate if the job role matches target roles
- Experience level match (20% weight)
- Modality match (15% weight)
- Salary match (15% weight)

NOTE: Job posting did not list required skills, so focus on role title match and experience level."""
    else:
        weights_desc = """
Compute a fit score from 0 to 100 based on:
- Skill match (50% weight)
- Role alignment (20% weight)
- Modality match (15% weight)
- Salary match (15% weight)"""

    prompt = f"""You are a career advisor evaluating job fit.
Return only a JSON object with no extra text.

User profile:
- Skills: {user_profile.get('tech_stack', [])}
- Target roles: {user_profile.get('target_roles', [])}
- Preferred modality: {user_profile.get('preferred_modality')}
- Preferred countries: {user_profile.get('preferred_countries', [])}
- Minimum salary: {user_profile.get('salary_min')}

Job details:
- Title: {job_data.get('title')}
- Company: {job_data.get('company')}
- Required skills: {job_data.get('required_skills', []) if has_required_skills else "Not listed"}
- Nice to have: {job_data.get('nice_to_have_skills', []) if job_data.get('nice_to_have_skills') else "Not listed"}
- Experience level: {job_data.get('experience_level')}
- Modality: {job_data.get('modality')}
- Location: {job_data.get('location')}
- Salary range: {job_data.get('salary_min')} - {job_data.get('salary_max')}

{f"Skill analysis: - Matched: {matched_skills}, Missing: {missing_skills}, Bonus: {bonus_skills}" if has_required_skills else "Skill analysis: Job did not list required skills, evaluate based on role title fit"}

{weights_desc}

Return:
{{
  "score": integer (0-100),
  "decision": "apply" | "review" | "ignore",
  "strengths": [list of strings, max 3],
  "gaps": [list of strings, max 3],
  "summary": "one sentence explanation"
}}

Decision rules:
- score >= 85 → "apply"
- score 60-84 → "review"
- score < 60 → "ignore"
"""

    print(f"[GROQ PROMPT] Job '{job_data.get('title')}' at '{job_data.get('company')}':\n{prompt}\n")

    try:
        response = call_llm(prompt)
        print(f"[GROQ RESPONSE] {response}\n")
        score_data = json.loads(response)

        # FALLBACK: If score<60 but title matches target roles, override to 50 with "review"
        score = score_data.get('score', 0)
        print(f"[FALLBACK CHECK] score={score}, job_title='{job_data.get('title')}', required_skills={job_data.get('required_skills')}")

        if score < 60:
            job_title = job_data.get('title', '').lower()
            target_roles = user_profile.get('target_roles', [])

            # Check if any target role keyword appears in job title
            role_keywords = []
            for role in target_roles:
                role_keywords.extend(role.lower().split())

            # Also add common role keywords
            common_keywords = {'robotics', 'ai', 'engineer', 'computer vision', 'python', 'ml', 'machine learning'}
            role_keywords.extend(common_keywords)

            title_has_keyword = any(keyword in job_title for keyword in role_keywords)

            if title_has_keyword:
                print(f"[FALLBACK] Job '{job_data.get('title')}' scored {score} but title matches keywords. Overriding to score=50, decision='review'")
                score_data['score'] = 50
                score_data['decision'] = 'review'
                score_data['summary'] = f"Role title matches target roles despite low score. {score_data.get('summary', '')}"

        return score_data
    except json.JSONDecodeError:
        if not retry:
            raise Exception("LLM returned invalid JSON twice")
        response = call_llm(prompt + "\n\nIMPORTANT: Return ONLY valid JSON.")
        print(f"[GROQ RESPONSE RETRY] {response}\n")
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
