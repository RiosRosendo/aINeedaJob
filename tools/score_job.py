"""Compute job-to-profile fit score using hard filters and LLM. Returns score dict with decision."""

import json
from tools.llm import call_llm
from agents.state import SCORE_THRESHOLDS


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

        # Check language requirements and adjust score
        score_data = _check_language_requirements(score_data, job_data, user_profile)

        # Check priority country match and let LLM decide boost
        score_data = _apply_priority_country_boost(score_data, job_data, user_profile)

        return score_data

    except Exception as e:
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
- Experience Level: {user_profile.get('experience_level', 'Junior')}
- Experience: {user_profile.get('cv_data', {}).get('experience', [])}
- Projects: {user_profile.get('cv_data', {}).get('projects', [])}
- Education: {user_profile.get('cv_data', {}).get('education', [])}
- Languages: {user_profile.get('cv_data', {}).get('languages', [])}
- Nationality: {user_profile.get('cv_data', {}).get('nationality', 'Unknown')}
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
  * Match skills and job requirements by semantic meaning across any language.
    The LLM should autonomously understand that equivalent terms in different
    languages refer to the same concept.
  * Evaluate skills autonomously based on semantic meaning, not exact text match
- Experience level: evaluate if job's required experience level matches the user's profile
  * User's self-reported level: {user_profile.get('experience_level', 'Junior')}
  * CV-detected level: {user_profile.get('cv_data', {}).get('detected_experience_level', 'Unknown') if isinstance(user_profile.get('cv_data'), dict) else json.loads(user_profile.get('cv_data', '{}')).get('detected_experience_level', 'Unknown')}
  * Consider: self-reported level, CV-detected level, actual CV content
  * If there is a significant mismatch (e.g., Senior job for Junior candidate), reflect this in the score
  * The LLM evaluates autonomously - no hardcoded penalties
  * Balance experience gap with other strengths (skills, education, projects)
- Education relevance (degree, certifications)
- Languages required for the role
- Salary expectations

Return:
{{
  "score": integer (0-100),
  "decision": "apply" | "review" | "ignore",
  "strengths": [list of 2-3 strengths],
  "gaps": [list of 2-3 gaps],
  "summary": "one sentence explanation"
}}

Decision rules (from SCORE_THRESHOLDS in agents/state.py):
- score >= {SCORE_THRESHOLDS['auto_apply']} → "apply"
- score {SCORE_THRESHOLDS['review']}-{SCORE_THRESHOLDS['auto_apply']-1} → "review"
- score < {SCORE_THRESHOLDS['review']} → "ignore"
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


def _check_language_requirements(score_data, job_data, user_profile):
    """Check if job has language requirements and adjust score accordingly."""
    try:
        from tools.db import execute_query

        # Get user's CV data with languages
        cv_data = user_profile.get('cv_data')
        if not cv_data:
            return score_data

        # Parse if string
        if isinstance(cv_data, str):
            cv_data = json.loads(cv_data)

        user_languages = cv_data.get('languages', [])
        if not user_languages:
            return score_data

        # Extract language names (e.g., "Spanish Native" → "Spanish")
        user_lang_names = set()
        for lang_entry in user_languages:
            if isinstance(lang_entry, dict):
                lang_name = lang_entry.get('language', '').lower()
            else:
                lang_name = str(lang_entry).split()[0].lower()
            if lang_name:
                user_lang_names.add(lang_name)

        # Detect language requirements in job description using LLM
        job_description = job_data.get('description_raw', '')
        if not job_description:
            return score_data

        prompt = f"""Analyze this job description and detect any language requirements.

Job Description:
{job_description[:1000]}

Return ONLY a JSON object:
{{
  "required_languages": ["language1", "language2"],
  "required_level": "intermediate or higher",
  "confidence": 0-100
}}

If no language requirement found, return empty languages list.
"""

        response = call_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()

        try:
            lang_data = json.loads(response)
            required_langs = {l.lower() for l in lang_data.get('required_languages', [])}

            if not required_langs:
                return score_data

            # Check if user speaks required languages
            missing_langs = required_langs - user_lang_names
            has_required_langs = len(required_langs) > 0 and len(missing_langs) == 0

            if missing_langs and lang_data.get('confidence', 0) > 70:
                # User doesn't speak required language - reduce score by 30
                original_score = score_data.get('score', 0)
                new_score = max(0, original_score - 30)
                score_data['score'] = new_score
                score_data['gaps'].append(f"Missing language: {', '.join(missing_langs)}")
                print(f"[LANGUAGE] Reduced score from {original_score} to {new_score} due to language mismatch", flush=True)

            elif has_required_langs:
                # User speaks required language - small bonus
                original_score = score_data.get('score', 0)
                new_score = min(100, original_score + 5)
                score_data['score'] = new_score
                print(f"[LANGUAGE] Increased score from {original_score} to {new_score} due to language match", flush=True)

        except:
            pass

        return score_data

    except Exception as e:
        print(f"[LANGUAGE CHECK] Warning: {str(e)}", flush=True)
        return score_data


def _apply_priority_country_boost(score_data, job_data, user_profile):
    """If job is in user's priority country, let LLM decide score boost."""
    try:
        priority_country = user_profile.get('priority_country')
        search_country = job_data.get('search_country')

        # No boost if user doesn't have priority country or job doesn't have search_country context
        if not priority_country or not search_country:
            return score_data

        # Normalize for comparison (both should be 2-letter codes)
        priority_code = priority_country.lower().strip()
        search_code = search_country.lower().strip()

        # If they don't match, no boost
        if priority_code != search_code:
            return score_data

        # Country match detected - ask LLM how much to boost
        original_score = score_data.get('score', 0)

        prompt = f"""This job is in the user's priority country ({priority_country.upper()}).
User's original match score: {original_score}/100

Given this priority country match, should the score be adjusted upward? Consider:
- The user prioritizes this country, so a match there is more valuable
- But don't artificially inflate scores - only boost if it's justified by the match quality
- The boost should reflect how much the country priority matters relative to the overall fit

Return ONLY a JSON object:
{{
  "boost_amount": integer 0-15,
  "reasoning": "brief explanation"
}}

Boost examples:
- 0: Country match doesn't add value (job was already poor fit)
- 5: Minor boost for being in priority country
- 10: Moderate boost - job is good fit AND in priority country
- 15: Significant boost - country priority is important for this user's goals
"""

        response = call_llm(prompt)
        response = response.replace("```json", "").replace("```", "").strip()
        decision = json.loads(response)

        boost = decision.get('boost_amount', 0)
        if boost > 0:
            new_score = min(100, original_score + boost)
            score_data['score'] = new_score
            print(f"[PRIORITY_COUNTRY] {priority_country.upper()} match: boosted {original_score} → {new_score} (+{boost})", flush=True)

        return score_data

    except Exception as e:
        print(f"[PRIORITY_COUNTRY] Warning: {str(e)}", flush=True)
        return score_data
