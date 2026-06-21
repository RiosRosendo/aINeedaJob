# CLAUDE.md — aINeedJob

This file provides guidance to Claude Code when working in this repository.

---

## What Is aINeedJob

aINeedJob is an autonomous career agent that runs 24/7 on behalf of job seekers. The user states a goal — for example, "I want a remote AI Engineer job in the US" — and the system handles discovery, analysis, CV tailoring, applications, email monitoring, follow-ups, and interview preparation automatically.

This is a multi-user SaaS product. Every piece of data, every agent action, and every workflow must be scoped to a specific user. Never mix data between users.

---

## WAT Framework

This codebase follows the WAT architecture: Workflows, Agents, Tools.

**Workflows** (`workflows/`) are Markdown SOPs. They define what needs to happen, in what order, with what inputs and outputs. Written in plain language.

**Agents** (you, Claude Code) read workflows and orchestrate execution. You handle reasoning, sequencing, and error recovery. You do not hardcode logic that belongs in a workflow.

**Tools** (`tools/`) are Python scripts that perform deterministic work: API calls, database queries, file operations, data transformations. They are consistent, testable, and fast.

**Why this matters:** Chaining five AI steps at 90% accuracy each yields 59% end-to-end accuracy. Offloading execution to deterministic scripts keeps the agent focused on orchestration, where it performs best.

---

## System Agents

### V1 — Core Pipeline (build these first)

**1. Job Discovery Agent**
- Responsibility: Continuously search job boards for new listings that match the user's profile and preferences.
- Inputs: `UserProfile` (target roles, preferred locations, modalities, salary range, tech stack)
- Outputs: Raw job listings saved to the `jobs` table with status `discovered`
- Tools: `tools/search_jobs.py`
- Sources (start with these): Adzuna API, The Muse API. Add LinkedIn and Indeed in V2.

**2. Job Parsing Agent**
- Responsibility: Extract structured data from raw job listings.
- Inputs: Raw job listing (HTML or text)
- Outputs: Structured `Job` entity with title, salary, required skills, experience level, modality, location
- Tools: `tools/parse_job.py`

**3. Job Match Agent**
- Responsibility: Compare a parsed job against a user's profile and compute a fit score with explanation.
- Inputs: `Job`, `UserProfile`
- Outputs: `FitScore` entity with numeric score (0–100), decision (Apply / Review / Ignore), list of strengths, list of gaps
- Tools: `tools/score_job.py`

**4. Decision Agent**
- Responsibility: Route each job based on its fit score.
- Rules:
  - Score ≥ 85 → auto-apply (trigger Application Agent)
  - Score 60–84 → notify user for approval, wait for response
  - Score < 60 → mark as ignored, do not surface to user
- Inputs: `FitScore`
- Outputs: Updated `Application` status

### V2 — Extended Pipeline (design now, build later)

**5. CV Tailoring Agent** — Generates a customized CV and cover letter for each job based on the `Job` description and `UserProfile`.

**6. Application Agent** — Submits applications via API integrations or browser automation (Playwright). Handles form filling, file attachments, and submission confirmation.

**7. Email Monitoring Agent** — Connects to Gmail/Outlook. Classifies incoming emails as: Interview Invite, Offer, Rejection, No Reply, or Other.

**8. Follow-up Agent** — Generates and optionally sends follow-up messages when no response is received after a defined period.

**9. Interview Agent** — When an interview is detected, researches the company and role, then generates technical questions, behavioral questions, and a mock interview session.

**10. Salary Agent** — Analyzes market salary data from Glassdoor and Levels.fyi to provide benchmarks and negotiation recommendations.

**11. Career Memory Agent** — Tracks patterns across interview outcomes and rejected applications. Recommends skill-building plans based on recurring gaps.

---

## Key Entities

These are the core data structures shared across all agents. Use these definitions consistently. Do not invent new field names without updating this section.

