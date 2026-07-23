'use client';

import { useEffect, useState } from 'react';
import { getApplications } from '@/lib/api';

interface ApplicationData {
  id: string;
  job_id: string;
  user_id: string;
  status: string;
  cv_version_url?: string;
  cover_letter_url?: string;
  applied_at?: string;
  created_at: string;
  updated_at: string;
  job_title?: string;
  job_company?: string;
  job_url?: string;
  application_method?: 'email' | 'form' | 'manual';
  application_notes?: string;
  fit_score?: number;
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<ApplicationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [checking, setChecking] = useState(false);
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [showIgnored, setShowIgnored] = useState(false);

  useEffect(() => {
    const loadApplications = async () => {
      try {
        setLoading(true);
        setError(null);

        const apps = await getApplications(100);
        setApplications(apps);

        // Try to load last checked time from localStorage
        const cached = localStorage.getItem('emailCheckTime');
        if (cached) {
          setLastChecked(cached);
        }
      } catch (err) {
        console.error('Failed to load applications:', err);
        setError('Failed to load applications. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadApplications();
  }, []);

  const handleCheckEmails = async () => {
    try {
      setChecking(true);
      const response = await fetch('http://localhost:8001/api/gmail/check', {
        method: 'GET',
        headers: {
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('[EMAIL CHECK] Result:', data);

      // Save last checked time
      const now = new Date().toLocaleTimeString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
      setLastChecked(now);
      localStorage.setItem('emailCheckTime', now);

      // Reload applications to reflect any status updates
      const apps = await getApplications(100);
      setApplications(apps);

    } catch (err) {
      console.error('Failed to check emails:', err);
      setError('Failed to check emails. Make sure Gmail is connected.');
    } finally {
      setChecking(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'applied':
        return '#3b82f6'; // blue
      case 'interview':
        return '#f59e0b'; // amber
      case 'offer':
        return '#10b981'; // green
      case 'rejected':
        return '#ef4444'; // red
      case 'ignored':
        return '#6b7280'; // gray
      case 'pending_approval':
        return '#f59e0b'; // amber
      default:
        return '#9ca3af'; // neutral gray
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending_approval':
        return 'Pending Review';
      case 'pending_application':
        return 'Pending Apply';
      case 'requires_manual':
        return 'Manual Apply';
      case 'in_review':
        return 'In Review';
      default:
        return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };

  const extractCompanyFromUrl = (url?: string, company?: string): string => {
    if (company && company !== 'Unknown Company') return company;
    if (!url) return 'Unknown Company';

    try {
      const urlObj = new URL(url);
      const domain = urlObj.hostname.replace('www.', '').split('.')[0];
      return domain.charAt(0).toUpperCase() + domain.slice(1);
    } catch {
      return company || 'Unknown Company';
    }
  };

  // Filter applications
  const filteredApplications = applications.filter(item => {
    const status = item?.application?.status || item?.status;
    const fitScore = item?.fit_score || (item?.application?.fit_score as any) || 0;

    // Hide ignored by default unless showIgnored is true
    if (!showIgnored && status === 'ignored') {
      return false;
    }

    // Filter out low-relevance jobs (fit_score < 60)
    if (fitScore < 60 && status !== 'ignored') {
      return false;
    }

    if (statusFilter === 'all') return true;
    return status === statusFilter;
  });

  const statuses = ['all', 'pending_approval', 'pending_application', 'applied', 'interview', 'offer', 'rejected'];
  const ignoredCount = applications.filter(item => (item?.application?.status || item?.status) === 'ignored').length;

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
              Applications
            </h1>
            <p style={{ color: 'var(--muted)' }}>
              {filteredApplications.length} of {applications.length} applications
            </p>
            {lastChecked && (
              <p
                className="text-xs mt-2"
                style={{ color: 'var(--faint)' }}
              >
                Last email check: {lastChecked}
              </p>
            )}
          </div>
          <button
            onClick={handleCheckEmails}
            disabled={checking}
            className="px-4 py-2 rounded-lg font-medium text-sm transition-all"
            style={{
              backgroundColor: checking ? 'var(--border)' : 'var(--primary-bg)',
              color: checking ? 'var(--muted)' : 'var(--primary-text)',
              cursor: checking ? 'not-allowed' : 'pointer',
              opacity: checking ? 0.6 : 1,
            }}
          >
            {checking ? 'Checking...' : 'Check Emails'}
          </button>
        </div>
      </div>

      {error && (
        <div
          className="mb-6 p-4 border rounded-lg"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: '#fee',
            color: '#c00',
          }}
        >
          {error}
        </div>
      )}

      {/* Status Filter */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <label
            className="text-xs font-semibold uppercase"
            style={{ color: 'var(--faint)' }}
          >
            Filter by Status
          </label>
          {ignoredCount > 0 && (
            <button
              onClick={() => setShowIgnored(!showIgnored)}
              className="text-xs font-medium px-2.5 py-1.5 rounded-lg transition-all"
              style={{
                backgroundColor: showIgnored ? 'var(--primary-bg)' : 'var(--card)',
                color: showIgnored ? 'var(--primary-text)' : 'var(--muted)',
                borderColor: 'var(--border)',
                border: '1px solid',
              }}
            >
              {showIgnored ? `Hide ignored (${ignoredCount})` : `Show ignored (${ignoredCount})`}
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {statuses.map(status => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className="px-3 py-2 rounded-lg text-xs font-medium transition-all"
              style={{
                backgroundColor:
                  statusFilter === status ? 'var(--primary-bg)' : 'var(--card)',
                color:
                  statusFilter === status ? 'var(--primary-text)' : 'var(--muted)',
                borderColor: 'var(--border)',
                border: '1px solid',
              }}
            >
              {getStatusLabel(status)}
            </button>
          ))}
        </div>
      </div>

      {/* Applications List */}
      {loading ? (
        <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '40px' }}>
          Loading applications...
        </div>
      ) : filteredApplications.length === 0 ? (
        <div
          style={{
            padding: '40px 20px',
            textAlign: 'center',
            borderRadius: '12px',
            backgroundColor: 'var(--card)',
            border: '1px solid var(--border)',
            color: 'var(--muted)',
          }}
        >
          <p className="text-lg">No applications found</p>
          <p className="text-sm mt-2">Try adjusting your filters</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredApplications.map((app, index) => (
            <ApplicationRow
              key={app.id}
              application={app}
              delay={index * 0.02}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface ApplicationRowProps {
  application: ApplicationData;
  delay: number;
}

function ApplicationRow({ application, delay }: ApplicationRowProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'applied':
        return '#3b82f6'; // blue
      case 'interview':
        return '#f59e0b'; // amber
      case 'offer':
        return '#10b981'; // green
      case 'rejected':
        return '#ef4444'; // red
      case 'ignored':
        return '#6b7280'; // gray
      case 'pending_approval':
        return '#f59e0b'; // amber
      case 'requires_manual':
        return '#f59e0b'; // amber
      default:
        return '#9ca3af'; // neutral gray
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending_approval':
        return 'Pending Review';
      case 'pending_application':
        return 'Pending Apply';
      case 'requires_manual':
        return 'Manual Apply';
      case 'in_review':
        return 'In Review';
      default:
        return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };

  const extractCompanyFromUrl = (url?: string, company?: string): string => {
    if (company && company !== 'Unknown Company') return company;
    if (!url) return 'Unknown Company';

    try {
      const urlObj = new URL(url);
      const domain = urlObj.hostname.replace('www.', '').split('.')[0];
      return domain.charAt(0).toUpperCase() + domain.slice(1);
    } catch {
      return company || 'Unknown Company';
    }
  };

  const createdDate = application?.created_at ? new Date(application.created_at) : new Date();
  const dateStr = createdDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: createdDate.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
  });

  const jobTitle = application?.job_title || 'Unknown Job';
  const company = extractCompanyFromUrl(application?.job_url, application?.job_company);
  const status = application?.status || 'unknown';
  const jobUrl = application?.job_url;
  const applicationMethod = application?.application_method;
  const applicationNotes = application?.application_notes;

  const getMethodColor = (method?: string) => {
    switch (method) {
      case 'form':
        return '#3b82f6'; // blue
      case 'email':
        return '#8b5cf6'; // purple
      case 'manual':
        return '#f59e0b'; // amber
      default:
        return 'var(--border)';
    }
  };

  return (
    <div
      className="border rounded-lg p-4 hover:shadow-md transition-all animate-fade-up"
      style={{
        borderColor: 'var(--border)',
        backgroundColor: 'var(--card)',
        animationDelay: `${delay}s`,
      }}
    >
      <div className="flex items-start justify-between gap-4">
        {/* Left: Job Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 mb-1">
            <h3
              className="font-semibold text-sm truncate"
              style={{
                color: 'var(--text)',
                letterSpacing: '-0.01em',
              }}
            >
              {jobTitle}
            </h3>
            {jobUrl && (
              <a
                href={jobUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:text-blue-600 flex-shrink-0 mt-0.5"
                title="View job posting"
              >
                ↗
              </a>
            )}
          </div>
          <p
            className="text-xs mb-3"
            style={{ color: 'var(--muted)' }}
          >
            {company}
          </p>
          <div className="flex flex-wrap gap-2">
            {/* Status Badge */}
            <span
              className="text-xs px-2.5 py-1.5 rounded-full font-medium"
              style={{
                color: 'white',
                backgroundColor: getStatusColor(status),
              }}
            >
              {getStatusLabel(status)}
            </span>

            {/* Application Method Badge */}
            {applicationMethod && (
              <span
                className="text-xs px-2.5 py-1.5 rounded-full font-medium"
                style={{
                  color: 'white',
                  backgroundColor: getMethodColor(applicationMethod),
                }}
              >
                Applied via {applicationMethod}
              </span>
            )}

            {/* Date */}
            <span
              className="text-xs px-2 py-1 rounded-full border"
              style={{
                borderColor: 'var(--border)',
                color: 'var(--faint)',
              }}
            >
              {dateStr}
            </span>
          </div>

          {/* Manual Apply Instructions */}
          {status === 'requires_manual' && applicationNotes && (
            <div
              className="mt-3 p-2.5 rounded-lg border text-xs"
              style={{
                backgroundColor: '#fffbeb',
                borderColor: '#fcd34d',
                color: '#92400e',
                fontWeight: '500',
              }}
            >
              {applicationNotes}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
