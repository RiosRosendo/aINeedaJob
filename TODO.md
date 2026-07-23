# aINeedJob - TODO

## High Priority

### Critical Fixes
- [x] Fix database query errors (execute_query vs execute_update)
- [x] Test pipeline end-to-end after database fixes
- [x] Verify auto-apply messages display correctly after fixes

### V2 Features (Job Sourcing)
- [x] Jobicy API integration (free, remote jobs)
- [x] Remotive API integration (free, remote jobs)
- [x] Jobs in all user preferred countries
- [ ] LinkedIn API integration (official, requires partner access)
- [ ] Indeed API integration
- [ ] Glassdoor API integration
- [ ] Work eligibility check (visa/work permit verification)
- [ ] Salary range parsing and storage

### V2 Features (Communication)
- [x] Weekly summary agent (LLM-generated activity reports)
- [x] Weekly summary API endpoint
- [x] Weekly summary scheduler (Monday 9am)
- [ ] Weekly summary email/push notification
- [ ] Follow-up agent (email after X days without response)
- [ ] Interview confirmation tracking
- [ ] Offer acceptance/rejection workflow

### Deployment
- [ ] Deploy to production (Railway/Render/AWS)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Database backup strategy
- [ ] Error monitoring (Sentry)
- [ ] Rate limiting configuration
- [ ] SSL/TLS certificates

---

## Medium Priority

### Data Quality
- [x] Clean up expired job listings (> 30 days old - automatic weekly cleanup)
- [x] Verify job freshness (autonomous weekly URL checks, 7-30 day window)
- [ ] Improve title filter precision (currently too permissive for generic "Engineer" titles)
- [ ] Remove duplicate jobs from same company in same week
- [ ] Standardize location parsing (extract city/state/country consistently)

### User Experience
- [ ] Dashboard: show pipeline progress (discovered → parsed → scored → applied)
- [ ] Applications page: sort by date/status/fit score
- [ ] Job details: show recruiter contact info (if available)
- [ ] Email notifications: send updates on interview invites and offers
- [ ] Profile page: show application statistics (apply rate, interview rate, offer rate)

### Agent Improvements
- [ ] Better cover letter generation (mention specific team/project if job description provides context)
- [ ] Improve email classification accuracy (handle false positives)
- [ ] Add retry logic for failed applications (after 1 week, try again with updated CV)
- [ ] Track which methods work best (form vs email vs manual)

### Testing
- [ ] Unit tests for tools (parse_job, score_job, etc.)
- [ ] Integration tests for pipeline (discovery → scoring → application)
- [ ] End-to-end tests for full workflow
- [ ] Mock Adzuna/Muse API responses for tests

---

## Low Priority

### Advanced Features
- [ ] Interview preparation agent (technical + behavioral questions, mock interview)
- [ ] Salary benchmarking agent (collect from Glassdoor, Levels.fyi, Stack Overflow)
- [ ] Career memory agent (track recurring skill gaps, recommend learning paths)
- [ ] Competitor analysis (track jobs at similar companies)
- [ ] Referral tracking (know which friend referred you to which company)

### Analytics & Reporting
- [ ] Career dashboard: 30/60/90 day goals
- [ ] Application funnel: applications → interviews → offers
- [ ] Time-to-interview metric (how long after application)
- [ ] Industry/role trends (which companies hiring most)

### Integrations
- [ ] Slack notifications for job matches and interviews
- [ ] Google Calendar integration (auto-add interviews)
- [ ] GitHub repo analysis (analyze projects for skill extraction)
- [ ] Stack Overflow profile parsing

### Localization
- [ ] Multi-language support (UI, emails, prompts)
- [ ] Regional job board APIs
- [ ] Currency conversion for salary data

---

## Backlog (Not Prioritized)

- Help user practice negotiation scripts
- Track application history with archive
- Export applications to PDF/Excel
- Integration with ATS systems (Greenhouse, Lever, etc.)
- Video interview preparation (practice with AI interviewer)
- Glassdoor review analysis by company
- LinkedIn recruiter message management
- Networking opportunity finder (mutual connections on LinkedIn)
