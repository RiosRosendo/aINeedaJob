# Workflow: Job Parsing

## Objective

Take a raw job listing from the database and extract structured data from it. Transform unstructured text into a clean `Job` entity that the Job Match Agent can compare against a user's profile.

---

## Trigger

- Automatic: triggered by Job Discovery Agent after each new job is saved with status `discovered`
- Manual: admin can re-trigger parsing on any job with status `discovered` or `parse_failed`

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `job_id` | Database | The job to parse |
| `user_id` | Database | The user this job belongs to |
| `description_raw` | jobs table | Raw HTML or text from the job board |
| `title` | jobs table | Raw job title as scraped |
| `url` | jobs table | Original job posting URL |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/parse_job.py` | Send raw description to LLM and extract structured fields |
| `tools/update_job.py` | Write parsed fields back to the jobs table |

---

## Steps

### Step 1 — Load raw job
- Query the `jobs` table for the given `job_id` and `user_id`
- If not found: log error, abort
- If status is not `discovered`: log warning "Job already processed", abort

### Step 2 — Clean raw text
- Strip HTML tags from `description_raw`
- Remove excessive whitespace and special characters
- Truncate to 4000 characters maximum to stay within LLM context limits

### Step 3 — Extract structured fields via LLM
- Call `tools/parse_job.py` with the cleaned text
- The tool sends the text to the LLM with this extraction prompt:

```
Extract the following fields from this job description.
Return only a JSON object with no extra text.

Fields:
- title (string)
- company (string)
- location (string)
- modality (string: "remote", "hybrid", or "on-site")
- salary_min (integer, annual USD, null if not mentioned)
- salary_max (integer, annual USD, null if not mentioned)
- required_skills (list of strings)
- nice_to_have_skills (list of strings)
- experience_level (string: "junior", "mid", "senior", or "unknown")
- experience_years_min (integer, null if not mentioned)
- responsibilities (list of strings, max 5)

Job description:
{cleaned_text}
```

- Expected output: valid JSON object with the fields above
- If LLM returns invalid JSON: retry once with a stricter prompt
- If second attempt fails: mark job as `parse_failed`, log error, abort

### Step 4 — Validate extracted fields
- `title` must not be null or empty
- `required_skills` must be a list (can be empty but not null)
- `modality` must be one of: "remote", "hybrid", "on-site" — if not, default to "unknown"
- `experience_level` must be one of: "junior", "mid", "senior", "unknown" — if not, default to "unknown"
- If validation fails on critical fields (title): mark as `parse_failed`, log reason, abort

### Step 5 — Save structured fields
- Call `tools/update_job.py` with the validated fields
- Update the job record in the `jobs` table
- Set status to `parsed`

### Step 6 — Log result
- Write a record to `agent_logs`:
  - `user_id`
  - `job_id`
  - `agent`: "job_parsing"
  - `status`: "success" or "failed"
  - `timestamp`

---

## Expected Output

- Updated job record in the `jobs` table with all structured fields populated
- Job status set to `parsed`
- Job Match Agent is triggered automatically

---

## Error Handling

| Situation | Action |
|---|---|
| Raw description is empty | Mark as `parse_failed`, log, skip |
| LLM returns invalid JSON twice | Mark as `parse_failed`, log, skip |
| Critical fields missing after parsing | Mark as `parse_failed`, log reason |
| DB update fails | Log error, retry once |
| Job already parsed | Skip silently |

---

## Notes

- Never modify `description_raw` — keep the original text intact in the database at all times.
- Salary extraction is best-effort. Many job postings do not include salary — always allow null.
- The LLM prompt must always request JSON only. Never allow free-text responses from the LLM in this step.
- Token cost per job is low (one short LLM call). Do not batch multiple jobs in one call — parse one at a time for reliability.
