# Workflow: Salary

## Objective

When a job offer is received, analyze market salary data to give the user a clear picture of whether the offer is competitive, what they should counter with, and how to negotiate effectively.

---

## Trigger

- Automatic: triggered by Email Monitoring Agent when Application status changes to `offer`
- Manual: user can request salary analysis for any job from the dashboard

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `application_id` | Database | The application with offer |
| `job_id` | Database | The target job |
| `user_id` | Database | The user negotiating |
| `title` | jobs table | Job title |
| `company` | jobs table | Company name |
| `location` | jobs table | Job location |
| `modality` | jobs table | remote / hybrid / on-site |
| `salary_min` | jobs table | Offered salary min (if known) |
| `salary_max` | jobs table | Offered salary max (if known) |
| `required_skills` | jobs table | Skills the role requires |
| `experience_level` | jobs table | junior / mid / senior |
| `tech_stack` | UserProfile | User's skills |
| `salary_min` | UserProfile | User's minimum acceptable salary |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/fetch_salary_data.py` | Fetch market salary data from public sources |
| `tools/analyze_offer.py` | Analyze offer vs market via LLM |
| `tools/generate_negotiation_script.py` | Generate negotiation talking points via LLM |
| `tools/save_salary_report.py` | Save analysis to database |
| `tools/create_notification.py` | Notify user that report is ready |

---

## Steps

### Step 1 — Load all inputs
- Query `applications`, `jobs`, and `user_profiles` tables
- If any required input missing: log error, notify user, abort

### Step 2 — Fetch market salary data
- Call `tools/fetch_salary_data.py` with job title, location, experience level
- Sources to query:
  - Levels.fyi (for tech roles)
  - Glassdoor salary data (public)
  - LinkedIn salary insights (public)
  - Bureau of Labor Statistics (for US roles)
- Extract:
  - P25 salary (entry point)
  - P50 salary (market median)
  - P75 salary (competitive)
  - P90 salary (top of market)
  - Remote vs on-site premium/discount
- If data not found for specific title: broaden search to similar titles
- If all sources fail: log warning, continue with available data

### Step 3 — Analyze the offer
- Call `tools/analyze_offer.py` with offer data and market data
- The tool sends this prompt:

```
Analyze this job offer against market data.
Return only a JSON object with no extra text.

Offer:
- Title: {job_title}
- Company: {job_company}
- Offered salary: {salary_min} - {salary_max}
- Location: {job_location}
- Modality: {job_modality}

Market data for {job_title} in {job_location}:
- P25: {p25}
- P50: {p50}
- P75: {p75}
- P90: {p90}

Candidate profile:
- Experience level: {experience_level}
- Key skills: {tech_stack}
- Minimum acceptable: {user_salary_min}

Return:
{
  "offer_percentile": integer (where the offer sits in the market),
  "verdict": "below_market" | "at_market" | "above_market",
  "recommended_counter": integer (what to counter with),
  "reasoning": "2-3 sentence explanation",
  "negotiation_leverage": ["list of factors that strengthen the candidate's position"],
  "risks": ["list of factors that weaken the position"]
}
```

### Step 4 — Generate negotiation script
- Call `tools/generate_negotiation_script.py` with the analysis from Step 3
- Generate:
  - Opening statement (how to start the negotiation conversation)
  - Counter-offer phrasing (exact words to use)
  - Response to pushback (if they say no)
  - Closing (how to accept or decline professionally)
- Format: word-for-word script the user can practice

### Step 5 — Save salary report
- Call `tools/save_salary_report.py`
- Save to `salary_reports` table:
  - `application_id`
  - `user_id`
  - `market_data`: JSON (P25, P50, P75, P90)
  - `offer_percentile`
  - `verdict`
  - `recommended_counter`
  - `negotiation_script`: text
  - `created_at`

### Step 6 — Notify user
- Call `tools/create_notification.py`:
  - `type`: "salary_report_ready"
  - `message`: "Your offer from {company} is {verdict}. Recommended counter: ${recommended_counter}"

### Step 7 — Log result
- Write to `agent_logs`:
  - `user_id`
  - `job_id`
  - `agent`: "salary"
  - `verdict`: below_market / at_market / above_market
  - `timestamp`

---

## Expected Output

- Salary report saved with market benchmarks and offer analysis
- Negotiation script ready on dashboard
- User notified immediately

---

## Error Handling

| Situation | Action |
|---|---|
| No market data found | Use broader job title, log warning |
| Offer salary not in email | Generate report with market data only, note offer amount unknown |
| LLM analysis fails | Save raw market data only, notify user |
| All salary sources unavailable | Notify user, provide manual research links |

---

## Notes

- Never tell the user what decision to make. The report provides data and options — the decision is always theirs.
- The recommended counter should be the P75 value unless the candidate has specific leverage that justifies P90.
- Remote roles require location-adjusted analysis. A remote job at a San Francisco company paying SF rates is different from one paying local rates.
- Salary data goes stale fast in tech. Always note the data fetch date in the report.
