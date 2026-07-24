# aINeedJob Architecture

Multi-user SaaS autonomous job search agent. Runs 24/7 on behalf of job seekers to discover, analyze, apply to, and follow up on job opportunities.

---

## Folder Structure

```
aINeedJob/
├── agents/           LangGraph pipeline orchestrators (Discovery → Process → Summary)
├── api/              FastAPI backend server
│   ├── routes/       Individual endpoint files
│   ├── models/       Pydantic schemas
│   └── dependencies.py
├── tools/            Reusable deterministic functions (API calls, DB ops, parsing, scoring)
├── scripts/          One-time maintenance utilities (backfill, verification, etc.)
├── frontend/         Next.js dashboard UI (React + Tailwind)
├── workflows/        Markdown SOP documentation for agents
├── database/         PostgreSQL schema and migrations
├── .env              API keys (gitignored)
├── .env.example      Template for required env vars
├── CLAUDE.md         Instructions for Claude Code
├── ARCHITECTURE.md   This file
├── PROGRESS.md       Feature completion tracking
└── TODO.md           Backlog and known issues
```

---

## Active Files

### agents/

| File | Purpose |
|------|---------|
| `pipeline.py` | Main LangGraph workflow: discovery_node → processing_node → summary_node. Searches all preferred countries, parses jobs, scores against profile, routes to applications |

### tools/

| File | Purpose |
|------|---------|
| `db.py` | PostgreSQL connection pool, execute_query(), execute_update() |
| `search_adzuna.py` | Adzuna API job search (English + local language roles) |
| `search_themuse.py` | The Muse API job search (global) |
| `search_jobicy.py` | Jobicy API (remote jobs, free tier) |
| `search_remotive.py` | Remotive API (remote jobs, free tier) |
| `search_occ.py` | OCC México scraper (Mexico job board) |
| `save_jobs.py` | Deduplicate and insert discovered jobs with search_country tagging |
| `parse_job.py` | Extract structured fields (title, salary, skills, etc.) using Groq LLM |
| `score_job.py` | Calculate fit_score (0-100) vs user profile using Groq LLM |
| `update_job.py` | Update job record with parsed data |
| `save_fit_score.py` | Insert/update fit_scores table with decision (apply/review/ignore) |
| `apply_job.py` | Submit applications via Workable/Ashby APIs |
| `tailor_cv.py` | Generate job-specific CV using Claude API |
| `check_eligibility.py` | Verify work authorization (visa requirements, remote eligibility) |
| `check_job_active.py` | Verify job is still posted (not expired) |
| `verify_active_jobs.py` | Batch check job status |
| `weekly_summary.py` | Generate weekly stats and LLM summary for dashboard |
| `create_notification.py` | Insert notification for user-in-the-loop events |
| `trigger_agent.py` | Async task runner |
| `logger.py` | Log agent runs to agent_logs table |
| `llm.py` | Groq API wrapper (llama-3.1-8b-instant, temp=0.1) |

### api/routes/

| File | Purpose |
|------|---------|
| `jobs.py` | GET /api/jobs (list with pagination), GET /api/jobs/logs (agent queue), GET /api/jobs/by-country (world map), POST /api/jobs/search (trigger discovery), POST /api/jobs/process (process unscored jobs) |
| `applications.py` | GET /api/applications (pending approvals), PATCH /api/applications/{id}/approve, PATCH /api/applications/{id}/dismiss |
| `summary.py` | GET /api/summary/weekly (fetch or generate weekly summary), POST /api/summary/weekly/regenerate |
| `debug.py` | GET /api/debug/jobs-by-country (show jobs by search_country for map diagnostics) |
| `auth.py` | POST /api/auth/login, POST /api/auth/register (user authentication) |
| `users.py` | GET /api/users/profile, PATCH /api/users/profile (user preferences) |
| `cv.py` | GET /api/cv/base, POST /api/cv/upload (CV management) |
| `gmail.py` | GET /api/gmail/auth, POST /api/gmail/sync (email monitoring via Gmail API) |

### api/

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app initialization, CORS setup, scheduler startup, router registration |
| `dependencies.py` | get_user_id() dependency (extract from x-user-id header) |
| `models/schemas.py` | Pydantic request/response models |

### scripts/

| File | Purpose |
|------|---------|
| `backfill_search_country.py` | Backfill search_country field for legacy jobs based on location extraction |
| `discover_mexico_jobs.py` | Trigger fresh Mexico job discovery search |
| `mark_apps_ignored.py` | Mark irrelevant applications (e.g., non-robotics jobs) as ignored |
| `verify_mexico_map.py` | Verify Mexico jobs appear on world map |
| `batch_process.py` | Process a batch of unscored jobs |

---

## Schedulers Running (APScheduler)

| Job | Schedule | What It Does |
|-----|----------|------------|
| Daily Job Search | 8:00 AM UTC | Run discovery_node for all users (find new jobs) |
| Email Monitoring | Every 6 hours (0, 6, 12, 18 UTC) | Check Gmail for interview invites, offers, rejections |
| Weekly Summary | Monday 9:00 AM UTC | Generate summary of past week's activity |
| Job Expiry Cleanup | Sunday 12:00 AM UTC | Mark expired jobs as inactive (expires_at IS NOT NULL) |
| Autonomous Job Verification | Tuesday 2:00 AM UTC | Verify all jobs still posted (not removed by employer) |
| Follow-up Agent | Monday 10:00 AM UTC | Send follow-ups to employers after 7+ days no response |
| Interview Prep | Tuesday 3:00 AM UTC | Research company & generate interview questions when interview detected |

---

## Key Data Flow

### Discovery Pipeline (agents/pipeline.py)

