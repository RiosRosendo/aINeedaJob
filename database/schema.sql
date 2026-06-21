-- ============================================================================
-- aINeedJob PostgreSQL Schema
-- ============================================================================
-- Production-ready schema for the WAT framework job automation system.
-- Generated from 11 workflows: job_discovery, job_parsing, job_match, decision,
-- cv_tailoring, application, email_monitoring, follow_up, interview, salary,
-- and career_memory.
-- ============================================================================

-- ============================================================================
-- ENUMS (Fixed-value types)
-- ============================================================================

CREATE TYPE job_modality AS ENUM ('remote', 'hybrid', 'on-site', 'unknown');
CREATE TYPE job_source AS ENUM ('adzuna', 'themuse', 'linkedin', 'indeed', 'direct', 'other');
CREATE TYPE job_experience_level AS ENUM ('junior', 'mid', 'senior', 'unknown');
CREATE TYPE job_status AS ENUM (
  'discovered',
  'parsed',
  'parse_failed',
  'scored',
  'match_failed',
  'ignored'
);

CREATE TYPE application_status AS ENUM (
  'pending_application',
  'pending_approval',
  'documents_ready',
  'applied',
  'applied_unconfirmed',
  'requires_manual',
  'job_expired',
  'failed',
  'ignored',
  'interview',
  'interview_prep_ready',
  'assessment',
  'offer',
  'rejected',
  'followup_exhausted'
);

CREATE TYPE fit_decision AS ENUM ('apply', 'review', 'ignore');
CREATE TYPE notification_type AS ENUM (
  'approval_required',
  'application_submitted',
  'interview_invite',
  'offer',
  'rejection',
  'assessment',
  'salary_report_ready',
  'interview_prep_ready',
  'career_insights_ready'
);

CREATE TYPE salary_verdict AS ENUM ('below_market', 'at_market', 'above_market');
CREATE TYPE email_provider AS ENUM ('gmail', 'outlook');

-- ============================================================================
-- MAIN TABLES
-- ============================================================================

-- Users: Core user accounts
-- ============================================================================
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  email_verified BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT email_valid CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

COMMENT ON TABLE users IS 'Core user account information. Each user can have one profile and multiple jobs/applications.';
COMMENT ON COLUMN users.id IS 'Unique user identifier (UUID)';
COMMENT ON COLUMN users.email IS 'Email address, unique and validated';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password, never plain text';
COMMENT ON COLUMN users.email_verified IS 'Whether user verified their email address';
COMMENT ON COLUMN users.is_active IS 'Soft delete flag - inactive users still exist in DB';

-- ============================================================================
-- User Profiles: Extended user profile and preferences
-- ============================================================================
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE,
  target_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
  preferred_modality job_modality DEFAULT 'remote',
  preferred_countries JSONB NOT NULL DEFAULT '[]'::jsonb,
  salary_min INTEGER,
  tech_stack JSONB NOT NULL DEFAULT '[]'::jsonb,
  cv_base_url TEXT,
  github_url VARCHAR(255),
  linkedin_url VARCHAR(255),
  email_provider email_provider,
  last_checked_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_user_profiles_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT salary_min_valid CHECK (salary_min IS NULL OR salary_min > 0)
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_email_provider ON user_profiles(email_provider);

COMMENT ON TABLE user_profiles IS 'Extended user profile including job preferences, skills, and profile URLs. One profile per user.';
COMMENT ON COLUMN user_profiles.target_roles IS 'JSON array of target job titles. e.g. ["AI Engineer", "Robotics Engineer"]';
COMMENT ON COLUMN user_profiles.preferred_modality IS 'Preferred work arrangement: remote, hybrid, or on-site';
COMMENT ON COLUMN user_profiles.preferred_countries IS 'JSON array of preferred countries for jobs. e.g. ["US", "Canada"]';
COMMENT ON COLUMN user_profiles.salary_min IS 'Minimum acceptable annual salary in USD';
COMMENT ON COLUMN user_profiles.tech_stack IS 'JSON array of user''s technical skills. e.g. ["Python", "Docker", "ROS2"]';
COMMENT ON COLUMN user_profiles.cv_base_url IS 'Path/URL to user''s base CV file (PDF or text)';
COMMENT ON COLUMN user_profiles.email_provider IS 'Which email provider user connected (Gmail or Outlook)';
COMMENT ON COLUMN user_profiles.last_checked_at IS 'Last time Email Monitoring Agent checked inbox';

