'use client';

import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { getApplications } from '@/lib/api';
import { ScoutSidebar } from '@/components/ScoutSidebar';
import { ScoutLoading } from '@/components/ScoutLoading';

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
  job_location?: string;
  job_url?: string;
  application_method?: 'email' | 'form' | 'manual';
  application_notes?: string;
  fit_score?: number;
  decision?: 'apply' | 'review' | 'ignore';
  strengths?: string[];
  gaps?: string[];
}

const getStatusColor = (status: string): { ring: string; text: string; isClosedOut: boolean } => {
  switch (status) {
    case 'pending_approval':
    case 'pending_application':
    case 'requires_manual':
      return { ring: '#c67139', text: '#c67139', isClosedOut: false };
    case 'applied':
    case 'interview':
    case 'offer':
    case 'in_review':
      return { ring: '#7a8a5e', text: '#7a8a5e', isClosedOut: false };
    case 'rejected':
    case 'ignored':
    default:
      return { ring: 'var(--muted)', text: 'var(--muted)', isClosedOut: status === 'rejected' || status === 'ignored' };
  }
};

const getStatusLabel = (status: string): string => {
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
      return status.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  }
};

const getScoreRingColor = (score: number): string => {
  return score >= 70 ? '#7a8a5e' : '#c67139';
};

const getRelativeTime = (date: Date): string => {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.round(diffMs / 1000);
  const diffMinutes = Math.round(diffSeconds / 60);
  const diffHours = Math.round(diffMinutes / 60);

  if (diffSeconds < 60) return 'just now';
  if (diffMinutes === 1) return '1 minute ago';
  if (diffMinutes < 60) return `${diffMinutes} minutes ago`;
  if (diffHours === 1) return '1 hour ago';
  return `${diffHours} hours ago`;
};

const getAllStatuses = (applications: ApplicationData[]) => {
  const statuses = new Set<string>();
  applications.forEach(app => {
    if (app.status === 'pending_application' || app.status === 'requires_manual') {
      statuses.add('pending_application');
    } else {
      statuses.add(app.status);
    }
  });
  return Array.from(statuses).sort();
};

