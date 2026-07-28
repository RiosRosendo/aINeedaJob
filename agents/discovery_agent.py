"""
Discovery Agent - autonomous job discovery across all job boards.

Handles the Discovery phase of the WAT pipeline:
- Searches all configured job boards (Adzuna, Muse, Jobicy, Remotive, OCC México)
- Autonomously translates roles to local languages per country
- Deduplicates and saves discovered jobs to database
- Tags jobs with search_country for geographic analytics

This agent runs on-demand via API endpoints or scheduled daily.
"""

from agents.state import JobState, map_country_to_adzuna_code
from tools.db import execute_query
from tools.search_adzuna import search_adzuna
from tools.search_themuse import search_themuse
from tools.search_jobicy import search_jobicy_jobs
from tools.search_remotive import search_remotive_jobs
from tools.search_occ import search_occ_for_mexico
from tools.save_jobs import save_jobs
from tools.llm import call_llm
import json


def discovery_node(state: JobState) -> JobState:
    """
    Search all preferred countries for jobs and save to database.

    Agent Role: DISCOVERY AGENT in WAT framework

    Orchestrates multi-country job search:
    1. Loads user profile (target_roles, preferred_countries, salary_min, modality)
    2. For each preferred country:
       - Searches Adzuna with English roles
       - Autonomously translates roles to country's primary language
       - Searches Adzuna again with local-language roles
       - For Mexico: also searches OCC Mundial (largest Mexico job board)
       - Tags each job with search_country code for analytics
    3. Also searches global job boards (Muse, Jobicy, Remotive) without country filtering
    4. Combines and deduplicates all discovered jobs (by URL + user_id)
    5. Saves to database with status='discovered' and search_country tag
    6. Queries unprocessed jobs (status in discovered/parsed, no fit_score yet) for next phase

    Tools Called:
    - search_adzuna(): Adzuna API search by roles/country/salary
    - _translate_roles_for_country(): LLM-based autonomous role translation
    - search_themuse(): Muse API global job search
    - search_jobicy_jobs(): Jobicy API free remote job search
    - search_remotive_jobs(): Remotive API free remote job search
    - search_occ_for_mexico(): OCC México scraper for Mexico-specific jobs
    - save_jobs(): Deduplication and database insertion

    Args:
        state (JobState): Pipeline state with user_id and optional pre-set roles

    Returns:
        JobState: Updated state with raw_jobs, unprocessed_jobs, roles, profile filled in
    """
    print(f"[DISCOVERY] Starting for user_id={state.get('user_id')}")
    try:
        user_id = state.get("user_id")
        if not user_id:
            raise Exception("user_id required")

        # Get profile
        profile_result = execute_query(
            "SELECT target_roles, preferred_countries, preferred_modality, salary_min FROM user_profiles WHERE user_id = %s",
            (user_id,)
        )
        if not profile_result:
            raise Exception("User profile not found")
        p = profile_result[0]
        state["profile"] = p
        print(f"[DISCOVERY] Profile loaded: {len(p.get('target_roles', []))} roles")

        # Use roles from request if provided, otherwise use profile roles
        roles = state.get("roles") or p.get("target_roles")
        state["roles"] = roles

        # Search ALL preferred countries
        adzuna_jobs = []
        preferred_countries = p.get("preferred_countries", [])
        searched_countries = []
        skipped_countries = []

        if isinstance(preferred_countries, list) and len(preferred_countries) > 0:
            for country_name in preferred_countries:
                country_code = map_country_to_adzuna_code(country_name)

                if country_code:
                    try:
                        print(f"[DISCOVERY] Searching {country_name} ({country_code})")

                        # Search with English roles
                        jobs_en = search_adzuna(roles, country_code, p.get("salary_min"))

                        # Autonomously detect country language and translate roles
                        local_roles = _translate_roles_for_country(roles, country_code)

                        # If translations are different from English, also search with local language
                        jobs_local = []
                        if local_roles and local_roles != roles:
                            jobs_local = search_adzuna(local_roles, country_code, p.get("salary_min"))
                            print(f"[DISCOVERY] {country_name} ({country_code}): Adzuna English={len(jobs_en)}, Adzuna Local={len(jobs_local)}")
                        else:
                            print(f"[DISCOVERY] {country_name} ({country_code}): Adzuna English={len(jobs_en)} (no local translation needed)")

                        jobs = jobs_en + jobs_local

                        # For Mexico, also search OCC Mundial (Mexico's biggest job board)
                        jobs_occ = []
                        if country_code.lower() == "mx":
                            print(f"[DISCOVERY] Searching OCC Mundial for Mexico (translated roles: {local_roles})")
                            jobs_occ = search_occ_for_mexico(local_roles if local_roles else roles)
                            print(f"[DISCOVERY] OCC Mundial found {len(jobs_occ)} jobs")
                            jobs = jobs + jobs_occ
                            print(f"[DISCOVERY] {country_name} ({country_code}): Adzuna+OCC total={len(jobs)}")

                        # Tag each job with the country it was discovered from
                        for job in jobs:
                            job['search_country'] = country_code.lower()

                        adzuna_jobs.extend(jobs)
                        searched_countries.append(f"{country_name} ({country_code})")
                    except Exception as e:
                        print(f"[DISCOVERY] Error searching {country_name}: {str(e)}")
                        skipped_countries.append(country_name)
                else:
                    print(f"[DISCOVERY] Country '{country_name}' not supported by Adzuna, skipping")
                    skipped_countries.append(country_name)
        else:
            print(f"[DISCOVERY] No preferred countries configured, skipping Adzuna search")

        # Search Muse (global, no country filtering needed)
        themuse_jobs = search_themuse(roles, p.get("preferred_modality"))

        # Search Jobicy (free API, no auth, remote jobs only)
        jobicy_jobs = []
        try:
            jobicy_jobs = search_jobicy_jobs(roles, count=50)
        except Exception as e:
            print(f"[DISCOVERY] Jobicy search error: {str(e)}")
            # Continue with other sources if Jobicy fails

        # Search Remotive (free API, no auth, remote jobs only)
        remotive_jobs = []
        try:
            remotive_jobs = search_remotive_jobs(roles, limit=50)
        except Exception as e:
            print(f"[DISCOVERY] Remotive search error: {str(e)}")
            # Continue with other sources if Remotive fails

        # Combine all jobs and save with their search_country context
        all_jobs = adzuna_jobs + themuse_jobs + jobicy_jobs + remotive_jobs

        # save_jobs will use search_country from job objects (set during Adzuna search)
        # Global jobs (Muse, Jobicy, Remotive) won't have search_country set
        save_result = save_jobs(user_id, all_jobs)
        state["raw_jobs"] = all_jobs
        print(f"[DISCOVERY] Searched countries: {searched_countries}")
        if skipped_countries:
            print(f"[DISCOVERY] Skipped countries: {skipped_countries}")
        print(f"[DISCOVERY] Jobs: Adzuna={len(adzuna_jobs)}, Muse={len(themuse_jobs)}, Jobicy={len(jobicy_jobs)}, Remotive={len(remotive_jobs)}, Total={len(all_jobs)}")
        print(f"[DISCOVERY] Save result: {save_result}")

        # Get ALL unprocessed jobs for this user (discovered/parsed without fit_score for this user)
        # This scopes jobs to the user's own records. If the same job URL exists for another user,
        # they have their own separate job record and fit_score - no cross-user deduplication.
        unprocessed = execute_query(
            """
            SELECT j.id, j.title, j.company, j.description_raw, j.source
            FROM jobs j
            LEFT JOIN fit_scores fs ON j.id = fs.job_id AND fs.user_id = %s
            WHERE j.user_id = %s
              AND j.status IN ('discovered', 'parsed')
              AND fs.id IS NULL
            ORDER BY j.created_at DESC
            """,
            (user_id, user_id)
        )
        state["unprocessed_jobs"] = unprocessed or []
        print(f"[DISCOVERY] Found {len(state['unprocessed_jobs'])} unprocessed jobs")

        return state
    except Exception as e:
        state["error"] = f"Discovery failed: {str(e)}"
        return state


