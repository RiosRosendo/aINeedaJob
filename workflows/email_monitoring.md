# Workflow: Email Monitoring

## Objective

Monitor the user's inbox for responses to submitted job applications. Classify each relevant email automatically and update the Application status accordingly. Trigger follow-up or interview preparation when appropriate.

---

## Trigger

- Scheduled: runs every 30 minutes per user (via Celery beat)
- Event-driven: triggered immediately when Application status changes to `applied`

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `user_id` | Database | The user whose inbox to monitor |
| `email_provider` | UserProfile | "gmail" or "outlook" |
| `applied_applications` | applications table | All applications with status `applied` |
| `gmail_token` | Secure storage | OAuth token for Gmail API |
| `outlook_token` | Secure storage | OAuth token for Microsoft Graph API |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/fetch_emails_gmail.py` | Fetch recent emails via Gmail API |
| `tools/fetch_emails_outlook.py` | Fetch recent emails via Outlook API |
| `tools/classify_email.py` | Classify email type via LLM |
| `tools/update_application.py` | Update Application status |
| `tools/create_notification.py` | Notify user of important emails |
| `tools/trigger_agent.py` | Trigger Interview or Follow-up Agent |

---

## Steps

### Step 1 — Load active applications
- Query `applications` table for all records with status `applied` for this `user_id`
- If no active applications: log "no active applications to monitor", exit
- Build a lookup map: `{company_name: application_id}` for fast matching

### Step 2 — Fetch recent emails
- Based on `email_provider`:
  - Gmail: call `tools/fetch_emails_gmail.py`
  - Outlook: call `tools/fetch_emails_outlook.py`
- Fetch only emails received since last monitoring run (use `last_checked_at` from user record)
- Fetch maximum 50 emails per run to avoid rate limits
- On auth error (token expired): log error, notify user to reconnect their email, abort
- On rate limit: log warning, skip this run, retry in 30 minutes

### Step 3 — Filter relevant emails
For each fetched email:
- Check if sender domain matches any company in the active applications lookup
- Check if subject line contains any of: job title, company name, "application", "interview", "position", "opportunity", "offer"
- If neither condition matches: skip email, do not classify
- This pre-filter avoids sending irrelevant emails to the LLM

### Step 4 — Classify relevant emails via LLM
For each email that passes the filter:
- Call `tools/classify_email.py` with email subject, sender, and body (truncated to 1000 chars)
- The tool sends this prompt:

```
Classify this email related to a job application.
Return only a JSON object with no extra text.

Email:
- From: {sender}
- Subject: {subject}
- Body: {body_truncated}

Classify as one of:
- "interview_invite": the company is scheduling an interview
- "offer": the company is making a job offer
- "rejection": the company is declining the application
- "follow_up_request": the company is asking for more information
- "assessment": the company is sending a technical test or assignment
- "no_reply_needed": acknowledgment or auto-reply, no action required
- "unknown": cannot determine

Return:
{
  "classification": "string",
  "confidence": float (0.0 to 1.0),
  "company": "string (extracted from email)",
  "action_required": boolean,
  "summary": "one sentence description of what this email says"
}
```

- If confidence < 0.7: classify as "unknown", do not take automated action
- If LLM fails: log error, skip this email, continue

### Step 5 — Act on classification

#### interview_invite
- Update Application status to `interview`
- Create notification: "Interview invitation from {company}"
- Trigger Interview Agent
- Log action

#### offer
- Update Application status to `offer`
- Create notification: "Job offer received from {company} — review it now"
- Trigger Salary Agent
- Log action

#### rejection
- Update Application status to `rejected`
- Create notification: "Application to {company} was not selected"
- Log action (do not surface to user unless they have notifications enabled for rejections)

#### assessment
- Update Application status to `assessment`
- Create notification: "Technical assessment received from {company}"
- Log action

#### follow_up_request
- Create notification: "{company} is asking for more information"
- Log action — human must respond manually

#### no_reply_needed
- Log silently, no notification, no status change

#### unknown
- Log silently, no automated action
- Flag for admin review if confidence < 0.5

### Step 6 — Update last checked timestamp
- Update `last_checked_at` in user record to current timestamp

### Step 7 — Log result
- Write a record to `agent_logs`:
  - `user_id`
  - `agent`: "email_monitoring"
  - `emails_fetched`: count
  - `emails_classified`: count
  - `actions_taken`: list of classification types found
  - `timestamp`

---

## Expected Output

- Application statuses updated based on email content
- User notified of interview invites, offers, and assessments
- Interview Agent or Salary Agent triggered when appropriate

---

## Error Handling

| Situation | Action |
|---|---|
| OAuth token expired | Notify user to reconnect email, pause monitoring |
| Rate limit from email provider | Skip run, retry in 30 minutes |
| LLM confidence below 0.7 | Classify as unknown, no automated action |
| No active applications | Exit silently |
| Email provider not connected | Notify user to connect Gmail or Outlook |
| Duplicate classification | Check if status already updated, skip |

---

## Notes

- Never read or store the full content of emails that are not related to job applications. Only process emails that pass the Step 3 filter.
- User privacy is critical. Email content must never be logged in plain text. Log only classification results and metadata.
- The confidence threshold of 0.7 is conservative by design. A false positive on an "offer" classification would cause serious problems. When in doubt, do nothing and let the user handle it.
- OAuth tokens must be stored encrypted. Never store them in plain text in the database.
- Give users full control: they must be able to disconnect their email at any time from the dashboard, which immediately stops monitoring.
