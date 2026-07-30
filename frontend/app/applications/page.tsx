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
  decision?: 'apply' | 'review' | 'ignore';
  strengths?: string[];
  gaps?: string[];
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

        console.log('[APP AUTH] user_id from localStorage:', localStorage.getItem('user_id'));
        console.log('[APP AUTH] token from localStorage:', localStorage.getItem('access_token') ? 'exists' : 'missing');

        const apps = await getApplications(1000);
        console.log('[APP LOAD] Total from API:', apps.length);
        console.log('[APP LOAD] First item:', apps[0]);
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
        console.log('[APP LOAD] Finally block executing, setting loading to false');
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
      const apps = await getApplications(1000);
      console.log('[EMAIL CHECK] Total from API:', apps.length);
      console.log('[EMAIL CHECK] First item:', apps[0]);
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
    const status = item?.status;
    const fitScore = item?.fit_score || 0;

    // Hide ignored by default unless showIgnored is true
    if (!showIgnored && status === 'ignored') {
      return false;
    }

    // Filter out low-relevance jobs (fit_score < 60)
    // But always show applications that are pending or already applied
    if (fitScore < 60 && !['ignored', 'pending_approval', 'pending_application', 'applied', 'interview', 'offer', 'rejected'].includes(status)) {
      return false;
    }

    if (statusFilter === 'all') return true;

    // Map filter tabs to actual status values
    if (statusFilter === 'pending_approval') {
      return status === 'pending_approval';
    }
    if (statusFilter === 'pending_application') {
      return status === 'pending_application' || status === 'requires_manual';
    }

    return status === statusFilter;
  });

  console.log('[APP FILTER] Total before filter:', applications.length);
  console.log('[APP FILTER] Total after filter:', filteredApplications.length);
  console.log('[APP FILTER] First item status:', applications[0]?.status);
  console.log('[APP FILTER] First item fit_score:', applications[0]?.fit_score);
  console.log('[APP FILTER] First item full object:', applications[0]);

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
          {console.log('[APP RENDER] Rendering', filteredApplications.length, 'applications')}
          {filteredApplications.map((app, index) => {
            try {
              return (
                <ApplicationRow
                  key={app.id}
                  application={app}
                  delay={index * 0.02}
                />
              );
            } catch (e) {
              console.error('[APP ROW] Error rendering app:', app.id, e);
              return <div key={app.id}>Error: {app.job_title}</div>;
            }
          })}
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
  console.log('[APP ROW] Rendering:', application.job_title);

  // Filter out poorly extracted titles
  const isValidTitle = (title?: string) => {
    if (!title) return false;
    const lower = title.toLowerCase();
    if (title.length > 120) return false; // Too long - likely bad extraction
    if (lower.includes('extract') || lower.includes('not specified') || lower.includes('job title')) return false;
    if (lower.includes('please') || lower.includes('update')) return false; // Common extraction errors
    return true;
  };

  const displayTitle = isValidTitle(application.job_title) ? application.job_title : 'Unknown Position';

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return null;
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return null;
    }
  };

  const dateStr = formatDate(application.created_at || application.applied_at);

  // Handle action buttons
  const handleApplyNow = () => {
    console.log('[APPLY NOW] job_url:', application.job_url);
    if (application.job_url) {
      window.open(application.job_url, '_blank');
    }
  };

  const handleMarkApplied = async () => {
    try {
      await fetch(`http://localhost:8001/api/applications/${application.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        body: JSON.stringify({ status: 'applied' }),
      });
      window.location.reload();
    } catch (e) {
      console.error('Failed to mark as applied:', e);
    }
  };

  const handleApprove = async () => {
    // TODO: Call API to approve
    console.log('[APP ROW] Approve:', application.id);
  };

  const handleDismiss = async () => {
    // TODO: Call API to dismiss
    console.log('[APP ROW] Dismiss:', application.id);
  };

  return (
    <div className="rounded-lg p-4 mb-3 border border-gray-700 bg-gray-800 hover:bg-gray-750 transition-all">
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1">
          <h3 className="font-bold text-white text-lg">{displayTitle}</h3>
          <p className="text-gray-400 text-sm">{application.job_company}</p>
          <p className="text-gray-500 text-xs mt-1">{application.job_location}</p>
          {dateStr && <p className="text-gray-600 text-xs mt-1">Found {dateStr}</p>}
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="text-blue-400 font-bold text-xl">{application.fit_score}%</span>
          <span className="text-xs px-2 py-1 rounded-full bg-gray-700 text-gray-300">
            {application.status?.replace(/_/g, ' ')}
          </span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 mt-3">
        {(application.status === 'pending_application' || application.status === 'requires_manual') && (
          <>
            <button
              onClick={handleApplyNow}
              className="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              Apply Now
            </button>
            <button
              onClick={handleMarkApplied}
              className="px-3 py-1 text-xs rounded border border-gray-600 text-gray-300 hover:bg-gray-700"
            >
              Mark Applied
            </button>
          </>
        )}

        {application.status === 'pending_approval' && (
          <>
            <button
              onClick={handleApprove}
              className="px-3 py-1 text-xs rounded bg-green-600 text-white hover:bg-green-700"
            >
              Approve
            </button>
            <button
              onClick={handleDismiss}
              className="px-3 py-1 text-xs rounded bg-red-600 text-white hover:bg-red-700"
            >
              Dismiss
            </button>
          </>
        )}

        {application.status === 'applied' && (
          <span className="px-3 py-1 text-xs rounded-full bg-green-900 text-green-300">
            Applied ✓
          </span>
        )}
      </div>

    </div>
  );
}
