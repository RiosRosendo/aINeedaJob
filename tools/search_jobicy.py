"""
Jobicy remote jobs search - free API, no authentication required.

Jobicy provides aggregated remote job listings from multiple sources.
"""

import requests
from typing import List, Dict


def search_jobicy_jobs(roles: List[str], count: int = 50) -> List[Dict]:
    """
    Search for remote jobs on Jobicy API.

    Args:
        roles: List of job titles/tags to search for (e.g., ["AI Engineer", "Python"])
        count: Number of results per search (default 50, max 50)

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
                "source": "jobicy"
            },
            ...
        ]
    """
    try:
        jobs = []
        base_url = "https://jobicy.com/api/v2/remote-jobs"

        for role in roles:
            print(f"[JOBICY] Searching for '{role}' jobs", flush=True)

            try:
                params = {
                    "count": min(count, 50),  # Jobicy max is 50
                    "tag": role
                }

                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                results = data.get("jobs", [])

                print(f"[JOBICY] Found {len(results)} jobs for '{role}'", flush=True)

                for job in results:
                    parsed_job = _parse_jobicy_job(job)
                    if parsed_job:
                        jobs.append(parsed_job)

            except requests.exceptions.RequestException as e:
                print(f"[JOBICY] Error fetching jobs for '{role}': {str(e)}", flush=True)
                continue
            except (ValueError, KeyError) as e:
                print(f"[JOBICY] Error parsing response for '{role}': {str(e)}", flush=True)
                continue

        print(f"[JOBICY] Total jobs found: {len(jobs)}", flush=True)
        return jobs

    except Exception as e:
        print(f"[JOBICY] Error in search_jobicy_jobs: {type(e).__name__}: {str(e)}", flush=True)
        return []


def _parse_jobicy_job(job_data: Dict) -> Dict or None:
    """
    Parse Jobicy job response into standardized format.

    Jobicy doesn't provide salary data, so salary fields are None.
    """
    try:
        job_id = job_data.get("id")
        if not job_id:
            return None

        # Jobicy doesn't provide salary data
        job = {
            "id": str(job_id),
            "title": job_data.get("title", "Unknown"),
            "company": job_data.get("company", "Unknown"),
            "description": job_data.get("description", ""),
            "location": "Remote",  # Jobicy only has remote jobs
            "salary_min": None,
            "salary_max": None,
            "url": job_data.get("url", ""),
            "source": "jobicy",
            "posted_date": job_data.get("posted_at"),
            "job_type": "Remote"
        }

        return job

    except Exception as e:
        print(f"[JOBICY] Error parsing job: {str(e)}", flush=True)
        return None