def _translate_roles_for_country(roles: list, country_code: str) -> list:
    """
    Autonomously translate English job roles to a country's primary job-search language.

    Agent Role: Helper for DISCOVERY AGENT

    Uses LLM to:
    1. Detect the primary professional language for a country's job market
    2. Translate English role names to that language (e.g., "AI Engineer" → "Ingeniero IA" for Mexico)
    3. Return translations as JSON array of role names

    Supports any country and language pair (not hardcoded translations).
    Validates output: filters out explanation text (strings > 50 chars or with newlines).

    Tools Called:
    - call_llm(): Groq LLM for language detection and autonomous translation

    Args:
        roles (list): English target roles (e.g., ["AI Engineer", "Robotics Engineer"])
        country_code (str): Adzuna country code (e.g., "mx", "jp", "es")

    Returns:
        list: Translated role names in country's primary language, or fallback to English if translation fails
    """
    if not roles or not country_code:
        return []

    try:
        roles_str = ", ".join(roles)
        prompt = f"""You are a job market expert. Translate these English job roles to the PRIMARY professional language used in job postings for {country_code.upper()}.

First, identify the primary job-search language for {country_code.upper()}, then translate the roles to that language.

English roles: {roles_str}

Return ONLY a valid JSON array of translated job titles. No explanation, no markdown.
Example: ["Ingeniero en Robótica", "Ingeniero de Sistemas Embebidos"]"""

        response = call_llm(prompt).strip()
        print(f"[TRANSLATION] Raw response for {country_code}: '{response[:100]}'", flush=True)

        # Remove markdown code blocks if present
        if response.startswith("```"):
            response = response.split("```")[1].strip()
            if response.startswith("json"):
                response = response[4:].strip()

        # Parse JSON array
        translated_roles = json.loads(response)

        # Validate: filter out strings longer than 50 chars or containing newlines
        # Those are likely explanation text, not actual role names
        translated_roles = [
            r.strip() for r in translated_roles
            if isinstance(r, str) and len(r) <= 50 and '\n' not in r and r.strip()
        ]

        print(f"[TRANSLATION] Country: {country_code}, English roles: {roles}")
        print(f"[TRANSLATION] {country_code.upper()} roles: {translated_roles}")
        return translated_roles

    except Exception as e:
        print(f"[TRANSLATION] Error translating for {country_code}: {str(e)}, falling back to English")
        return roles
