# Workflow: Follow-up

## Objective

Automatically generate and send a professional follow-up message when no response has been received after a defined period. Keep the user top-of-mind with recruiters without being pushy.

---

## Trigger

- Scheduled: runs every 24 hours per user (via Celery beat)
- Checks all applications with status `applied` and no response after 7 days

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `user_id` | Database | The user whose applications to check |
| `application_id` | Database | The application to follow up on |
| `job_id` | Database | The target job |
| `applied_at` | applications table | When the application was submitted |
| `last_followup_at` | applications table | When the last follow-up was sent (null if none) |
| `followup_count` | applications table | How many follow-ups have been sent |
| `title` | jobs table | Job title |
| `company` | jobs table | Company name |
| `user_name` | UserProfile | User's full name |
| `email_provider` | UserProfile | "gmail" or "outlook" |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/generate_followup.py` | Generate follow-up message via LLM |
| `tools/send_email_gmail.py` | Send email via Gmail API |
| `tools/send_email_outlook.py` | Send email via Outlook API |
| `tools/update_application.py` | Update follow-up metadata |
| `tools/create_notification.py` | Notify user before sending (if approval required) |

---

## Steps

### Step 1 — Find applications that need follow-up
- Query `applications` table for records where:
  - `user_id` = current user
  - `status` = `applied`
  - `applied_at` < now - 7 days
  - `followup_count` < 2 (maximum 2 follow-ups per application)
  - `last_followup_at` is null OR `last_followup_at` < now - 7 days
- If no applications qualify: log "no follow-ups needed", exit

### Step 2 — Generate follow-up message via LLM
For each qualifying application:
- Call `tools/generate_followup.py` with job and user data
- The tool sends this prompt:

```
Write a professional follow-up email for a job application.
Return only a JSON object with no extra text.

Context:
- Applicant name: {user_name}
- Job title: {job_title}
- Company: {job_company}
- Days since application: {days_since_applied}
- Follow-up number: {followup_count + 1} of 2

Instructions:
- 3-4 sentences maximum
- Express continued interest in the role
- Reference the specific position by title
- Do NOT mention that this is an automated follow-up
- Do NOT be apologetic or overly formal
- Tone: confident, brief, professional
- Do NOT ask "have you made a decision yet" — too pushy

Return:
{
  "subject": "string",
  "body": "string",
  "tone_check": "brief description of tone used"
}
```

- If LLM fails: log error, skip this application, continue to next

### Step 3 — Request user approval (first follow-up only)
- If `followup_count` = 0 (first follow-up ever):
  - Create notification showing the generated message
  - Wait for user to approve or edit before sending
  - If no response in 24 hours: skip this cycle, retry next day
- If `followup_count` = 1 (second follow-up):
  - Send automatically without approval (user already approved the pattern)

### Step 4 — Send follow-up email
- Based on `email_provider`:
  - Gmail: call `tools/send_email_gmail.py`
  - Outlook: call `tools/send_email_outlook.py`
- On success: proceed to Step 5
- On auth error: notify user to reconnect email, abort
- On send failure: log error, retry once, then mark as `followup_failed`

### Step 5 — Update application record
- Increment `followup_count` by 1
- Update `last_followup_at` to current timestamp
- If `followup_count` = 2: update status to `followup_exhausted`

### Step 6 — Log result
- Write a record to `agent_logs`:
  - `user_id`
  - `job_id`
  - `application_id`
  - `agent`: "follow_up"
  - `followup_number`: 1 or 2
  - `status`: "sent" / "pending_approval" / "failed"
  - `timestamp`

---

## Expected Output

- Follow-up email sent on behalf of user
- Application record updated with follow-up metadata
- User notified of sent follow-up

---

## Error Handling

| Situation | Action |
|---|---|
| Email provider not connected | Notify user, skip follow-up |
| LLM generation fails | Skip this application, log error |
| User does not approve in 24h | Skip this cycle, retry next day |
| Max follow-ups reached (2) | Mark as `followup_exhausted`, stop |
| Application gets a response | Email Monitoring Agent updates status, follow-up stops automatically |

---

## Notes

- Never send more than 2 follow-ups per application. More than that damages the user's reputation with the recruiter.
- Always wait at least 7 days between follow-ups.
- If the Email Monitoring Agent detects a response (any classification), immediately stop follow-up for that application.
- The user must be able to disable follow-ups globally or per application from the dashboard.
- Never mention in the follow-up that it was generated or sent automatically.
