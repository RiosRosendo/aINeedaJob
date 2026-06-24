"""
Search Adzuna job board API for listings.

Queries the Adzuna API for jobs matching roles, country, and salary criteria.
Returns raw job listings with all available fields.

Required environment variables:
  - ADZUNA_APP_ID: Adzuna application ID
  - ADZUNA_API_KEY: Adzuna API key

Rate limiting:
  - Automatically waits 60 seconds and retries once on 429 (rate limit)
  - Raises exception if rate limited twice in a row

Authentication:
  - Raises explicit exception if API key is invalid (401/403)

Example usage:
  from tools.search_adzuna import search_adzuna

  jobs = search_adzuna(
    roles=['AI Engineer', 'Machine Learning Engineer'],
    country='US',
    salary_min=150000
  )

  print(f"Found {len(jobs)} jobs")
  for job in jobs:
    print(f"  {job['title']} at {job['company']} ({job['salary_min']}-{job['salary_max']})")
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv('ADZUNA_APP_ID')
ADZUNA_API_KEY = os.getenv('ADZUNA_API_KEY')
ADZUNA_BASE_URL = 'https://api.adzuna.com/v1/api/jobs'

if not ADZUNA_APP_ID or not ADZUNA_API_KEY:
    raise ValueError("ADZUNA_APP_ID and ADZUNA_API_KEY required in .env")


def search_adzuna(roles, country, salary_min=None):
    """
    Search Adzuna API for jobs.

    Args:
        roles (list): List of job titles to search for (e.g., ['AI Engineer'])
        country (str): Country code (e.g., 'US', 'GB', 'CA')
        salary_min (int): Minimum annual salary in USD (optional)

    Returns:
        list: List of raw job dictionaries with fields:
              title, company, location, modality, salary_min, salary_max,
              url, source, description_raw

    Raises:
        Exception: If authentication fails (401/403) or other errors occur
    """
    if not roles or not country:
        return []

    all_jobs = []

    for role in roles:
        try:
            jobs = _search_role(role, country, salary_min)
            all_jobs.extend(jobs)
        except Exception as e:
            # Log and continue to next role
            if '401' in str(e) or '403' in str(e):
                raise Exception(f"Adzuna authentication failed: {str(e)}")
            # For other errors, continue searching other roles
            continue

    return all_jobs


def _search_role(role, country, salary_min):
    """Search Adzuna for a single role."""
    params = {
        'app_id': ADZUNA_APP_ID,
        'app_key': ADZUNA_API_KEY,
        'what': role,
        'results_per_page': 50,
    }

    if salary_min:
        params['salary_min'] = salary_min

    jobs = []
    page = 1
    max_pages = 3  # Limit to avoid excessive API calls

    while page <= max_pages:
        try:
            response = _make_request(f'{ADZUNA_BASE_URL}/{country.lower()}/search/{page}', params)
            data = response.json()

            if 'results' not in data:
                break

            for result in data['results']:
                job = {
                    'title': result.get('title', ''),
                    'company': result.get('company', {}).get('display_name', ''),
                    'location': result.get('location', {}).get('display_name', ''),
                    'modality': _extract_modality(result.get('description', '')),
                    'salary_min': result.get('salary_min'),
                    'salary_max': result.get('salary_max'),
                    'url': result.get('redirect_url', ''),
                    'source': 'adzuna',
                    'description_raw': result.get('description', ''),
                }
                jobs.append(job)

            # Check if more pages available
            if data.get('results') and len(data.get('results', [])) < 50:
                break

            page += 1

        except Exception as e:
            if '429' in str(e):
                # Rate limit hit, don't retry for role — move to next
                break
            raise

    return jobs


def _make_request(url, params, retry=True):
    """Make HTTP request with retry logic for rate limits."""
    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 429:
            if retry:
                time.sleep(60)  # Wait 60 seconds
                return _make_request(url, params, retry=False)
            else:
                raise Exception("Rate limited (429) — retry exhausted")

        if response.status_code in (401, 403):
            raise Exception(f"Authentication failed ({response.status_code})")

        response.raise_for_status()
        return response

    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {str(e)}")


def _extract_modality(description):
    """Extract work modality from job description."""
    if not description:
        return 'unknown'

    desc_lower = description.lower()

    if 'remote' in desc_lower:
        return 'remote'
    elif 'hybrid' in desc_lower:
        return 'hybrid'
    elif 'on-site' in desc_lower or 'on site' in desc_lower or 'office' in desc_lower:
        return 'on-site'

    return 'unknown'
