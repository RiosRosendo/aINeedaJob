"""
Remotive remote jobs search - free API, no authentication required.

Remotive aggregates remote job listings with a focus on tech roles.
"""

import requests
from typing import List, Dict


def search_remotive_jobs(roles: List[str], limit: int = 50) -> List[Dict]:
    """
    Search for remote jobs on Remotive API.

    Args:
        roles: List of job titles/keywords to search for (e.g., ["AI Engineer", "Python"])
        limit: Number of results per search (default 50)

    Returns:
        List of job listings in standardized format:
        [
            {
                "id": "unique_id",
                "title": "Job Title",
                "company": "Company Name",
                "description": "Job description",
                "location": "Remote",
                "salary_min": None,
                "salary_max": None,
                "url": "https://...",
                "source": "remotive"
            },
            ...
        ]
    """
    try:
        jobs = []
        base_url = "https://remotive.com/api/remote-jobs"

        for role in roles:
            print(f"[REMOTIVE] Searching for '{role}' jobs", flush=True)

            try:
                params = {
                    "search": role,
                    "limit": min(limit, 100)  # Remotive supports up to 100
                }

                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                results = data.get("jobs", [])

                print(f"[REMOTIVE] Found {len(results)} jobs for '{role}'", flush=True)

                for job in results:
                    parsed_job = _parse_remotive_job(job)
                    if parsed_job:
                        jobs.append(parsed_job)

            except requests.exceptions.RequestException as e:
                print(f"[REMOTIVE] Error fetching jobs for '{role}': {str(e)}", flush=True)
                continue
            except (ValueError, KeyError) as e:
                print(f"[REMOTIVE] Error parsing response for '{role}': {str(e)}", flush=True)
                continue

        print(f"[REMOTIVE] Total jobs found: {len(jobs)}", flush=True)
        return jobs

    except Exception as e:
        print(f"[REMOTIVE] Error in search_remotive_jobs: {type(e).__name__}: {str(e)}", flush=True)
        return []


def _parse_remotive_job(job_data: Dict) -> Dict or None:
    """
    Parse Remotive job response into standardized format.

    Remotive doesn't provide salary data, so salary fields are None.
    """
    try:
        job_id = job_data.get("id")
        if not job_id:
            return None

        # Remotive doesn't provide salary data
        job = {
            "id": str(job_id),
            "title": job_data.get("title", "Unknown"),
            "company": job_data.get("company_name", "Unknown"),
            "description": job_data.get("description", ""),
            "location": "Remote",  # Remotive only has remote jobs
            "salary_min": None,
            "salary_max": None,
            "url": job_data.get("url", ""),
            "source": "remotive",
            "posted_date": job_data.get("published_at"),
            "job_type": "Remote",
            "category": job_data.get("category")
        }

        return job

    except Exception as e:
        print(f"[REMOTIVE] Error parsing job: {str(e)}", flush=True)
        return None