-- ============================================================================
-- Jobs: Job listings discovered from job boards
-- ============================================================================
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  source job_source NOT NULL DEFAULT 'other',
  url TEXT NOT NULL,
  title_raw VARCHAR(255),
  title VARCHAR(255),
  company VARCHAR(255),
  location VARCHAR(255),
  modality job_modality DEFAULT 'unknown',
  salary_min INTEGER,
  salary_max INTEGER,
  required_skills JSONB DEFAULT '[]'::jsonb,
  nice_to_have_skills JSONB DEFAULT '[]'::jsonb,
  experience_level job_experience_level DEFAULT 'unknown',
  experience_years_min INTEGER,
  responsibilities JSONB DEFAULT '[]'::jsonb,
  description_raw TEXT,
  status job_status DEFAULT 'discovered',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_jobs_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT salary_range_valid CHECK (
    (salary_min IS NULL AND salary_max IS NULL) OR
    (salary_min IS NOT NULL AND salary_max IS NOT NULL AND salary_min <= salary_max) OR
    (salary_min IS NOT NULL AND salary_max IS NULL) OR
    (salary_min IS NULL AND salary_max IS NOT NULL)
  ),
  CONSTRAINT salary_positive CHECK (salary_min IS NULL OR salary_min > 0),
  CONSTRAINT experience_years_valid CHECK (experience_years_min IS NULL OR experience_years_min >= 0),
  CONSTRAINT url_per_user_unique UNIQUE (user_id, url)
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_user_status ON jobs(user_id, status);

COMMENT ON TABLE jobs IS 'Job listings discovered from job boards (Adzuna, The Muse, etc). Stores both raw and parsed data.';
COMMENT ON COLUMN jobs.source IS 'Which job board this came from (adzuna, themuse, linkedin, indeed, direct, other)';
COMMENT ON COLUMN jobs.url IS 'Original job posting URL, unique per user to avoid duplicates';
COMMENT ON COLUMN jobs.title_raw IS 'Raw job title as scraped from the board';
COMMENT ON COLUMN jobs.title IS 'Parsed/cleaned job title extracted by Job Parsing Agent';
COMMENT ON COLUMN jobs.description_raw IS 'Full raw HTML/text from job board. Kept intact for reference, never modified.';
COMMENT ON COLUMN jobs.status IS 'Pipeline status: discovered → parsed → scored, or parse_failed/match_failed';
COMMENT ON COLUMN jobs.required_skills IS 'JSON array of required technical skills, extracted by parsing agent';
COMMENT ON COLUMN jobs.nice_to_have_skills IS 'JSON array of nice-to-have skills, extracted by parsing agent';

-- ============================================================================
-- Fit Scores: Job-to-profile matching scores
-- ============================================================================
CREATE TABLE fit_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL,
  user_id UUID NOT NULL,
  score INTEGER NOT NULL,
  decision fit_decision NOT NULL,
  strengths JSONB DEFAULT '[]'::jsonb,
  gaps JSONB DEFAULT '[]'::jsonb,
  summary TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_fit_scores_job_id FOREIGN KEY (job_id)
    REFERENCES jobs(id) ON DELETE CASCADE,
  CONSTRAINT fk_fit_scores_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT score_range CHECK (score >= 0 AND score <= 100)
);

CREATE INDEX idx_fit_scores_job_id ON fit_scores(job_id);
CREATE INDEX idx_fit_scores_user_id ON fit_scores(user_id);
CREATE INDEX idx_fit_scores_decision ON fit_scores(decision);
CREATE INDEX idx_fit_scores_score ON fit_scores(score);
CREATE INDEX idx_fit_scores_created_at ON fit_scores(created_at);
CREATE INDEX idx_fit_scores_job_user ON fit_scores(job_id, user_id);

