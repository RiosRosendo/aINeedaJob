# Workflow: Decision

## Objective

Route each scored job to the correct action based on its fit score. Either trigger the Application Agent automatically, notify the user for manual approval, or discard the job silently.

---

## Trigger

- Automatic: triggered by Job Match Agent after a FitScore is saved
- Manual: admin can re-trigger on any job with status `scored`

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `job_id` | Database | The job to route |
| `user_id` | Database | The user this job belongs to |
| `score` | fit_scores table | Numeric fit score 0-100 |
| `decision` | fit_scores table | "apply" / "review" / "ignore" |
| `strengths` | fit_scores table | List of strengths from Job Match Agent |
| `gaps` | fit_scores table | List of gaps from Job Match Agent |
| `summary` | fit_scores table | One sentence explanation |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/create_notification.py` | Insert a notification record for the user |
| `tools/update_application.py` | Create or update an Application record |
| `tools/trigger_agent.py` | Trigger the next agent in the pipeline |

---

## Steps

### Step 1 — Load FitScore
- Query `fit_scores` table for the latest score for this `job_id` and `user_id`
- If not found: log error, abort
- If job status is not `scored`: log warning, abort

### Step 2 — Route by decision

#### If decision = "apply" (score ≥ 85)
1. Create an `Application` record with status `pending_application`
2. Call `tools/trigger_agent.py` to trigger the CV Tailoring Agent
3. Log action: "auto_apply triggered"

#### If decision = "review" (score 60–84)
1. Create an `Application` record with status `pending_approval`
2. Call `tools/create_notification.py` with:
   - `user_id`
   - `type`: "approval_required"
   - `job_id`
   - `message`: "A job matching {score}% of your profile needs your approval"
   - `expires_at`: now + 48 hours
3. Log action: "user_notified for approval"
4. STOP — do not trigger any further agents. Wait for user response.

#### If decision = "ignore" (score < 60)
1. Create an `Application` record with status `ignored`
2. Do NOT create a notification
3. Do NOT trigger any further agents
4. Log action: "job_ignored"

### Step 3 — Handle user response (review cases only)
This step is event-driven, not sequential. It fires when the user responds to a notification.

#### If user approves
- Update `Application` status to `pending_application`
- Call `tools/trigger_agent.py` to trigger CV Tailoring Agent
- Log action: "user_approved, cv_tailoring triggered"

#### If user dismisses
- Update `Application` status to `ignored`
- Mark notification as resolved
- Log action: "user_dismissed"

#### If no response after 48 hours
- Update `Application` status to `ignored`
- Mark notification as expired
- Log action: "approval_expired, job_ignored"

### Step 4 — Log result
- Write a record to `agent_logs`:
  - `user_id`
  - `job_id`
  - `agent`: "decision"
  - `action`: "auto_apply" / "pending_approval" / "ignored"
  - `score`: the fit score
  - `timestamp`

---

## Expected Output

- New `Application` record in the `applications` table
- Notification record (only for review cases)
- CV Tailoring Agent triggered (for apply and approved review cases)

---

## Error Handling

| Situation | Action |
|---|---|
| FitScore not found | Abort, log error |
| Notification delivery fails | Log error, retry once, then mark as `notification_failed` |
| Trigger agent fails | Log error, retry once, then alert admin |
| User responds after expiry | Ignore response, log warning |
| Duplicate application for same job | Skip, log warning "Application already exists" |

---

## Notes

- This agent never applies on behalf of the user without either a score ≥ 85 or explicit user approval. This is a hard rule — never bypass it.
- The 48-hour expiry window can be made configurable per user in a future version.
- Notifications must show the job title, company, fit score, strengths, and gaps — not just the score number. The user needs context to make a good decision.
- Keep the ignore list accessible on the dashboard so users can recover a dismissed job if they change their mind.
