import axios from 'axios';
import { UserProfile, Job, Application, FitScore } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_USER_ID || '550e8400-e29b-41d4-a716-446655440000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'x-user-id': DEFAULT_USER_ID,
  },
});

// User Profile
export const getUserProfile = async () => {
  try {
    const response = await api.get<UserProfile>('/api/users/profile');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch user profile:', error);
    throw error;
  }
};

export const updateUserProfile = async (profile: Partial<UserProfile>) => {
  try {
    const response = await api.put<UserProfile>('/api/users/profile', profile);
    return response.data;
  } catch (error) {
    console.error('Failed to update user profile:', error);
    throw error;
  }
};

// Jobs
export const getJobs = async (limit: number = 50) => {
  try {
    const response = await api.get<Job[]>('/api/jobs', {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch jobs:', error);
    throw error;
  }
};

export const getJobsWithStats = async () => {
  try {
    const [jobsResponse, applicationsResponse] = await Promise.all([
      api.get<Job[]>('/api/jobs', { params: { limit: 100 } }),
      api.get<Application[]>('/api/applications', { params: { limit: 100 } }),
    ]);

    const jobs = jobsResponse.data || [];
    const applications = applicationsResponse.data || [];

    // Calculate stats
    const stats = {
      jobs_found: jobs.length,
      applied: applications.filter(a => a.status === 'applied').length,
      interviews: applications.filter(a => a.status === 'interview').length,
      needs_approval: applications.filter(a => a.status === 'pending_approval').length,
    };

    // Get first 3 pending approval jobs for the queue
    const approvalJobIds = new Set(
      applications
        .filter(a => a.status === 'pending_approval')
        .map(a => a.job_id)
    );

    const pendingJobs = jobs
      .filter(j => approvalJobIds.has(j.id))
      .slice(0, 3);

    return { jobs: pendingJobs, stats, allJobs: jobs, allApplications: applications };
  } catch (error) {
    console.error('Failed to fetch jobs with stats:', error);
    throw error;
  }
};

export const getJob = async (jobId: string) => {
  try {
    const response = await api.get<{ job: Job; fit_score?: FitScore }>(`/api/jobs/${jobId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch job:', error);
    throw error;
  }
};

export const triggerJobSearch = async (roles?: string[], country?: string) => {
  try {
    const response = await api.post('/api/jobs/search', {
      roles: roles || ['AI Engineer'],
      country: country || 'us',
    });
    return response.data;
  } catch (error) {
    console.error('Failed to trigger job search:', error);
    throw error;
  }
};

export const getAgentLogs = async (limit: number = 5) => {
  try {
    const response = await api.get('/api/jobs/logs', {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch agent logs:', error);
    return [];
  }
};

export const getPendingApprovalJobs = async () => {
  try {
    const response = await api.get<Application[]>('/api/applications', {
      params: { limit: 100 },
    });
    const applications = response.data || [];

    // Get pending approval applications
    const pendingAppIds = applications
      .filter(app => app.status === 'pending_approval')
      .slice(0, 3)
      .map(app => app.job_id);

    if (pendingAppIds.length === 0) {
      return [];
    }

    // Fetch jobs for these applications
    const allJobs = await getJobs(100);
    return allJobs.filter(job => pendingAppIds.includes(job.id));
  } catch (error) {
    console.error('Failed to fetch pending approval jobs:', error);
    return [];
  }
};

// Applications
export const getApplications = async (limit: number = 50) => {
  try {
    const response = await api.get<Application[]>('/api/applications', {
      params: { limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch applications:', error);
    throw error;
  }
};

export const getApplication = async (applicationId: string) => {
  try {
    const response = await api.get<Application>(`/api/applications/${applicationId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch application:', error);
    throw error;
  }
};

export const approveApplication = async (applicationId: string) => {
  try {
    const response = await api.patch<Application>(`/api/applications/${applicationId}/approve`);
    return response.data;
  } catch (error) {
    console.error('Failed to approve application:', error);
    throw error;
  }
};

export const dismissApplication = async (applicationId: string) => {
  try {
    const response = await api.patch<Application>(`/api/applications/${applicationId}/dismiss`);
    return response.data;
  } catch (error) {
    console.error('Failed to dismiss application:', error);
    throw error;
  }
};