COMMENT ON TABLE fit_scores IS 'Job-to-profile fit scores computed by Job Match Agent. Provides decision (apply/review/ignore) and explanation.';
COMMENT ON COLUMN fit_scores.score IS 'Numeric fit score 0-100. Decision rules: ≥85 = apply, 60-84 = review, <60 = ignore';
COMMENT ON COLUMN fit_scores.decision IS 'Recommended action: apply (auto-apply), review (user approval), or ignore (skip)';
COMMENT ON COLUMN fit_scores.strengths IS 'JSON array of 3 key strengths: why the user is a good match';
COMMENT ON COLUMN fit_scores.gaps IS 'JSON array of 3 key gaps: what the user is missing for this role';
COMMENT ON COLUMN fit_scores.summary IS 'One sentence explanation of the score (displayed on dashboard)';

-- ============================================================================
-- Applications: Job applications and their lifecycle
-- ============================================================================
CREATE TABLE applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL,
  user_id UUID NOT NULL,
  status application_status DEFAULT 'pending_application',
  cv_version_url TEXT,
  cover_letter_url TEXT,
  applied_at TIMESTAMP WITH TIME ZONE,
  last_followup_at TIMESTAMP WITH TIME ZONE,
  followup_count INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_applications_job_id FOREIGN KEY (job_id)
    REFERENCES jobs(id) ON DELETE CASCADE,
  CONSTRAINT fk_applications_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT followup_count_valid CHECK (followup_count >= 0 AND followup_count <= 2)
);

CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_applied_at ON applications(applied_at);
CREATE INDEX idx_applications_created_at ON applications(created_at);
CREATE INDEX idx_applications_user_status ON applications(user_id, status);

COMMENT ON TABLE applications IS 'Application lifecycle tracking. Follows job from decision → CV generation → submission → response tracking.';
COMMENT ON COLUMN applications.status IS 'Application state machine: pending_application → documents_ready → applied → interview/offer/rejected';
COMMENT ON COLUMN applications.cv_version_url IS 'URL to tailored CV PDF generated for this specific job';
COMMENT ON COLUMN applications.cover_letter_url IS 'URL to cover letter PDF generated for this specific job';
COMMENT ON COLUMN applications.applied_at IS 'Timestamp when application was actually submitted';
COMMENT ON COLUMN applications.last_followup_at IS 'When the last follow-up email was sent (null if never sent)';
COMMENT ON COLUMN applications.followup_count IS 'Number of follow-ups sent. Max 2 follow-ups per application.';

-- ============================================================================
-- Notifications: User notifications for important events
-- ============================================================================
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  job_id UUID,
  type notification_type NOT NULL,
  message TEXT NOT NULL,
  is_read BOOLEAN DEFAULT FALSE,
  expires_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_notifications_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_notifications_job_id FOREIGN KEY (job_id)
    REFERENCES jobs(id) ON DELETE SET NULL
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_expires_at ON notifications(expires_at);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read);

COMMENT ON TABLE notifications IS 'User notifications for important events: approval required, interviews, offers, rejections, ready-to-review items.';
COMMENT ON COLUMN notifications.type IS 'Notification category: approval_required, application_submitted, interview_invite, offer, rejection, assessment, etc.';
COMMENT ON COLUMN notifications.message IS 'Human-readable notification text';
COMMENT ON COLUMN notifications.is_read IS 'Whether user has viewed this notification';
COMMENT ON COLUMN notifications.expires_at IS 'When this notification expires (e.g., 48-hour approval windows)';

-- ============================================================================
-- Agent Logs: Audit trail of all agent runs
-- ============================================================================
CREATE TABLE agent_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  job_id UUID,
  application_id UUID,
  agent VARCHAR(50) NOT NULL,
  status VARCHAR(20),
  details JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_agent_logs_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_agent_logs_job_id FOREIGN KEY (job_id)
    REFERENCES jobs(id) ON DELETE SET NULL,
  CONSTRAINT fk_agent_logs_application_id FOREIGN KEY (application_id)
    REFERENCES applications(id) ON DELETE SET NULL
);

CREATE INDEX idx_agent_logs_user_id ON agent_logs(user_id);
CREATE INDEX idx_agent_logs_agent ON agent_logs(agent);
CREATE INDEX idx_agent_logs_created_at ON agent_logs(created_at);
CREATE INDEX idx_agent_logs_job_id ON agent_logs(job_id);