export default function ApplicationsPage() {
  const [isDark, setIsDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [applications, setApplications] = useState<ApplicationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<{ needs_approval: number }>({ needs_approval: 0 });
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [checking, setChecking] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [showIgnored, setShowIgnored] = useState(false);
  const [checkResult, setCheckResult] = useState<{ type: 'success' | 'error' | 'none'; message: string } | null>(null);
  const [emailsFound, setEmailsFound] = useState<number>(0);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.setAttribute('data-dark', '');
    } else {
      root.removeAttribute('data-dark');
    }
  }, [isDark]);

  useEffect(() => {
    const loadApplications = async () => {
      try {
        setLoading(true);
        setError(null);
        const apps = await getApplications(1000);
        setApplications(apps);
        const pendingApprovalCount = apps.filter((app: any) => app.status === 'pending_approval').length;
        setStats({ needs_approval: pendingApprovalCount });

        const cached = localStorage.getItem('emailCheckTime');
        if (cached) {
          setLastChecked(new Date(cached));
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
      setError(null);
      setCheckResult(null);

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
      const now = new Date();
      setLastChecked(now);
      localStorage.setItem('emailCheckTime', now.toISOString());

      const apps = await getApplications(1000);
      setApplications(apps);

      const newEmails = data.emails_found || 0;
      setEmailsFound(newEmails);

      if (newEmails > 0) {
        setCheckResult({
          type: 'success',
          message: `Scout found ${newEmails} new ${newEmails === 1 ? 'reply' : 'replies'}`,
        });
      } else {
        setCheckResult({
          type: 'none',
          message: 'No new replies',
        });
      }

      setTimeout(() => {
        setCheckResult(null);
      }, 5000);

    } catch (err) {
      console.error('Failed to check emails:', err);
      setCheckResult({
        type: 'error',
        message: 'Could not check emails',
      });
      setTimeout(() => {
        setCheckResult(null);
      }, 5000);
    } finally {
      setChecking(false);
    }
  };

  const filteredApplications = applications.filter(item => {
    const status = item?.status;
    const fitScore = item?.fit_score || 0;

    if (!showIgnored && status === 'ignored') {
      return false;
    }

    if (fitScore < 60 && !['ignored', 'pending_approval', 'pending_application', 'applied', 'interview', 'offer', 'rejected', 'requires_manual'].includes(status)) {
      return false;
    }

    if (statusFilter === 'all') return true;

    if (statusFilter === 'pending_application') {
      return status === 'pending_application' || status === 'requires_manual';
    }

    return status === statusFilter;
  });

  const ignoredCount = applications.filter(item => item?.status === 'ignored').length;
  const allStatuses = ['all', ...getAllStatuses(applications)];

  const getStatusCount = (status: string): number => {
    if (status === 'all') return filteredApplications.length;

    return filteredApplications.filter(app => {
      if (status === 'pending_application') {
        return app.status === 'pending_application' || app.status === 'requires_manual';
      }
      return app.status === status;
    }).length;
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)' }}>
      <ScoutSidebar isDark={isDark} setIsDark={setIsDark} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} stats={stats} />

      <main style={{ flex: 1, maxWidth: '980px', margin: '0 auto', width: '100%', padding: '44px 50px 70px', boxSizing: 'border-box' }}>
        {/* Header */}
        <div style={{ marginBottom: '44px' }}>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '34px', fontWeight: 400, color: 'var(--text)', margin: '0 0 8px', letterSpacing: '-0.015em' }}>
            Where things stand
          </h1>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
            <div>
              <p style={{ fontSize: '14px', color: 'var(--muted)', margin: '0 0 4px' }}>
                {filteredApplications.length} of {applications.length} applications
              </p>
              {lastChecked && (
                <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '0 0 8px' }}>
                  Last checked: {getRelativeTime(lastChecked)}
                </p>
              )}
              {checkResult && (
                <p style={{
                  fontSize: '12px',
                  color: checkResult.type === 'success' ? 'var(--color-accent-700)' : checkResult.type === 'error' ? '#cc3333' : 'var(--muted)',
                  margin: 0,
                  animation: 'fadeOut 0.5s ease-in-out 4.5s forwards',
                  transition: 'opacity 0.3s',
                }}>
                  {checkResult.message}
                </p>
              )}
            </div>
            <button
              onClick={handleCheckEmails}
              disabled={checking}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '8.8px calc(13.2px * 1.2)',
                borderRadius: '999px',
                border: 'none',
                background: 'var(--card)',
                color: checking ? 'var(--muted)' : 'var(--color-accent-700)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                fontWeight: 700,
                cursor: checking ? 'not-allowed' : 'pointer',
                boxShadow: 'inset 0 2px 5px rgba(32,30,29,.15)',
                transition: 'all 0.25s',
              }}
              onMouseEnter={(e) => !checking && (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
              onMouseLeave={(e) => !checking && (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.15)')}
            >
              {checking ? 'Checking…' : 'Check emails'}
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div style={{
            padding: '13.2px 17.6px',
            borderRadius: '20px',
            background: 'transparent',
            color: 'var(--color-accent-700)',
            fontSize: '13px',
            marginBottom: '26.4px',
            boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)',
          }}>
            {error}
          </div>
        )}

        {/* Filter Row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '26.4px', gap: '16px' }}>
          <label style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', margin: 0, fontFamily: 'var(--font-body)', fontWeight: 700 }}>
            Filter by Status
          </label>
          {ignoredCount > 0 && (
            <button
              onClick={() => setShowIgnored(!showIgnored)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '8.8px calc(13.2px * 1.2)',
                borderRadius: '999px',
                border: 'none',
                background: 'var(--card)',
                color: showIgnored ? 'var(--color-accent-700)' : 'var(--muted)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'inset 0 2px 5px rgba(32,30,29,.15)',
                transition: 'all 0.25s',
              }}
            >
              {showIgnored ? `Hide ignored (${ignoredCount})` : `Show ignored (${ignoredCount})`}
            </button>
          )}
        </div>

        {/* Status Tabs */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8.8px', marginBottom: '35.2px' }}>
          {allStatuses.map(status => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '7px 12px',
                borderRadius: '999px',
                border: 'none',
                background: statusFilter === status ? 'var(--card)' : 'transparent',
                color: statusFilter === status ? 'var(--color-accent-700)' : 'var(--muted)',
                fontFamily: 'var(--font-body)',
                fontSize: '13px',
                fontWeight: statusFilter === status ? 700 : 400,
                cursor: 'pointer',
                boxShadow: statusFilter === status ? 'inset 0 2px 5px rgba(32,30,29,.15)' : 'none',
                transition: 'all 0.25s',
              }}
            >
              {status === 'all' ? 'All' : getStatusLabel(status)} · {getStatusCount(status)}
            </button>
          ))}
        </div>

        {/* Empty State */}
        {!loading && filteredApplications.length === 0 && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '70px 50px',
            borderRadius: '20px',
            background: 'transparent',
            boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)',
          }}>
            <p style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', color: 'var(--text)', margin: '0 0 8.8px' }}>
              No applications found
            </p>
            <p style={{ fontSize: '13px', color: 'var(--muted)', margin: 0 }}>
              Try adjusting your filters
            </p>
          </div>
        )}

        {/* Loading State */}
        {loading && <ScoutLoading message="Loading applications..." />}

        {/* Applications List */}
        {!loading && filteredApplications.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '13.2px' }}>
            {filteredApplications.map((app, index) => (
              <ApplicationRow key={app.id} application={app} delay={index * 0.04} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

interface ApplicationRowProps {
  application: ApplicationData;
  delay: number;
}

function ApplicationRow({ application, delay }: ApplicationRowProps) {
  const isValidTitle = (title?: string) => {
    if (!title) return false;
    const lower = title.toLowerCase();
    if (title.length > 120) return false;
    if (lower.includes('extract') || lower.includes('not specified') || lower.includes('job title')) return false;
    if (lower.includes('please') || lower.includes('update')) return false;
    return true;
  };

  const displayTitle = isValidTitle(application.job_title) ? application.job_title : 'Unknown Position';

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
  const fitScore = application.fit_score || 0;
  const statusInfo = getStatusColor(application.status);
  const statusLabel = getStatusLabel(application.status);

  const shouldShowApplyButtons = application.status === 'pending_application' || application.status === 'requires_manual';
  const shouldShowApprovalButtons = application.status === 'pending_approval';

  const handleApplyNow = () => {
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
    try {
      await fetch(`http://localhost:8001/api/applications/${application.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        body: JSON.stringify({ status: 'pending_application' }),
      });
      window.location.reload();
    } catch (e) {
      console.error('Failed to approve:', e);
    }
  };

  const handleDismiss = async () => {
    try {
      await fetch(`http://localhost:8001/api/applications/${application.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        body: JSON.stringify({ status: 'ignored' }),
      });
      window.location.reload();
    } catch (e) {
      console.error('Failed to dismiss:', e);
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: '26.4px',
      padding: '17.6px',
      borderRadius: '20px',
      background: 'var(--card)',
      boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)',
      opacity: statusInfo.isClosedOut ? 0.65 : 1,
      transition: 'opacity 0.3s',
      animation: `ainFadeUp 0.5s ease-out forwards`,
      animationDelay: `${Math.min(delay, 0.4)}s`,
    }}>
      {/* Left: Role info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', color: 'var(--text)', margin: '0 0 4.4px', fontWeight: 400 }}>
          {displayTitle}
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '0 0 4.4px' }}>
          {application.job_company || 'Unknown'} {application.job_location ? `· ${application.job_location}` : ''}
        </p>
        {dateStr && (
          <p style={{ fontSize: '11px', color: 'var(--muted)', margin: '0 0 8.8px' }}>
            Found {dateStr}
          </p>
        )}

        {/* Approval Buttons - Bottom Left */}
        {shouldShowApprovalButtons && (
          <div style={{ display: 'flex', flexDirection: 'row', gap: '6px', marginTop: '8.8px' }}>
            <button
              onClick={handleApprove}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                width: 'auto',
                padding: '5px 16px',
                borderRadius: '999px',
                border: 'none',
                background: 'var(--bg)',
                color: '#7a8a5e',
                fontFamily: 'var(--font-body)',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
                transition: 'all 0.25s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(32,30,29,.15)')}
            >
              Approve
            </button>
            <button
              onClick={handleDismiss}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                width: 'auto',
                padding: '5px 16px',
                borderRadius: '999px',
                border: 'none',
                background: 'var(--bg)',
                color: 'var(--muted)',
                fontFamily: 'var(--font-body)',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
                transition: 'all 0.25s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(32,30,29,.15)')}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Apply Buttons - Bottom Left */}
        {shouldShowApplyButtons && (
          <div style={{ display: 'flex', flexDirection: 'row', gap: '6px', marginTop: '8.8px' }}>
            <button
              onClick={handleApplyNow}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                width: 'auto',
                padding: '5px 16px',
                borderRadius: '999px',
                border: 'none',
                background: 'var(--bg)',
                color: '#c67139',
                fontFamily: 'var(--font-body)',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
                transition: 'all 0.25s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(32,30,29,.15)')}
            >
              Apply now
            </button>
            <button
              onClick={handleMarkApplied}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                width: 'auto',
                padding: '5px 16px',
                borderRadius: '999px',
                border: 'none',
                background: 'var(--bg)',
                color: 'var(--muted)',
                fontFamily: 'var(--font-body)',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
                transition: 'all 0.25s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
              onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(32,30,29,.15)')}
            >
              Mark applied
            </button>
          </div>
        )}
      </div>

      {/* Right: Score ring + status label + actions */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8.8px', width: '110px', flexShrink: 0, alignSelf: 'center', marginTop: '8px' }}>
        {/* Progress Ring */}
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          style={{ overflow: 'visible' }}
        >
          {/* Track */}
          <circle
            cx="32"
            cy="32"
            r="26"
            fill="none"
            stroke="var(--track)"
            strokeWidth="6"
          />
          {/* Progress */}
          <circle
            cx="32"
            cy="32"
            r="26"
            fill="none"
            stroke={getScoreRingColor(fitScore)}
            strokeWidth="6"
            strokeDasharray={163.36}
            strokeDashoffset={163.36 * (1 - fitScore / 100)}
            strokeLinecap="round"
            style={{
              transform: 'rotate(-90deg)',
              transformOrigin: '32px 32px',
              transition: 'stroke-dashoffset 0.3s ease',
            }}
          />
          {/* Score text */}
          <text
            x="32"
            y="36"
            textAnchor="middle"
            fontSize="16"
            fontWeight="700"
            fill={getScoreRingColor(fitScore)}
            fontFamily="var(--font-body)"
          >
            {fitScore}
          </text>
        </svg>
      </div>
    </div>
  );
}
