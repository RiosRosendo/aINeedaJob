# Workflow: CV Tailoring

## Objective

Generate a customized CV and cover letter for a specific job. Highlight the user's most relevant experience and skills based on the job description and fit score analysis. Produce ready-to-use documents that maximize the user's chances of passing ATS screening.

---

## Trigger

- Automatic: triggered by Decision Agent when decision = "apply" or user approves a "review" job
- Manual: user can request a new CV version for any job from the dashboard

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `job_id` | Database | The job to tailor for |
| `user_id` | Database | The user whose CV to tailor |
| `description_raw` | jobs table | Full job description |
| `required_skills` | jobs table | Skills the job requires |
| `nice_to_have_skills` | jobs table | Preferred skills |
| `title` | jobs table | Job title |
| `company` | jobs table | Company name |
| `strengths` | fit_scores table | Matched strengths from Job Match Agent |
| `gaps` | fit_scores table | Skill gaps from Job Match Agent |
| `cv_base_url` | UserProfile | Path to user's base CV (PDF or text) |
| `github_url` | UserProfile | User's GitHub profile |
| `linkedin_url` | UserProfile | User's LinkedIn profile |
| `tech_stack` | UserProfile | User's full skill set |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/read_cv.py` | Extract text content from the user's base CV |
| `tools/tailor_cv.py` | Generate tailored CV content via LLM |
| `tools/generate_cover_letter.py` | Generate cover letter via LLM |
| `tools/export_pdf.py` | Convert generated content to PDF |
| `tools/save_documents.py` | Save generated files and update Application record |

---

## Steps

### Step 1 — Load all inputs
- Query `jobs`, `fit_scores`, and `user_profiles` tables
- If any required input is missing: log error, abort, notify user

### Step 2 — Extract base CV content
- Call `tools/read_cv.py` with the user's `cv_base_url`
- Extract text content from the PDF
- If CV not found or unreadable: log error, abort, notify user to re-upload their CV

### Step 3 — Generate tailored CV via LLM
- Call `tools/tailor_cv.py` with all inputs
- The tool sends this prompt to the LLM:

```
You are an expert CV writer and career coach.
Rewrite this CV to maximize fit for the target job.
Return only a JSON object with no extra text.

Target job:
- Title: {job_title}
- Company: {job_company}
- Required skills: {required_skills}
- Nice to have: {nice_to_have_skills}
- Full description: {description_raw}

User's current CV:
{cv_text}

User's strengths for this role: {strengths}
User's gaps for this role: {gaps}

Instructions:
- Reorder and reword experience bullets to highlight relevance to this job
- Move the most relevant skills to the top of the skills section
- Use keywords from the job description naturally (for ATS optimization)
- Do NOT invent experience or skills the user does not have
- Do NOT change dates, company names, or job titles
- Keep total length under 1 page (max 600 words of content)

Return:
{
  "summary": "2-3 sentence professional summary tailored to this role",
  "skills": ["ordered list of skills, most relevant first"],
  "experience": [
    {
      "company": "string",
      "title": "string",
      "dates": "string",
      "bullets": ["rewritten bullet points, max 3 per role"]
    }
  ],
  "education": ["unchanged from original"],
  "certifications": ["unchanged from original"]
}
```

- If LLM returns invalid JSON: retry once
- If second attempt fails: log error, abort, notify user

### Step 4 — Validate CV output
- `summary` must not be empty
- `experience` must preserve all original roles (same count as base CV)
- `skills` must only contain skills present in the user's `tech_stack` or base CV
- If validation fails: log error, abort

### Step 5 — Generate cover letter via LLM
- Call `tools/generate_cover_letter.py`
- The tool sends this prompt:

```
Write a professional cover letter for this job application.
Return only a JSON object with no extra text.

Applicant: {user_name}
Target job: {job_title} at {job_company}
Key strengths for this role: {strengths}
Relevant skills: {matched_skills}

Instructions:
- 3 paragraphs maximum
- Opening: express genuine interest in the role and company
- Middle: highlight 2-3 specific strengths with brief evidence
- Closing: call to action, professional sign-off
- Tone: confident but not arrogant, professional but human
- Do NOT use generic phrases like "I am writing to apply for..."
- Length: 200-250 words

Return:
{
  "subject_line": "string (for email applications)",
  "body": "full cover letter text"
}
```

- If LLM fails: log warning, continue without cover letter (CV is the priority)

### Step 6 — Export to PDF
- Call `tools/export_pdf.py` with the tailored CV content
- Generate: `CV_{user_id}_{job_id}.pdf`
- Generate: `CoverLetter_{user_id}_{job_id}.pdf` (if cover letter succeeded)
- If PDF generation fails: log error, save raw text as fallback, continue

### Step 7 — Save documents
- Call `tools/save_documents.py`
- Upload PDFs to cloud storage
- Update `Application` record with:
  - `cv_version_url`: link to tailored CV PDF
  - `cover_letter_url`: link to cover letter PDF
  - `status`: "documents_ready"

### Step 8 — Log result
- Write a record to `agent_logs`:
  - `user_id`
  - `job_id`
  - `agent`: "cv_tailoring"
  - `cv_url`: generated CV path
  - `cover_letter_url`: generated cover letter path
  - `timestamp`
- Trigger Application Agent

---

## Expected Output

- Tailored CV PDF saved to cloud storage
- Cover letter PDF saved to cloud storage
- Application record updated with document URLs and status `documents_ready`
- Application Agent triggered

---

## Error Handling

| Situation | Action |
|---|---|
| Base CV not found | Abort, notify user to upload CV |
| LLM invents skills not in profile | Validation catches it, abort and log |
| LLM removes experience entries | Validation catches it, abort and log |
| PDF export fails | Save raw text as fallback, continue pipeline |
| Cover letter fails | Log warning, continue without it |
| Cloud upload fails | Retry once, then log error and alert admin |

---

## Notes

- The LLM must never invent experience, skills, or credentials. The validation step exists specifically to catch this. If the output adds skills not in the user's profile, reject it entirely.
- ATS optimization means using the job's exact keywords naturally — not stuffing them. The LLM prompt instructs this explicitly.
- Each job gets its own CV version. Never reuse a CV generated for a different job.
- The user can preview and download both documents from the dashboard before the Application Agent submits them.
