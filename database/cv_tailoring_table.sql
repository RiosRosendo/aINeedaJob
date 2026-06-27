-- ============================================================================
-- CV Tailoring Table
-- Stores tailored CVs generated for specific jobs
-- ============================================================================

CREATE TABLE IF NOT EXISTS cv_tailored (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  summary TEXT,
  highlighted_skills JSONB DEFAULT '[]'::jsonb,
  relevant_projects JSONB DEFAULT '[]'::jsonb,
  tailoring_notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT unique_user_job_tailor UNIQUE (user_id, job_id)
);

CREATE INDEX idx_cv_tailored_user_id ON cv_tailored(user_id);
CREATE INDEX idx_cv_tailored_job_id ON cv_tailored(job_id);
CREATE INDEX idx_cv_tailored_created_at ON cv_tailored(created_at);

COMMENT ON TABLE cv_tailored IS 'Tailored CVs generated for specific jobs, optimized for ATS and job match';
COMMENT ON COLUMN cv_tailored.summary IS 'Professional summary tailored to the specific job';
COMMENT ON COLUMN cv_tailored.highlighted_skills IS 'JSON array of skills highlighted for this job, in order of relevance';
COMMENT ON COLUMN cv_tailored.relevant_projects IS 'JSON array of projects with tailoring notes, emphasizing relevance to this job';
COMMENT ON COLUMN cv_tailored.tailoring_notes IS 'Explanation of what was tailored and why';
