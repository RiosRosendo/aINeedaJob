"""
Real API integration test: Adzuna + Groq + PostgreSQL

Tests the full job discovery pipeline with real APIs:
1. Search Adzuna for AI Engineer jobs
2. Save to database
3. Parse first job with Groq LLM
4. Print results at each step

Run with: python test_real_pipeline.py
"""

import json
import sys
from uuid import uuid4

# Add project root to path
sys.path.insert(0, '.')

from tools.search_adzuna import search_adzuna
from tools.save_jobs import save_jobs
from tools.parse_job import parse_job
from tools.db import execute_query, execute_update

# Constants
TEST_USER_ID = str(uuid4())
TEST_EMAIL = f'test-real-{str(uuid4())[:8]}@example.com'


def setup_test_user():
    """Create test user and profile in database."""
    print("=" * 70)
    print("STEP 0: Setting up test user")
    print("=" * 70)

    # Check if user exists
    existing = execute_query("SELECT id FROM users WHERE id = %s", (TEST_USER_ID,))

    if existing:
        print(f"[OK] User {TEST_USER_ID} already exists, skipping creation")
        return

    # Create user
    execute_update(
        "INSERT INTO users (id, email, password_hash, name, email_verified, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
        (TEST_USER_ID, TEST_EMAIL, "hash", "Test User", True, True)
    )

    # Create user profile
    execute_update(
        """INSERT INTO user_profiles
           (user_id, target_roles, preferred_modality, preferred_countries, salary_min, tech_stack)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            TEST_USER_ID,
            json.dumps(["AI Engineer", "ML Engineer"]),
            "remote",
            json.dumps(["USA", "Canada"]),
            100000,
            json.dumps(["Python", "PyTorch", "TensorFlow", "AWS"])
        )
    )
    print(f"[OK] Created user {TEST_USER_ID}")
    print()


def search_jobs():
    """Step 1: Search Adzuna for AI Engineer jobs."""
    print("=" * 70)
    print("STEP 1: Searching Adzuna API")
    print("=" * 70)
    print("Query: AI Engineer (US, salary_min=$100k)")
    print()

    try:
        # Search Adzuna
        jobs = search_adzuna(roles=['AI Engineer'], country='US', salary_min=100000)

        # Limit to 5 jobs for quick testing
        jobs = jobs[:5]

        print(f"[OK] Found {len(jobs)} jobs from Adzuna\n")

        for i, job in enumerate(jobs, 1):
            print(f"  {i}. {job['title']}")
            print(f"     Company: {job['company']}")
            print(f"     Salary: ${job.get('salary_min', 'N/A')}")
            print()

        return jobs

    except Exception as e:
        print(f"[ERROR] ERROR: {e}")
        sys.exit(1)


def save_jobs_to_db(jobs):
    """Step 2: Save jobs to database."""
    print("=" * 70)
    print("STEP 2: Saving to PostgreSQL")
    print("=" * 70)
    print(f"User ID: {TEST_USER_ID}")
    print()

    try:
        result = save_jobs(TEST_USER_ID, jobs)

        print(f"[OK] Saved {result['jobs_saved']} new jobs")
        print(f"[OK] Skipped {result['duplicates_skipped']} duplicates")
        print()

        return result

    except Exception as e:
        print(f"[ERROR] ERROR: {e}")
        sys.exit(1)


def get_first_job():
    """Get first job from database."""
    try:
        jobs = execute_query(
            "SELECT id, title, description_raw FROM jobs WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
            (TEST_USER_ID,)
        )

        if not jobs:
            print("[ERROR] ERROR: No jobs found in database")
            sys.exit(1)

        return jobs[0]

    except Exception as e:
        print(f"[ERROR] ERROR: {e}")
        sys.exit(1)


def parse_first_job(job):
    """Step 3: Parse first job with Groq LLM."""
    print("=" * 70)
    print("STEP 3: Parsing job with Groq LLM")
    print("=" * 70)
    print(f"Job ID: {job['id']}")
    print(f"Title: {job['title']}")
    print(f"Description: {job['description_raw'][:100]}...")
    print()

    try:
        # Parse job
        print("Calling Groq API...")
        parsed = parse_job(job['id'], TEST_USER_ID, job['description_raw'])

        print("[OK] Job parsed successfully\n")

        print("Parsed Fields:")
        print(f"  Title: {parsed.get('title')}")
        print(f"  Company: {parsed.get('company')}")
        print(f"  Location: {parsed.get('location')}")
        print(f"  Modality: {parsed.get('modality')}")
        print(f"  Salary: ${parsed.get('salary_min')} - ${parsed.get('salary_max')}")
        print(f"  Experience Level: {parsed.get('experience_level')}")
        print(f"  Required Skills: {parsed.get('required_skills')}")
        print()

        return parsed

    except Exception as e:
        print(f"[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Run the full pipeline."""
    print("\n")
    print("=" * 70)
    print("REAL API INTEGRATION TEST")
    print("Adzuna + Groq + PostgreSQL Pipeline")
    print("=" * 70)
    print()

    # Step 0: Setup
    setup_test_user()

    # Step 1: Search
    jobs = search_jobs()

    # Step 2: Save
    save_jobs_to_db(jobs)

    # Step 3: Parse
    job = get_first_job()
    parsed = parse_first_job(job)

    # Summary
    print("=" * 70)
    print("COMPLETE [OK]")
    print("=" * 70)
    print(f"Jobs found: {len(jobs)}")
    print(f"First job parsed: {parsed['title']}")
    print(f"Ready for job matching!")
    print()


if __name__ == '__main__':
    main()
