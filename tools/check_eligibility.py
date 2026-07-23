"""
Work Eligibility Agent - checks if user can legally work in job's country.

Evaluates:
- User nationality/citizenship
- Job location (country)
- Job modality (remote jobs are always eligible)
- Visa/work permit requirements mentioned in job description
- Any citizenship restrictions in job posting

Uses Groq LLM for nuanced legal evaluation (different countries have different visa programs).
"""

import os
import json
from groq import Groq
from tools.db import execute_query


def check_work_eligibility(user_id: str, job_id: str) -> dict:
    """
    Check if user can legally work in the job's country.

    Args:
        user_id: User ID (to fetch nationality from cv_data)
        job_id: Job ID (to fetch country and job type)

    Returns:
        {
            "eligible": true/false,
            "confidence": "high/medium/low",
            "reason": "explanation of the eligibility decision",
            "visa_required": true/false,
            "visa_type": "work visa, H1-B, EU Blue Card, etc." or null,
            "recommendation": "what the user should do"
        }
    """
    try:
        print(f"[ELIGIBILITY] Checking work eligibility for user {user_id}, job {job_id}", flush=True)

        # Fetch user's nationality from cv_data in user_profiles
        cv_result = execute_query(
            "SELECT cv_data FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )

        if not cv_result:
            print(f"[ELIGIBILITY] No CV found for user {user_id}, assuming eligible", flush=True)
            return {
                "eligible": True,
                "confidence": "low",
                "reason": "No CV data found - cannot verify eligibility, assuming eligible",
                "visa_required": False,
                "visa_type": None,
                "recommendation": "Update your CV with nationality information for accurate eligibility checks"
            }

        cv_data = cv_result[0].get('cv_data', {})
        if isinstance(cv_data, str):
            cv_data = json.loads(cv_data)

        user_nationality = cv_data.get('nationality', 'Unknown')
        user_citizenship = cv_data.get('citizenship', 'Unknown')

        # Fetch job location and modality
        job_result = execute_query(
            "SELECT location, modality, title, description_raw FROM jobs WHERE id = %s AND user_id = %s",
            (job_id, user_id)
        )

        if not job_result:
            print(f"[ELIGIBILITY] Job {job_id} not found for user {user_id}", flush=True)
            return {
                "eligible": False,
                "confidence": "high",
                "reason": "Job not found",
                "visa_required": False,
                "visa_type": None,
                "recommendation": "Unable to verify job"
            }

        job = job_result[0]
        job_location = job.get('location', 'Unknown')
        job_modality = job.get('modality', 'unknown')
        job_title = job.get('title', 'Unknown')
        job_description = job.get('description_raw', '')

        # Remote jobs are always eligible regardless of country
        if job_modality == 'remote':
            print(f"[ELIGIBILITY] Job {job_id} is REMOTE - always eligible", flush=True)
            return {
                "eligible": True,
                "confidence": "high",
                "reason": f"This is a remote position, so you can work from Mexico regardless of job location",
                "visa_required": False,
                "visa_type": None,
                "recommendation": "You're eligible to apply! Remote positions have no work permit restrictions."
            }

        # Extract country from location string
        job_country = _extract_country_from_location(job_location)

        print(f"[ELIGIBILITY] User nationality: {user_nationality}, Job country: {job_country}, Modality: {job_modality}", flush=True)

        # Use Groq LLM to evaluate eligibility
        eligibility_result = _evaluate_eligibility_with_llm(
            user_nationality=user_nationality,
            user_citizenship=user_citizenship,
            job_country=job_country,
            job_modality=job_modality,
            job_title=job_title,
            job_description=job_description
        )

        print(f"[ELIGIBILITY] Result for job {job_id}: {eligibility_result}", flush=True)
        return eligibility_result

    except Exception as e:
        print(f"[ELIGIBILITY] Error checking eligibility: {type(e).__name__}: {str(e)}", flush=True)
        return {
            "eligible": True,
            "confidence": "low",
            "reason": f"Error during eligibility check: {str(e)}",
            "visa_required": False,
            "visa_type": None,
            "recommendation": "Please review the job requirements manually for work authorization"
        }


def _extract_country_from_location(location_str: str) -> str:
    """Extract country name from location string."""
    if not location_str:
        return "Unknown"

    location_lower = location_str.lower().strip()

    # Country name mappings
    country_keywords = {
        "united states": "United States",
        "usa": "United States",
        "america": "United States",
        "canada": "Canada",
        "mexico": "Mexico",
        "uk": "United Kingdom",
        "united kingdom": "United Kingdom",
        "germany": "Germany",
        "france": "France",
        "italy": "Italy",
        "spain": "Spain",
        "netherlands": "Netherlands",
        "japan": "Japan",
        "china": "China",
        "india": "India",
        "australia": "Australia",
        "uae": "United Arab Emirates",
        "united arab emirates": "United Arab Emirates",
        "singapore": "Singapore",
    }

    # Check for direct matches
    for keyword, country in country_keywords.items():
        if keyword in location_lower:
            return country

    # Return as-is if no match found (fallback)
    return location_str.split(',')[-1].strip() if ',' in location_str else location_str


def _evaluate_eligibility_with_llm(
    user_nationality: str,
    user_citizenship: str,
    job_country: str,
    job_modality: str,
    job_title: str,
    job_description: str
) -> dict:
    """Use Groq LLM to evaluate work eligibility."""
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = f"""You are an immigration law expert evaluating work eligibility.

USER PROFILE:
- Nationality: {user_nationality}
- Citizenship: {user_citizenship}

JOB DETAILS:
- Title: {job_title}
- Location: {job_country}
- Modality: {job_modality}
- Description: {job_description[:500]}

Evaluate whether this person can legally work in {job_country} for this {job_modality} position.

Consider:
1. Bilateral agreements between {user_nationality} and {job_country}
2. Common visa programs (work visa, digital nomad, etc.)
3. Any specific visa requirements mentioned in the job description
4. Whether the position is hiring internationally

Provide a JSON response with:
{{
    "eligible": true/false,
    "confidence": "high/medium/low",
    "reason": "brief explanation",
    "visa_required": true/false,
    "visa_type": "e.g., 'work visa', 'H1-B', 'EU Blue Card', 'digital nomad visa'",
    "recommendation": "what the user should do"
}}

Be practical: if work permits exist and are commonly granted, consider the person eligible.
Only mark as ineligible if the country explicitly forbids or severely restricts hiring from this nationality."""

        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Low temperature for consistent legal evaluation
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()

        # Extract JSON from response
        result = _extract_json_from_response(result_text)

        if result:
            return result
        else:
            print(f"[ELIGIBILITY] Could not parse LLM response: {result_text}", flush=True)
            return {
                "eligible": True,
                "confidence": "low",
                "reason": "Unable to definitively evaluate - please check local visa requirements",
                "visa_required": False,
                "visa_type": None,
                "recommendation": "Contact the employer or immigration authority for definitive guidance"
            }

    except Exception as e:
        print(f"[ELIGIBILITY] LLM error: {type(e).__name__}: {str(e)}", flush=True)
        return {
            "eligible": True,
            "confidence": "low",
            "reason": f"Unable to evaluate: {str(e)}",
            "visa_required": False,
            "visa_type": None,
            "recommendation": "Check job requirements and visa eligibility manually"
        }


def _extract_json_from_response(text: str) -> dict or None:
    """Extract JSON object from LLM response."""
    try:
        # Try direct JSON parsing first
        return json.loads(text)
    except:
        pass

    # Try to find JSON block in markdown code fence
    if "```json" in text:
        try:
            start = text.index("```json") + 7
            end = text.index("```", start)
            json_str = text[start:end].strip()
            return json.loads(json_str)
        except:
            pass

    # Try to find JSON block without language specifier
    if "```" in text:
        try:
            start = text.index("```") + 3
            end = text.index("```", start)
            json_str = text[start:end].strip()
            return json.loads(json_str)
        except:
            pass

    # Try to find JSON object with {}
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        json_str = text[start:end]
        return json.loads(json_str)
    except:
        pass

    return None
