# Workflow: Job Discovery

## Objective

Search job boards continuously for new listings that match a user's profile and preferences. Save every result to the database for the Job Parsing Agent to process next.

---

## Trigger

- Scheduled: every 6 hours per user (via Celery beat)
- Manual: user clicks "Search Now" on the dashboard

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `user_id` | Database | The user this search belongs to |
| `target_roles` | UserProfile | e.g. ["AI Engineer", "Robotics Engineer"] |
| `preferred_modality` | UserProfile | "remote" / "hybrid" / "on-site" |
| `preferred_countries` | UserProfile | e.g. ["US", "Canada"] |
| `salary_min` | UserProfile | Minimum acceptable salary (annual, USD) |
| `tech_stack` | UserProfile | e.g. ["Python", "ROS2", "Docker"] |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/search_adzuna.py` | Search Adzuna API for job listings |
| `tools/search_themuse.py` | Search The Muse API for job listings |
| `tools/save_jobs.py` | Deduplicate and save results to PostgreSQL |

---

## Steps

### Step 1 — Load user profile
- Query the `user_profiles` table using `user_id`
- If profile not found: log error, abort, notify user to complete their profile
- If profile incomplete (missing `target_roles` or `preferred_countries`): log warning, abort

### Step 2 — Search Adzuna
- Call `tools/search_adzuna.py` with:
  - `roles`: user's `target_roles`
  - `country`: user's `preferred_countries`
  - `salary_min`: user's `salary_min`
- Expected output: list of raw job objects
- On rate limit (429): wait 60 seconds, retry once. If it fails again: log and skip Adzuna, continue to Step 3
- On auth error (401/403): log error "Adzuna API key invalid", abort and alert admin
- On empty results: log warning "No results from Adzuna", continue to Step 3

### Step 3 — Search The Muse
- Call `tools/search_themuse.py` with:
  - `roles`: user's `target_roles`
  - `location`: user's `preferred_modality`
- Expected output: list of raw job objects
- On rate limit: wait 60 seconds, retry once. If it fails again: log and skip
- On empty results: log warning "No results from The Muse", continue to Step 4

### Step 4 — Deduplicate and save
- Call `tools/save_jobs.py` with the combined results from Steps 2 and 3
- The tool checks for duplicates using the job's source URL (`job.url`)
- Only insert jobs where `url` does not already exist in the `jobs` table for this `user_id`
- Set initial status to `discovered` for all new records
- Expected output: count of new jobs saved

### Step 5 — Log result
- Write a record to `agent_logs`:
  - `user_id`
  - `agent`: "job_discovery"
  - `jobs_found`: total raw results
  - `jobs_saved`: new records inserted
  - `timestamp`
- If zero jobs saved: log reason (all duplicates, or all sources failed)

---

## Expected Output

- New rows in the `jobs` table with status `discovered`
- A record in `agent_logs` with the run summary
- Job Parsing Agent is triggered automatically for each new job

---

## Error Handling

| Situation | Action |
|---|---|
| User profile not found | Abort, log error, notify user |
| All sources return empty | Log warning, do not trigger Parsing Agent |
| All sources fail with errors | Log error, notify admin, retry in 1 hour |
| Duplicate jobs | Skip silently, count and log |
| DB write fails | Log error with job URL, retry once |

---

## Notes

- Never mix jobs between users. Always filter by `user_id`.
- LinkedIn and Indeed are NOT used in V1 due to bot detection. Add in V2 with Playwright and proper anti-detection.
- The Muse API is free with no authentication required for basic use. Adzuna requires an App ID and API Key stored in `.env`.
- Keep raw job data in `description_raw` — do not clean or parse it here. That is the Job Parsing Agent's responsibility.
