'use client';

import { useEffect, useState } from 'react';
import { getApplications, getJob, approveApplication, dismissApplication } from '@/lib/api';
import { Application, Job } from '@/lib/types';

interface PendingJob {
  application: Application;
  job: Job;
}

export default function ApprovalsPage() {
  const [pendingJobs, setPendingJobs] = useState<PendingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPendingJobs = async () => {
    try {
      setLoading(true);
      setError(null);

      const applications = await getApplications(100);
      const pending = applications.filter(app => app.status === 'pending_approval');

      const jobsData: PendingJob[] = [];
      for (const app of pending) {
        try {
          const jobData = await getJob(app.job_id);
          jobsData.push({
            application: app,
            job: jobData.job || jobData,
          });
        } catch (err) {
          console.error(`Failed to fetch job ${app.job_id}:`, err);
        }
      }

      setPendingJobs(jobsData);
    } catch (err) {
      console.error('Failed to load pending jobs:', err);
      setError('Failed to load pending jobs. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPendingJobs();
  }, []);

  const handleApprove = async (applicationId: string) => {
    try {
      await approveApplication(applicationId);
      await loadPendingJobs();
    } catch (err) {
      console.error('Failed to approve application:', err);
      setError('Failed to approve. Please try again.');
    }
  };

  const handleDismiss = async (applicationId: string) => {
    try {
      await dismissApplication(applicationId);
      await loadPendingJobs();
    } catch (err) {
      console.error('Failed to dismiss application:', err);
      setError('Failed to dismiss. Please try again.');
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
        Pending Approvals
      </h1>
      <p className="mb-8" style={{ color: 'var(--muted)' }}>
        Jobs that need your approval (fit score 60-84)
      </p>

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

      {loading ? (
        <div style={{ color: 'var(--muted)' }}>Loading...</div>
      ) : pendingJobs.length === 0 ? (
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
          <p className="text-lg">No pending approvals</p>
          <p className="text-sm mt-2">All your job reviews are up to date!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {pendingJobs.map((item, index) => (
            <ApprovalCard
              key={item.application.id}
              application={item.application}
              job={item.job}
              onApprove={handleApprove}
              onDismiss={handleDismiss}
              delay={index * 0.08}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface ApprovalCardProps {
  application: Application;
  job: Job;
  onApprove: (id: string) => void;
  onDismiss: (id: string) => void;
  delay: number;
}

function ApprovalCard({
  application,
  job,
  onApprove,
  onDismiss,
  delay,
}: ApprovalCardProps) {
  const [isApproving, setIsApproving] = useState(false);
  const [isDismissing, setIsDismissing] = useState(false);

  const handleApproveClick = async () => {
    setIsApproving(true);
    try {
      await onApprove(application.id);
    } finally {
      setIsApproving(false);
    }
  };

  const handleDismissClick = async () => {
    setIsDismissing(true);
    try {
      await onDismiss(application.id);
    } finally {
      setIsDismissing(false);
    }
  };

  const fitScore = Math.round(job.fit_score || 75);
  const getScoreColor = (score: number) => {
    if (score >= 80) return '#10b981'; // green
    if (score >= 70) return '#f59e0b'; // amber
    if (score >= 60) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const location = job.location ? job.location.split(',')[0] : 'Location N/A';

  return (
    <div
      className="border rounded-2xl p-6 animate-fade-up hover:shadow-lg transition-all"
      style={{
        borderColor: 'var(--border)',
        backgroundColor: 'var(--card)',
        animationDelay: `${delay}s`,
      }}
    >
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start mb-4">
        {/* Job Info */}
        <div className="md:col-span-2">
          <h3
            className="text-lg font-semibold mb-1"
            style={{
              color: 'var(--text)',
              letterSpacing: '-0.02em',
            }}
          >
            {job.title}
          </h3>
          <p
            className="text-sm mb-3"
            style={{ color: 'var(--muted)' }}
          >
            {job.company}
          </p>
          <div className="flex flex-wrap gap-3">
            <span
              className="text-xs px-2 py-1 border rounded-full"
              style={{
                borderColor: 'var(--border)',
                color: 'var(--muted)',
              }}
            >
              {job.modality || 'unknown'}
            </span>
            <span
              className="text-xs px-2 py-1 border rounded-full"
              style={{
                borderColor: 'var(--border)',
                color: 'var(--muted)',
              }}
            >
              {location}
            </span>
          </div>
        </div>

        {/* Fit Score */}
        <div className="flex flex-col items-center justify-center">
          <div
            className="relative w-16 h-16 flex items-center justify-center"
            style={{
              borderRadius: '50%',
              border: `4px solid ${getScoreColor(fitScore)}`,
              backgroundColor: 'var(--bg)',
            }}
          >
            <div
              style={{
                fontSize: '20px',
                fontWeight: 'bold',
                color: getScoreColor(fitScore),
              }}
            >
              {fitScore}
            </div>
          </div>
          <p
            className="text-xs mt-2 text-center"
            style={{ color: 'var(--faint)' }}
          >
            Fit Score
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <button
            onClick={handleApproveClick}
            disabled={isApproving || isDismissing}
            className="px-4 py-2 rounded-lg font-medium text-sm transition-all"
            style={{
              backgroundColor: '#10b981',
              color: 'white',
              opacity: isApproving || isDismissing ? 0.6 : 1,
              cursor: isApproving || isDismissing ? 'not-allowed' : 'pointer',
            }}
          >
            {isApproving ? 'Approving...' : 'Approve'}
          </button>
          <button
            onClick={handleDismissClick}
            disabled={isApproving || isDismissing}
            className="px-4 py-2 rounded-lg font-medium text-sm transition-all"
            style={{
              backgroundColor: 'var(--border)',
              color: 'var(--muted)',
              opacity: isApproving || isDismissing ? 0.6 : 1,
              cursor: isApproving || isDismissing ? 'not-allowed' : 'pointer',
            }}
          >
            {isDismissing ? 'Dismissing...' : 'Dismiss'}
          </button>
        </div>
      </div>

      {/* Description snippet */}
      {job.description_raw && (
        <p
          className="text-sm line-clamp-2"
          style={{ color: 'var(--faint)' }}
        >
          {job.description_raw.substring(0, 200)}...
        </p>
      )}
    </div>
  );
}
