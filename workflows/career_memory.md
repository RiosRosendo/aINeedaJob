# Workflow: Career Memory

## Objective

Learn from the user's application history over time. Identify patterns in rejections, interview failures, and successful applications. Generate personalized recommendations to improve the user's profile, skills, and strategy continuously.

---

## Trigger

- Scheduled: runs once per week per user (via Celery beat)
- Event-driven: triggered after every 5 new rejection or no-reply outcomes
- Manual: user can request an analysis from the dashboard at any time

---

## Required Inputs

| Input | Source | Description |
|---|---|---|
| `user_id` | Database | The user to analyze |
| `applications` | applications table | Full application history |
| `fit_scores` | fit_scores table | All fit scores with strengths and gaps |
| `interview_outcomes` | applications table | Which interviews led to offers vs rejections |
| `tech_stack` | UserProfile | User's current skills |
| `target_roles` | UserProfile | User's target job titles |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `tools/analyze_history.py` | Analyze application patterns via LLM |
| `tools/generate_learning_plan.py` | Generate skill-building recommendations via LLM |
| `tools/save_career_insights.py` | Save insights to database |
| `tools/create_notification.py` | Notify user of new insights |
| `tools/update_user_profile.py` | Update profile with learned preferences |

---

## Steps

### Step 1 — Load application history
- Query all applications for this `user_id`
- Minimum required: 10 applications to generate meaningful insights
- If fewer than 10: log "insufficient data", exit silently
- Group by outcome:
  - `successful`: status = `offer` or `interview`
  - `rejected`: status = `rejected`
  - `no_reply`: status = `followup_exhausted`
  - `ignored_by_agent`: status = `ignored`

### Step 2 — Extract pattern data
For each application, collect:
- Fit score
- Decision (apply / review / ignore)
- Required skills of the job
- Gaps identified at match time
- Outcome (offer / interview / rejected / no_reply)
- Company size (startup / mid / enterprise)
- Job source (adzuna / themuse / etc.)

### Step 3 — Analyze patterns via LLM
- Call `tools/analyze_history.py` with aggregated pattern data
- The tool sends this prompt:

```
Analyze this user's job application history and identify patterns.
Return only a JSON object with no extra text.

Application summary:
- Total applications: {total}
- Offers received: {offers}
- Interviews reached: {interviews}
- Rejections: {rejections}
- No replies: {no_replies}

Most common skill gaps across rejections:
{top_gaps}

Skills present in successful applications:
{success_skills}

Score distribution:
- Average score: {avg_score}
- Score range of interviews: {interview_score_range}
- Score range of rejections: {rejection_score_range}

Identify:
1. Which skills appear most in gaps of rejected applications
2. Which skills correlate with interview invitations
3. Whether the user's target roles match their actual skill set
4. Whether certain job sources perform better than others
5. Any patterns in company size or type that correlate with success

Return:
{
  "top_skill_gaps": ["ordered list of skills to learn, most impactful first"],
  "success_patterns": ["what is working"],
  "failure_patterns": ["what is not working"],
  "role_alignment": "are target roles realistic given current skills — honest assessment",
  "source_performance": {"source_name": "performance summary"},
  "profile_recommendations": ["specific changes to improve fit scores"],
  "summary": "2-3 sentence overall assessment"
}
```

### Step 4 — Generate learning plan
- If `top_skill_gaps` has 3 or more items:
  - Call `tools/generate_learning_plan.py`
  - For each top skill gap, generate:
    - Best free resource (course, tutorial, documentation)
    - Estimated time to basic proficiency
    - A small project to demonstrate the skill
  - Format as a 4-week action plan

### Step 5 — Save insights
- Call `tools/save_career_insights.py`
- Save to `career_insights` table:
  - `user_id`
  - `analysis`: full JSON from Step 3
  - `learning_plan`: JSON from Step 4
  - `applications_analyzed`: count
  - `created_at`

### Step 6 — Update user profile (if needed)
- If `role_alignment` indicates a significant mismatch:
  - Call `tools/update_user_profile.py` to flag the mismatch
  - Do NOT automatically change `target_roles` — show the recommendation and let the user decide
- If new skills were added to the learning plan and completed:
  - Suggest adding them to `tech_stack` via dashboard

### Step 7 — Notify user
- Call `tools/create_notification.py`:
  - `type`: "career_insights_ready"
  - `message`: "Weekly career insights ready — {summary}"

### Step 8 — Log result
- Write to `agent_logs`:
  - `user_id`
  - `agent`: "career_memory"
  - `applications_analyzed`: count
  - `top_gaps`: first 3 skill gaps identified
  - `timestamp`

---

## Expected Output

- Career insights report with pattern analysis
- Personalized 4-week learning plan
- Profile recommendations
- User notified with summary

---

## Error Handling

| Situation | Action |
|---|---|
| Fewer than 10 applications | Exit silently, no notification |
| LLM analysis fails | Log error, retry next scheduled run |
| No patterns found | Save "insufficient pattern data" report, suggest more applications |
| Learning plan generation fails | Save analysis without learning plan |

---

## Notes

- This agent improves over time as more data accumulates. The first meaningful report requires at least 10 applications. The most useful reports come after 30+.
- Never tell the user they are not qualified for their target role directly. Frame everything as "here is how to get closer to your goal."
- The learning plan must only recommend free or low-cost resources. Do not recommend paid bootcamps or expensive certifications.
- Career insights are personal and sensitive. Never expose one user's insights to another user under any circumstances.
- This agent is what transforms aINeedJob from a job search tool into a long-term career development partner.