COMMENT ON TABLE agent_logs IS 'Audit trail of all agent runs. Records every action taken by each agent: job_discovery, job_parsing, job_match, decision, cv_tailoring, application, email_monitoring, follow_up, interview, salary, career_memory.';
COMMENT ON COLUMN agent_logs.agent IS 'Which agent ran: job_discovery, job_parsing, job_match, decision, cv_tailoring, application, email_monitoring, follow_up, interview, salary, or career_memory';
COMMENT ON COLUMN agent_logs.status IS 'Outcome: success, failed, skipped, pending';
COMMENT ON COLUMN agent_logs.details IS 'JSON object storing agent-specific metadata. Structure varies by agent type.';

-- ============================================================================
-- Interview Prep: Interview preparation kits
-- ============================================================================
CREATE TABLE interview_prep (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL,
  user_id UUID NOT NULL,
  company_research JSONB,
  technical_questions JSONB,
  behavioral_questions JSONB,
  mock_interview TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_interview_prep_application_id FOREIGN KEY (application_id)
    REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_interview_prep_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_interview_prep_application_id ON interview_prep(application_id);
CREATE INDEX idx_interview_prep_user_id ON interview_prep(user_id);
CREATE INDEX idx_interview_prep_created_at ON interview_prep(created_at);

COMMENT ON TABLE interview_prep IS 'Interview preparation kits generated by Interview Agent. Contains company research, technical/behavioral questions, and mock interview script.';
COMMENT ON COLUMN interview_prep.company_research IS 'JSON object with: mission, values, recent news, tech stack, interview culture, funding stage';
COMMENT ON COLUMN interview_prep.technical_questions IS 'JSON array of technical interview questions with difficulty levels, hints, and ideal answer points';
COMMENT ON COLUMN interview_prep.behavioral_questions IS 'JSON array of behavioral questions in STAR format with guidance';
COMMENT ON COLUMN interview_prep.mock_interview IS 'Full conversational mock interview script for practice';

-- ============================================================================
-- Salary Reports: Job offer analysis and negotiation guidance
-- ============================================================================
CREATE TABLE salary_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL,
  user_id UUID NOT NULL,
  market_data JSONB,
  offer_percentile INTEGER,
  verdict salary_verdict,
  recommended_counter INTEGER,
  negotiation_script TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_salary_reports_application_id FOREIGN KEY (application_id)
    REFERENCES applications(id) ON DELETE CASCADE,
  CONSTRAINT fk_salary_reports_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT offer_percentile_valid CHECK (offer_percentile IS NULL OR (offer_percentile >= 0 AND offer_percentile <= 100))
);

CREATE INDEX idx_salary_reports_application_id ON salary_reports(application_id);
CREATE INDEX idx_salary_reports_user_id ON salary_reports(user_id);
CREATE INDEX idx_salary_reports_verdict ON salary_reports(verdict);
CREATE INDEX idx_salary_reports_created_at ON salary_reports(created_at);

COMMENT ON TABLE salary_reports IS 'Salary offer analysis generated by Salary Agent. Provides market benchmarking and negotiation strategy.';
COMMENT ON COLUMN salary_reports.market_data IS 'JSON object with salary percentiles: {p25, p50, p75, p90, source_date}';
COMMENT ON COLUMN salary_reports.offer_percentile IS 'Where offered salary sits in market (0-100)';
COMMENT ON COLUMN salary_reports.verdict IS 'Verdict: below_market, at_market, or above_market';
COMMENT ON COLUMN salary_reports.recommended_counter IS 'Recommended counter-offer amount (typically P75 of market)';
COMMENT ON COLUMN salary_reports.negotiation_script IS 'Word-for-word negotiation script: opening, counter phrasing, pushback handling, closing';

-- ============================================================================
-- Career Insights: Pattern analysis and learning recommendations
-- ============================================================================
CREATE TABLE career_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  analysis JSONB,
  learning_plan JSONB,
  applications_analyzed INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_career_insights_user_id FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_career_insights_user_id ON career_insights(user_id);
CREATE INDEX idx_career_insights_created_at ON career_insights(created_at);