```
┌─────────────────┐
│ discovery_node  │ Search all preferred countries (Adzuna, Muse, Jobicy, Remotive, OCC)
└────────┬────────┘
         ↓ Tag jobs with search_country during discovery
┌─────────────────┐
│  save_jobs      │ Deduplicate by (url, user_id), insert to jobs table
└────────┬────────┘
         ↓ Unprocessed jobs = discovered/parsed without fit_scores
┌─────────────────┐
│processing_node  │ Parse job descriptions (extract title, salary, skills)
└────────┬────────┘
         ↓
┌─────────────────┐
│ score_job       │ Compare vs user profile, generate fit_score (0-100)
└────────┬────────┘
         ↓
┌─────────────────┐
│   DECISION:     │ ≥85: auto-apply | 60-84: user review | <60: ignore
└────────┬────────┘
         ↓
┌─────────────────┐
│ applications    │ Create app record, trigger CV tailoring
└────────┬────────┘
         ↓
┌─────────────────┐
│  summary_node   │ Generate weekly stats and dashboard summary
└─────────────────┘
```

### User-in-the-Loop: Approval Flow

```
Jobs scored 60-84 need user approval before applying:

┌──────────────────────┐
│ pending_approval     │ Appears on Approvals page
│ (Dashboard Queue)    │
└──────────┬───────────┘
           ↓ User clicks "Approve"
┌──────────────────────┐
│ pending_application  │ CV tailoring triggered
└──────────┬───────────┘
           ↓ CV ready
┌──────────────────────┐
│ applied              │ Application submitted
└──────────────────────┘
```

### World Map Country Detection

```
┌─────────────────────────────────────────────────┐
│ GET /api/jobs/by-country                        │
└────────────────────┬────────────────────────────┘
                     ↓
        COALESCE(search_country,
           CASE location ILIKE '%Mexico%' THEN 'mx'
               location ILIKE '%USA%' THEN 'us'
               ...
           END)
                     ↓
        SELECT country_code, COUNT(*) GROUP BY country_code
                     ↓
        Map country codes to COUNTRY_COORDS (lat/lng)
                     ↓
        Return to frontend for React map visualization
```

---

## Multi-User Scoping

**Every database operation includes `user_id` in WHERE clause:**

```python
# Jobs for user A don't appear in user B's dashboard
SELECT * FROM jobs WHERE user_id = 'user-a-uuid' AND expires_at IS NULL

# Applications for user A are isolated
SELECT * FROM applications WHERE user_id = 'user-a-uuid'

# No cross-user data leakage
```

---

## Known Issues & Inconsistencies

### Fixed Today ✅

1. **Jobs Queue Filtering** - Now filters to show only fit_score ≥ 60
2. **Jobs Found Count** - Single source of truth: `SELECT COUNT(*) FROM jobs WHERE user_id=X AND expires_at IS NULL`
3. **Approvals Page** - Removed deduplication, now shows all 11 pending approvals
4. **Applications Endpoint** - Fixed to return all distinct applications (not deduplicated by hash)
5. **Mexico on Map** - Backfill added search_country for legacy jobs, Mexico now visible with 2 jobs

### Remaining Issues

1. **NULL search_country (3,630 jobs = 56%)** - Global jobs from Muse/Jobicy/Remotive lack country info. Impact: may not group on map. Fix: requires location extraction LLM or manual categorization.

2. **Discovery Pipeline Tagging** - Need to verify all newly discovered jobs are tagged with search_country during save_jobs(). Currently only 1-2 Mexico jobs per discovery even though search finds 36.

3. **OCC México Scraper** - Getting HTTP 404 errors when searching for translated job titles. Impact: Mexico job count should be higher.

---

## Testing & Verification

### Debug Endpoints

```bash
# Check jobs by country (for world map)
curl http://localhost:8001/api/debug/jobs-by-country \
  -H "x-user-id: 14ab2d63-1eef-43d9-b3f4-748566bad8da"

# Shows:
# - Total active jobs
# - Jobs grouped by search_country (from discovery tagging)
# - Mexico sample jobs
```

### Maintenance Scripts

```bash
# Backfill search_country for legacy jobs
python scripts/backfill_search_country.py

# Trigger Mexico discovery
python scripts/discover_mexico_jobs.py

# Verify Mexico on map
python scripts/verify_mexico_map.py

# Mark irrelevant applications (non-robotics) as ignored
python scripts/mark_apps_ignored.py
```

---

## Deployment & Startup

```bash
# Start backend (port 8001)
uvicorn api.main:app --port 8001 --reload

# Start frontend (port 3000)
cd frontend && npm run dev

# Scheduler auto-starts with backend
# All 7 background jobs initialize on app startup
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, Tailwind CSS 3, Recharts (maps) |
| Backend | FastAPI, Uvicorn, APScheduler, Pydantic |
| AI/LLM | Groq API (llama-3.1-8b-instant), Claude API (CV tailoring) |
| Database | PostgreSQL 15, psycopg2, RealDictRow |
| Job Board APIs | Adzuna, The Muse, Jobicy, Remotive, OCC México |
| Auth | Gmail OAuth 2.0, Workable/Ashby API tokens |
| Orchestration | LangGraph (workflow DAG) |
| Async | APScheduler (background jobs), Celery-ready (not yet implemented) |

---

## Git Workflow

1. All changes committed with Rosendo de los Rios credentials
2. Commits follow pattern: `type: description` (fix:, feat:, chore:, docs:)
3. Push to `origin master` after each logical change
4. Keep PROGRESS.md and TODO.md in sync with actual state

---

**Last Updated**: 2026-07-23  
**Status**: System ready for Rosendo to restart server and test  
**Critical Path**: Dashboard + Mexican jobs on map ✅ (Complete)
