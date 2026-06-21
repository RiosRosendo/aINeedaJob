# Workflow: Job Match

## Objective

Compare a parsed job against a user's profile and compute a fit score from 0 to 100. Produce a clear explanation of strengths and gaps so the user understands why the system made its decision.

---

## Trigger

- Automatic: triggered by Job Parsing Agent after a job status is set to `parsed`
- Manual: admin or user can re-trigger matching on any job with status `parsed`

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `job_id` | Database | The job to evaluate |
| `user_id` | Database | The user to match against |
| `required_skills` | jobs table | Skills the job requires |
| `nice_to_have_skills` | jobs table | Skills the job prefers but does not require |
| `experience_level` | jobs table | junior / mid / senior / unknown |
| `modality` | jobs table | remote / hybrid / on-site |
| `location` | jobs table | Job location |
| `salary_min` | jobs table | Minimum salary offered |
| `tech_stack` | UserProfile | User's skills |
| `target_roles` | UserProfile | User's target job titles |
| `preferred_modality` | UserProfile | User's preferred work modality |
| `preferred_countries` | UserProfile | User's preferred locations |
| `salary_min` | UserProfile | User's minimum acceptable salary |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/score_job.py` | Send job + profile to LLM and compute fit score |
| `tools/save_fit_score.py` | Save FitScore entity to the database |

---

## Steps

### Step 1 — Load job and user profile
- Query `jobs` table for `job_id` and `user_id`
- Query `user_profiles` table for `user_id`
- If either is not found: log error, abort
- If job status is not `parsed`: log warning, abort

### Step 2 — Run hard filters
Before calling the LLM, apply fast rule-based checks:

| Filter | Condition | Action |
|---|---|---|
| Modality mismatch | User wants remote, job is on-site | Score = 0, decision = ignore |
| Salary below minimum | Job salary_max < user salary_min | Score = 0, decision = ignore |
| Country mismatch | Job location not in user preferred_countries | Score = 0, decision = ignore |

- If any hard filter fails: skip LLM call, save FitScore with score = 0, decision = `ignore`, reason = filter name
- This saves LLM cost on obviously incompatible jobs

### Step 3 — Compute skill overlap
- Calculate matched skills: intersection of `required_skills` and user `tech_stack`
- Calculate missing skills: `required_skills` minus user `tech_stack`
- Calculate bonus skills: intersection of `nice_to_have_skills` and user `tech_stack`
- Pass these lists to the LLM in Step 4

### Step 4 — Compute fit score via LLM
- Call `tools/score_job.py` with job data, user profile, and skill overlap from Step 3
- The tool sends this prompt to the LLM:

```
You are a career advisor evaluating job fit.
Return only a JSON object with no extra text.

User profile:
- Skills: {user_tech_stack}
- Target roles: {user_target_roles}
- Preferred modality: {user_preferred_modality}
- Preferred countries: {user_preferred_countries}
- Minimum salary: {user_salary_min}

Job details:
- Title: {job_title}
- Company: {job_company}
- Required skills: {job_required_skills}
- Nice to have: {job_nice_to_have_skills}
- Experience level: {job_experience_level}
- Modality: {job_modality}
- Location: {job_location}
- Salary range: {job_salary_min} - {job_salary_max}

Skill analysis:
- Matched skills: {matched_skills}
- Missing skills: {missing_skills}
- Bonus skills: {bonus_skills}

Compute a fit score from 0 to 100 based on:
- Skill match (50% weight)
- Role alignment (20% weight)
- Modality match (15% weight)
- Salary match (15% weight)

Return:
{
  "score": integer (0-100),
  "decision": "apply" | "review" | "ignore",
  "strengths": [list of strings, max 3],
  "gaps": [list of strings, max 3],
  "summary": "one sentence explanation"
}

Decision rules:
- score >= 85 → "apply"
- score 60-84 → "review"
- score < 60 → "ignore"
```

- Expected output: valid JSON with score, decision, strengths, gaps, summary
- If LLM returns invalid JSON: retry once
- If second attempt fails: log error, mark job as `match_failed`, abort

### Step 5 — Validate output
- `score` must be integer between 0 and 100
- `decision` must be one of: "apply", "review", "ignore"
- `strengths` and `gaps` must be lists
- If validation fails: log error, mark job as `match_failed`, abort

### Step 6 — Save FitScore
- Call `tools/save_fit_score.py` with the validated output
- Insert a new record into the `fit_scores` table
- Update job status to `scored`

### Step 7 — Log result
- Write a record to `agent_logs`:
  - `user_id`
  - `job_id`
  - `agent`: "job_match"
  - `score`: the computed score
  - `decision`: apply / review / ignore
  - `timestamp`

---

## Expected Output

- New record in `fit_scores` table with score, decision, strengths, gaps, summary
- Job status updated to `scored`
- Decision Agent is triggered automatically

---

## Error Handling

| Situation | Action |
|---|---|
| Job or profile not found | Abort, log error |
| Hard filter fails | Save score = 0, decision = ignore, skip LLM |
| LLM returns invalid JSON twice | Mark as `match_failed`, log, skip |
| Score out of range | Clamp to 0-100 and log warning |
| DB write fails | Retry once, then log error |

---

## Notes

- Hard filters run before the LLM to save cost. A modality mismatch should never reach the LLM.
- The 50/20/15/15 weight distribution is a starting point. Adjust based on user feedback after launch.
- Never show raw scores to users without context. Always surface strengths and gaps alongside the number.
- The `summary` field is what appears on the dashboard card — keep it one sentence, actionable, and honest.
