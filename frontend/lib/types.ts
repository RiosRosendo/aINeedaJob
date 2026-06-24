export interface UserProfile {
  user_id: string;
  name: string;
  email: string;
  target_roles: string[];
  preferred_modality: 'remote' | 'hybrid' | 'on-site';
  preferred_countries: string[];
  salary_min: number;
  tech_stack: string[];
  cv_base_url?: string;
  github_url?: string;
  linkedin_url?: string;
}

export interface Job {
  id: string;
  user_id: string;
  source: 'adzuna' | 'themuse' | 'linkedin' | 'indeed';
  title: string;
  company: string;
  location: string;
  modality: 'remote' | 'hybrid' | 'on-site' | 'unknown';
  salary_min?: number;
  salary_max?: number;
  required_skills: string[];
  nice_to_have_skills?: string[];
  experience_level: 'junior' | 'mid' | 'senior' | 'unknown';
  description_raw: string;
  status: 'discovered' | 'parsed' | 'scored' | 'ignored';
  created_at: string;
  fit_score?: number;
  strengths?: string[];
  gaps?: string[];
}

export interface FitScore {
  score_id: string;
  job_id: string;
  user_id: string;
  score: number;
  decision: 'apply' | 'review' | 'ignore';
  strengths: string[];
  gaps: string[];
  scored_at: string;
}

export interface Application {
  id: string;
  job_id: string;
  user_id: string;
  status: 'pending_approval' | 'pending_application' | 'applied' | 'in_review' | 'interview' | 'offer' | 'rejected' | 'ignored';
  cv_version_url?: string;
  cover_letter_url?: string;
  applied_at?: string;
  created_at: string;
  updated_at: string;
  fit_score?: number;
  decision?: 'apply' | 'review' | 'ignore';
  strengths?: string[];
  gaps?: string[];
}

export interface ActivityEvent {
  type: 'discovery' | 'application' | 'tailoring' | 'flagging' | 'scan_complete';
  title: string;
  timestamp: string;
  count?: number;
  company?: string;
  role?: string;
}

export interface DashboardStats {
  jobs_found: number;
  applied: number;
  interviews: number;
  needs_approval: number;
}