COMMENT ON TABLE career_insights IS 'Career pattern analysis and learning recommendations from Career Memory Agent. Generated weekly or on-demand.';
COMMENT ON COLUMN career_insights.analysis IS 'JSON object with: top_skill_gaps, success_patterns, failure_patterns, role_alignment, source_performance, profile_recommendations, summary';
COMMENT ON COLUMN career_insights.learning_plan IS 'JSON object with 4-week action plan: for each skill gap, provides resource, time estimate, and demo project';
COMMENT ON COLUMN career_insights.applications_analyzed IS 'Number of applications included in this analysis (minimum 10 for meaningful insights)';

-- ============================================================================
-- TRIGGERS: Auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_update BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_user_profiles_update BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_jobs_update BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_fit_scores_update BEFORE UPDATE ON fit_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_applications_update BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_notifications_update BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_interview_prep_update BEFORE UPDATE ON interview_prep
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_salary_reports_update BEFORE UPDATE ON salary_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_career_insights_update BEFORE UPDATE ON career_insights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS: Useful query patterns for application logic
-- ============================================================================

-- Active applications needing follow-up (past 7 days, no response)
CREATE VIEW applications_needing_followup AS
SELECT
  a.id,
  a.user_id,
  a.job_id,
  a.applied_at,
  a.last_followup_at,
  a.followup_count,
  j.company,
  j.title
FROM applications a
JOIN jobs j ON a.job_id = j.id
WHERE
  a.status = 'applied'
  AND a.applied_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND a.followup_count < 2
  AND (a.last_followup_at IS NULL OR a.last_followup_at < CURRENT_TIMESTAMP - INTERVAL '7 days');

COMMENT ON VIEW applications_needing_followup IS 'Applications that should receive an automated follow-up (7+ days since application, no response, max 2 follow-ups)';

-- Jobs ready for matching (parsed but not yet scored)
CREATE VIEW jobs_ready_for_matching AS
SELECT
  j.id,
  j.user_id,
  j.title,
  j.company,
  j.status
FROM jobs j
WHERE
  j.status = 'parsed'
  AND NOT EXISTS (SELECT 1 FROM fit_scores fs WHERE fs.job_id = j.id);

COMMENT ON VIEW jobs_ready_for_matching IS 'Jobs in parsed status with no existing fit_score (ready to be processed by Job Match Agent)';

-- User application summary
CREATE VIEW user_application_summary AS
SELECT
  u.id as user_id,
  u.email,
  COUNT(DISTINCT a.id) as total_applications,
  COUNT(DISTINCT CASE WHEN a.status = 'applied' THEN a.id END) as applications_applied,
  COUNT(DISTINCT CASE WHEN a.status = 'interview' THEN a.id END) as interviews,
  COUNT(DISTINCT CASE WHEN a.status = 'offer' THEN a.id END) as offers,
  COUNT(DISTINCT CASE WHEN a.status = 'rejected' THEN a.id END) as rejections,
  COUNT(DISTINCT CASE WHEN a.status = 'ignored' THEN a.id END) as ignored,
  MAX(a.applied_at) as last_application_at
FROM users u
LEFT JOIN applications a ON u.id = a.user_id
GROUP BY u.id, u.email;

COMMENT ON VIEW user_application_summary IS 'Quick summary of each user''s application statistics for dashboard and reporting';

-- ============================================================================
-- FINAL NOTES
-- ============================================================================
-- This schema is designed to:
-- 1. Store complete job search lifecycle from discovery through negotiation
-- 2. Support the WAT framework agents with proper state transitions
-- 3. Provide audit trails via agent_logs for debugging and transparency
-- 4. Use JSONB for flexible storage of LLM outputs (skills, research, etc.)
-- 5. Maintain referential integrity with foreign keys and constraints
-- 6. Include comprehensive indexing for query performance
-- 7. Be production-ready with comments for future maintenance
--
-- Key design decisions:
-- - description_raw is NEVER modified (full audit trail of original text)
-- - All timestamp fields are WITH TIME ZONE for global operation
-- - Cascading deletes for user data (GDPR compliance)
-- - ENUM types for fixed values (status, decisions, verdicts)
-- - JSONB for complex data structures (skills, research, analysis results)
-- - Soft-delete pattern: users.is_active instead of hard delete
-- ============================================================================
