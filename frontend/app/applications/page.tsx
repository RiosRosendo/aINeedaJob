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
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<ApplicationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    const loadApplications = async () => {
      try {
        setLoading(true);
        setError(null);

        const apps = await getApplications(100);
        setApplications(apps);
      } catch (err) {
        console.error('Failed to load applications:', err);
        setError('Failed to load applications. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadApplications();
  }, []);

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
      case 'in_review':
        return 'In Review';
      default:
        return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };

  // Filter applications
  const filteredApplications = applications.filter(item => {
    if (statusFilter === 'all') return true;
    return item?.application?.status === statusFilter || item?.status === statusFilter;
  });

  const statuses = ['all', 'applied', 'interview', 'offer', 'rejected', 'ignored', 'pending_approval', 'in_review'];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
          Applications
        </h1>
        <p style={{ color: 'var(--muted)' }}>
          {filteredApplications.length} of {applications.length} applications
        </p>
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
        <label
          className="text-xs font-semibold uppercase mb-3 block"
          style={{ color: 'var(--faint)' }}
        >
          Filter by Status
        </label>
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
      case 'in_review':
        return 'In Review';
      default:
        return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };

  const createdDate = application?.created_at ? new Date(application.created_at) : new Date();
  const dateStr = createdDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: createdDate.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
  });

  const jobTitle = application?.job_title || 'Unknown Job';
  const company = application?.job_company || 'Unknown Company';
  const status = application?.status || 'unknown';

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
          <h3
            className="font-semibold text-sm mb-1 truncate"
            style={{
              color: 'var(--text)',
              letterSpacing: '-0.01em',
            }}
          >
            {jobTitle}
          </h3>
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
        </div>
      </div>
    </div>
  );
}
