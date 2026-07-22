"""
LinkedIn jobs search using Jsearch API on RapidAPI.

Jsearch provides aggregated LinkedIn jobs data without needing LinkedIn API access.
"""

import os
import requests
from typing import List, Dict


def search_linkedin_jobs(roles: List[str], location: str = None, count: int = 10) -> List[Dict]:
    """
    Search for jobs on LinkedIn using Jsearch API.

    Args:
        roles: List of job titles to search for (e.g., ["AI Engineer", "Machine Learning"])
        location: Location filter (optional, e.g., "United States", "Remote")
        count: Number of results to fetch (default 10)

    Returns:
        List of job listings in standardized format matching Adzuna results:
        [
            {
                "id": "unique_id",
                "title": "Job Title",
                "company": "Company Name",
                "description": "Job description",
                "location": "City, Country",
                "salary_min": 100000,
                "salary_max": 150000,
                "url": "https://...",
                "source": "linkedin"
            },
            ...
        ]
    """
    try:
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            print("[LINKEDIN] WARNING: RAPIDAPI_KEY not set in environment", flush=True)
            return []

        jobs = []
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }

        for role in roles:
            print(f"[LINKEDIN] Searching for '{role}' in {location or 'all locations'}", flush=True)

            # Build search query
            query = role
            if location:
                query = f"{role} {location}"

            params = {
                "query": query,
                "page": 1,
                "num_pages": 1,  # One page per request
                "date_posted": "week"  # Only jobs posted in the last week
            }

            try:
                url = "https://jsearch.p.rapidapi.com/search"
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                results = data.get("data", [])

                print(f"[LINKEDIN] Found {len(results)} jobs for '{role}'", flush=True)

                for job in results:
                    parsed_job = _parse_linkedin_job(job)
                    if parsed_job:
                        jobs.append(parsed_job)

            except requests.exceptions.RequestException as e:
                print(f"[LINKEDIN] Error fetching jobs for '{role}': {str(e)}", flush=True)
                continue
            except (ValueError, KeyError) as e:
                print(f"[LINKEDIN] Error parsing response for '{role}': {str(e)}", flush=True)
                continue

        print(f"[LINKEDIN] Total jobs found: {len(jobs)}", flush=True)
        return jobs

    except Exception as e:
        print(f"[LINKEDIN] Error in search_linkedin_jobs: {type(e).__name__}: {str(e)}", flush=True)
        return []


def _parse_linkedin_job(job_data: Dict) -> Dict or None:
    """
    Parse Jsearch job response into standardized format.

    Jsearch returns LinkedIn and other job boards in the same format.
    """
    try:
        job_id = job_data.get("job_id")
        if not job_id:
            return None

        # Extract salary range if available
        salary_min = None
        salary_max = None

        if job_data.get("job_min_salary"):
            salary_min = int(job_data.get("job_min_salary"))
        if job_data.get("job_max_salary"):
            salary_max = int(job_data.get("job_max_salary"))

        # Build standard job object
        job = {
            "id": job_id,
            "title": job_data.get("job_title", "Unknown"),
            "company": job_data.get("employer_name", "Unknown"),
            "description": job_data.get("job_description", ""),
            "location": _format_location(job_data),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "url": job_data.get("job_apply_link", ""),
            "source": "linkedin",
            "posted_date": job_data.get("job_posted_at_datetime_utc"),
            "job_type": job_data.get("job_employment_type", ""),
            "is_remote": job_data.get("job_is_remote", False)
        }

        return job

    except Exception as e:
        print(f"[LINKEDIN] Error parsing job: {str(e)}", flush=True)
        return None


def _format_location(job_data: Dict) -> str:
    """Format location from Jsearch response."""
    city = job_data.get("job_city", "")
    state = job_data.get("job_state", "")
    country = job_data.get("job_country", "")

    if job_data.get("job_is_remote"):
        return "Remote"

    parts = [p for p in [city, state, country] if p]
    return ", ".join(parts) if parts else "Location not specified"