```python
UserProfile {
  user_id: UUID
  name: str
  email: str
  target_roles: list[str]          # e.g. ["AI Engineer", "Robotics Engineer"]
  preferred_modality: str          # "remote" | "hybrid" | "on-site"
  preferred_countries: list[str]
  salary_min: int                  # annual, USD
  tech_stack: list[str]            # e.g. ["Python", "ROS2", "Docker"]
  cv_url: str                      # path or cloud link to base CV
  github_url: str
  linkedin_url: str
}

Job {
  job_id: UUID
  user_id: UUID
  source: str                      # "adzuna" | "themuse" | "linkedin" | ...
  title: str
  company: str
  location: str
  modality: str                    # "remote" | "hybrid" | "on-site"
  salary_min: int
  salary_max: int
  required_skills: list[str]
  experience_level: str            # "junior" | "mid" | "senior"
  description_raw: str
  url: str
  discovered_at: datetime
  status: str                      # "discovered" | "parsed" | "scored" | "ignored"
}

FitScore {
  score_id: UUID
  job_id: UUID
  user_id: UUID
  score: int                       # 0–100
  decision: str                    # "apply" | "review" | "ignore"
  strengths: list[str]
  gaps: list[str]
  scored_at: datetime
}

Application {
  application_id: UUID
  job_id: UUID
  user_id: UUID
  status: str                      # "pending_approval" | "applied" | "in_review"
                                   # | "interview" | "offer" | "rejected" | "ignored"
  cv_version_url: str
  cover_letter_url: str
  applied_at: datetime
  last_updated: datetime
}
```

---

## Agent Coordination Rules

1. **Pipeline order is strict:** Discovery → Parsing → Matching → Decision → (Application or Notify User)
2. **Each agent writes its output before the next agent reads it.** Never pass data directly between agents in memory across async boundaries. Write to DB first.
3. **Human-in-the-loop for Review decisions:** When the Decision Agent routes a job to "review", it must create a notification for the user and pause. The Application Agent only fires after explicit user approval. Never auto-apply to a Review-tier job.
4. **Failures are logged, not silently swallowed.** If any tool raises an exception, log the error to the `agent_logs` table with job_id, agent name, error message, and timestamp. Then continue with the next item in the queue — do not halt the pipeline.
5. **All actions are user-scoped.** Every DB query must include `WHERE user_id = ?`. Every tool call must receive the user_id as an argument.
6. **Rate limits are respected.** If a tool hits a rate limit, log it, wait the required interval, and retry once. If it fails again, mark the job as `retry_pending` and move on.

---

## Human-in-the-Loop Protocol

When the Decision Agent scores a job between 60–84:

1. Insert a record into the `notifications` table with type `approval_required`
2. Surface it on the user's dashboard with the job summary and fit score breakdown
3. Wait for the user to respond: Approve or Dismiss
4. On Approve → trigger Application Agent
5. On Dismiss → update Application status to `ignored`
6. If no response after 48 hours → auto-dismiss and log reason

The agent never applies on behalf of a user without either a score ≥ 85 or explicit user approval.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, Tailwind |
| Backend | FastAPI |
| AI / LLM | OpenAI API, Claude API |
| Database | PostgreSQL |
| Browser Automation | Playwright (V2) |
| Agent Orchestration | LangGraph |
| Task Queue | Redis + Celery |
| Email | Gmail API, Outlook API (V2) |
| Environment | python-dotenv, `.env` file |

---

## File Structure

```
.tmp/                  # Temporary files. Regenerated as needed. Never commit.
tools/                 # Python scripts for deterministic execution
workflows/             # Markdown SOPs
.env                   # API keys and secrets (gitignored)
.env.example           # Template for required environment variables
CLAUDE.md              # This file
```

---

## Operating Rules

1. **Check `tools/` before writing new code.** If a tool already exists for the task, use it.
2. **Read the relevant workflow before executing any multi-step task.**
3. **On failure:** Read the full error, fix the tool, verify the fix, update the workflow with what you learned.
4. **Never store secrets in code.** All API keys, tokens, and credentials go in `.env` only.
5. **Always include `user_id` in every database operation.** This is a multi-user system.
6. **Deliverables go to cloud or the `outputs/` folder.** `.tmp/` is for intermediate files only.
7. **Keep workflows updated.** When you discover a rate limit, a timing quirk, or a better approach, document it in the relevant workflow file.

---

## Self-Improvement Loop

Every failure is an opportunity to make the system more robust:

1. Identify what broke
2. Fix the tool
3. Verify the fix works
4. Update the workflow with the new approach
5. Resume with a stronger system

This loop is how aINeedJob improves over time.