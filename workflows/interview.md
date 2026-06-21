# Workflow: Interview

## Objective

When an interview invitation is detected, research the company and role, then generate a personalized interview preparation kit including technical questions, behavioral questions, and a mock interview session.

---

## Trigger

- Automatic: triggered by Email Monitoring Agent when Application status changes to `interview`
- Manual: user can request interview prep from dashboard for any application

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `application_id` | Database | The application with interview |
| `job_id` | Database | The target job |
| `user_id` | Database | The user preparing |
| `title` | jobs table | Job title |
| `company` | jobs table | Company name |
| `description_raw` | jobs table | Full job description |
| `required_skills` | jobs table | Skills the job requires |
| `tech_stack` | UserProfile | User's skills |
| `gaps` | fit_scores table | Skill gaps identified during matching |
| `strengths` | fit_scores table | Strengths identified during matching |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/research_company.py` | Fetch company info via web search |
| `tools/generate_tech_questions.py` | Generate technical interview questions via LLM |
| `tools/generate_behavioral_questions.py` | Generate behavioral questions via LLM |
| `tools/generate_mock_interview.py` | Generate full mock interview session via LLM |
| `tools/save_interview_prep.py` | Save prep kit to database |
| `tools/create_notification.py` | Notify user that prep kit is ready |

---

## Steps

### Step 1 — Load all inputs
- Query `applications`, `jobs`, `fit_scores`, and `user_profiles` tables
- If any required input missing: log error, notify user, abort

### Step 2 — Research the company
- Call `tools/research_company.py` with company name
- Fetch from public sources:
  - Company website (About page, Careers page)
  - Recent news (last 6 months)
  - Glassdoor reviews summary
  - LinkedIn company page
- Extract:
  - Company mission and values
  - Recent product launches or news
  - Tech stack used (from job postings, engineering blog)
  - Interview culture (from Glassdoor)
  - Company size and funding stage
- If research fails: log warning, continue with available data

### Step 3 — Generate technical questions
- Call `tools/generate_tech_questions.py`
- The tool sends this prompt:

```
Generate technical interview questions for this role.
Return only a JSON object with no extra text.

Role: {job_title} at {job_company}
Required skills: {required_skills}
Candidate skill gaps: {gaps}
Company tech stack: {company_tech_stack}

Generate 10 technical questions ordered by difficulty (easy to hard).
Focus extra questions on the candidate's skill gaps.

Return:
{
  "questions": [
    {
      "question": "string",
      "skill_tested": "string",
      "difficulty": "easy" | "medium" | "hard",
      "hint": "one sentence hint if stuck",
      "ideal_answer_points": ["list of key points a good answer covers"]
    }
  ]
}
```

### Step 4 — Generate behavioral questions
- Call `tools/generate_behavioral_questions.py`
- The tool sends this prompt:

```
Generate behavioral interview questions for this role.
Return only a JSON object with no extra text.

Role: {job_title} at {job_company}
Company values: {company_values}
Candidate strengths: {strengths}

Generate 5 behavioral questions using the STAR format.
Focus on situations that highlight the candidate's strengths.

Return:
{
  "questions": [
    {
      "question": "string",
      "what_they_want_to_know": "string",
      "star_prompt": "Situation / Task / Action / Result — what to cover in each"
    }
  ]
}
```

### Step 5 — Generate mock interview
- Call `tools/generate_mock_interview.py`
- Creates a structured mock interview session:
  - 3 technical questions (medium difficulty)
  - 2 behavioral questions
  - Opening small talk simulation
  - Closing "do you have any questions for us" section with 3 suggested questions to ask
- Format: conversational script the user can practice with

### Step 6 — Save prep kit
- Call `tools/save_interview_prep.py`
- Save to `interview_prep` table:
  - `application_id`
  - `user_id`
  - `company_research`: JSON
  - `technical_questions`: JSON
  - `behavioral_questions`: JSON
  - `mock_interview`: text
  - `created_at`
- Update Application status to `interview_prep_ready`

### Step 7 — Notify user
- Call `tools/create_notification.py`:
  - `type`: "interview_prep_ready"
  - `message`: "Your interview prep kit for {job_title} at {job_company} is ready"

### Step 8 — Log result
- Write to `agent_logs`:
  - `user_id`
  - `job_id`
  - `agent`: "interview"
  - `questions_generated`: count
  - `timestamp`

---

## Expected Output

- Full interview prep kit saved to database
- User notified with link to prep kit on dashboard
- Prep kit includes: company research, technical questions with hints, behavioral questions with STAR guidance, mock interview script

---

## Error Handling

| Situation | Action |
|---|---|
| Company research fails | Log warning, generate questions without company context |
| Technical questions LLM fails | Log error, skip technical section, continue |
| Behavioral questions LLM fails | Log error, skip behavioral section, continue |
| All LLM calls fail | Notify user, provide manual research links instead |
| No skill gaps identified | Generate general questions for the role level |

---

## Notes

- The prep kit must be available on the dashboard within 5 minutes of the interview invitation being detected.
- Never promise that the generated questions will be asked in the real interview. Frame them as "likely topics based on the role and company."
- The mock interview is meant to be practiced out loud, not read. The dashboard should present it in a conversational format.
- Company research from Glassdoor must be treated carefully — it reflects employee opinions, not facts. Present it as "what employees say" not "company facts."
