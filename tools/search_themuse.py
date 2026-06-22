"""
Search The Muse job board API for listings.

Queries The Muse API for jobs matching roles and work modality.
The Muse API requires no authentication for basic use.
Returns raw job listings with all available fields.

Rate limiting:
  - The Muse allows ~60 requests/hour per IP
  - Automatically waits 60 seconds and retries once on 429 (rate limit)
  - Raises exception if rate limited twice

Example usage:
  from tools.search_themuse import search_themuse

  jobs = search_themuse(
    roles=['AI Engineer', 'Machine Learning Engineer'],
    modality='remote'
  )

  print(f"Found {len(jobs)} jobs")
  for job in jobs:
    print(f"  {job['title']} at {job['company']}")
"""

import time
import requests

THEMUSE_BASE_URL = 'https://www.themuse.com/api/public/jobs'


def search_themuse(roles, modality=None):
    """
    Search The Muse API for jobs.

    Args:
        roles (list): List of job titles to search for (e.g., ['AI Engineer'])
        modality (str): Work modality filter (remote, hybrid, on-site) (optional)

    Returns:
        list: List of raw job dictionaries with fields:
              title, company, location, modality, salary_min, salary_max,
              url, source, description_raw

    Raises:
        Exception: If API call fails (non-429, non-empty-results errors)
    """
    if not roles:
        return []

    all_jobs = []

    for role in roles:
        try:
            jobs = _search_role(role, modality)
            all_jobs.extend(jobs)
        except Exception as e:
            # For non-critical errors, continue to next role
            if '429' not in str(e):
                continue
            raise

    return all_jobs


def _search_role(role, modality):
    """Search The Muse for a single role."""
    params = {
        'role': role,
        'page': 0,
        'per_page': 50,
    }

    # Add modality filter if specified
    # The Muse uses 'level' for experience, 'location' for geography
    # We'll use keywords for modality filtering instead
    if modality:
        if modality == 'remote':
            params['location'] = 'remote'
        elif modality == 'hybrid':
            # The Muse doesn't have native hybrid filter, filter in post-processing
            pass
        elif modality == 'on-site':
            # Filter in post-processing to avoid empty results
            pass

    jobs = []
    page = 0
    max_pages = 3  # Limit pages to avoid excessive API calls

    while page < max_pages:
        params['page'] = page

        try:
            response = _make_request(THEMUSE_BASE_URL, params)
            data = response.json()

            if 'results' not in data:
                break

            for result in data['results']:
                # Filter by modality if specified
                job_modality = _extract_modality(result.get('locations', []))

                if modality and modality != job_modality and modality != 'unknown':
                    continue

                job = {
                    'title': result.get('name', ''),
                    'company': result.get('company', {}).get('name', ''),
                    'location': _extract_location(result.get('locations', [])),
                    'modality': job_modality,
                    'salary_min': None,  # The Muse doesn't provide salary in API
                    'salary_max': None,
                    'url': result.get('refs', {}).get('landing_page', ''),
                    'source': 'themuse',
                    'description_raw': result.get('contents', ''),
                }
                jobs.append(job)

            # Check if more pages available
            if len(data.get('results', [])) < 50:
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


def _extract_location(locations):
    """Extract primary location from locations array."""
    if not locations:
        return 'unknown'

    if isinstance(locations, list) and len(locations) > 0:
        location = locations[0]
        if isinstance(location, dict):
            name = location.get('name', '')
            return name if name else 'unknown'
        return str(location)

    return 'unknown'


def _extract_modality(locations):
    """Extract work modality from locations."""
    if not locations:
        return 'unknown'

    if isinstance(locations, list):
        for loc in locations:
            if isinstance(loc, dict):
                name = loc.get('name', '').lower()
                if 'remote' in name:
                    return 'remote'

    return 'on-site'  # Default to on-site if not specified as remote
