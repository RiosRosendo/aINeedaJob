# aINeedJob - Progress Log

## Completed

### Core Infrastructure
- [x] PostgreSQL database schema with multi-user scoping
- [x] FastAPI backend with JWT authentication (login/register)
- [x] Next.js frontend with responsive design
- [x] Environment configuration (`.env` file management)

### Discovery & Scoring
- [x] Job discovery from Adzuna API (9+ countries)
- [x] Job discovery from Jobicy API (free, remote jobs)
- [x] Job discovery from Remotive API (free, remote jobs)
- [x] Job discovery from The Muse API
- [x] Job parsing with LLM-based title validation (language-agnostic)
- [x] Semantic job scoring with Groq LLM
- [x] Fit score calculation (0-100)
- [x] Decision routing (Apply / Review / Ignore)

### User Approvals & Decisions
- [x] Human-in-the-loop approval system
- [x] Notifications for review-tier jobs (60-84 score)
- [x] Approvals page with job details and fit score
- [x] Approve/Dismiss/Auto-Apply buttons on approvals page

### Application Processing
- [x] CV upload and extraction to database
- [x] CV data storage in PostgreSQL (JSON)
- [x] CV tailoring for each job (LLM-generated)
- [x] Cover letter generation (LLM-based, when needed)
- [x] Auto-Apply agent with Playwright browser automation
- [x] Multilingual support (Spanish, German, French, Japanese, Chinese)
- [x] LLM-based navigation (full autonomy, no hardcoded button names)
- [x] Up to 3 page redirects to reach application page
- [x] Form filling with email/name auto-fill
- [x] Manual vs. automated decision tracking
- [x] Work eligibility verification (visa/work permit checks)

### Email & Communication
- [x] Gmail OAuth2 integration
- [x] Email token storage and refresh
- [x] Email monitoring agent (6-hour checks)
- [x] Email classification (Interview/Offer/Rejected/Follow-up)
- [x] Application status updates from emails

### Scheduling & Automation
- [x] APScheduler integration
- [x] Daily job discovery (configurable time)
- [x] 6-hour email monitoring cycle
- [x] Weekly summary generation (every Monday 9am)
- [x] Job expiry cleanup (every Sunday midnight)
- [x] Autonomous job verification (every Tuesday 2am)
- [x] Async task execution

### Dashboard & Analytics
- [x] World map showing jobs by country
- [x] Statistics dashboard (jobs found, applied, interviews, offers)
- [x] Applications list with status filtering
- [x] Job details with fit score breakdown
- [x] Weekly summary agent (natural language activity summaries)
- [x] Weekly summary endpoint (GET /api/summary/weekly)
- [x] Weekly summary display on dashboard
- [x] On-demand summary generation ("Generate now" button)
- [x] Job expiry system (exclude expired jobs from dashboard stats)
- [x] Dashboard stats exclude jobs older than 30 days
- [x] Job freshness verification (autonomous weekly URL checks)
- [x] Dashboard shows only recently verified active jobs
- [x] Eligibility badge on approvals page (visa/work permit status)
- [x] Work eligibility details with LLM-generated explanation

### Developer Experience
- [x] Comprehensive logging throughout pipeline
- [x] Error tracking with agent_logs table
- [x] Debug endpoints for manual triggers
- [x] CLAUDE.md documentation

---

## Known Bugs Fixed

### Database & Queries
- [x] **Database column naming**: Fixed `last_updated` → `updated_at` (columns table uses `updated_at`)
- [x] **Foreign key column naming**: Fixed `application_id` → `id` (applications table uses `id` as PK)
- [x] **agent_logs schema**: Corrected `agent_name` → `agent`, added `details` JSON field
- [x] **Pipeline status update bug**: Applications stuck in `pending_application` - added UPDATE queries for review/ignore decisions
- [x] **execute_query() vs execute_update()**: Fixed INSERT/UPDATE to use `execute_update()` which doesn't expect results

### API & Response Handling
- [x] **Groq API format**: Changed `client.messages.create()` → `client.chat.completions.create()`
- [x] **JSON response parsing**: Added `_extract_json()` to handle markdown code blocks and raw JSON
- [x] **Response structure**: API returns unwrapped `response.data` from autoApplyForJob()

### Browser Automation
- [x] **asyncio.run() event loop conflict**: Use ThreadPoolExecutor to run Playwright in separate thread
- [x] **Button clicking reliability**: Replaced CSS selectors with Playwright's `get_by_role()`, `get_by_text()` locators
- [x] **Timeout handling**: Added 2-minute timeout for Playwright execution

### Frontend
- [x] **Relative URL issue**: Changed API calls from `/api/...` → `http://localhost:8001/api/...`
- [x] **Missing x-user-id header**: Added to all API calls
- [x] **Cached message display**: Fixed to show fresh LLM-generated messages
- [x] **Response structure extraction**: Corrected `response.data.result` path (API already unwraps)

### LLM & Natural Language
- [x] **Job title validation**: Implemented with LLM instead of hardcoded keywords (handles any language)
- [x] **Button clicking autonomy**: LLM decides which button to click (no hardcoded list)
- [x] **Cover letter generation**: LLM generates contextual letters when job requires them
- [x] **User-friendly error messages**: LLM generates "what_i_tried" and "why_i_need_help" messages instead of technical errors

### Git & Deployment
- [x] **Git ignore**: Added `.env` and credentials to `.gitignore`
- [x] **Route ordering**: Fixed `/by-country` route before `/:job_id` to prevent false matches

---

## Next Steps (See TODO.md)

High priority items for V2:
- LinkedIn API integration
- Jobs in all user preferred countries
- Work eligibility verification
- Weekly summary agent
- Production deployment

Current impediments:
- None currently blocking
- System is functional for MVP
