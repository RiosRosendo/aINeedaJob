'use client';

import { useEffect, useState } from 'react';
import { Sun, Moon, RotateCw, X } from 'lucide-react';
import { getUserProfile, getJobsWithStats, getAgentLogs, getPendingApprovalJobs } from '@/lib/api';
import { Job, UserProfile, DashboardStats } from '@/lib/types';

interface ActivityLog {
  id: string;
  agent: string;
  status: string;
  details?: any;
  created_at: string;
  job_id?: string;
  fit_score?: number;
  decision?: string;
}

export default function Dashboard() {
  const [isDark, setIsDark] = useState(true);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    jobs_found: 0,
    applied: 0,
    interviews: 0,
    needs_approval: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [profileData, jobsData, logs, pendingJobs] = await Promise.all([
          getUserProfile().catch(err => {
            console.error('Profile fetch error:', err);
            return null;
          }),
          getJobsWithStats().catch(err => {
            console.error('Jobs fetch error:', err);
            throw err;
          }),
          getAgentLogs(5).catch(err => {
            console.error('Agent logs fetch error:', err);
            return [];
          }),
          getPendingApprovalJobs().catch(err => {
            console.error('Pending jobs fetch error:', err);
            return [];
          }),
        ]);

        setProfile(profileData);
        setJobs(pendingJobs);
        setActivityLogs(logs);
        setStats(jobsData.stats);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
        setError('Failed to load dashboard data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const toggleTheme = () => {
    setIsDark(!isDark);
    if (isDark) {
      document.documentElement.classList.add('theme-light');
    } else {
      document.documentElement.classList.remove('theme-light');
    }
  };

  // Format activity logs for display
  const formatActivityEvents = (logs: ActivityLog[]) => {
    return logs
      .filter(log => {
        // Hide job_match events with score=0 or no score
        if (log.agent === 'job_match' && log.status === 'success') {
          const score = log.fit_score !== undefined ? log.fit_score : (log.details?.score !== undefined ? log.details.score : 0);
          if (score === 0) return false;
        }
        return true;
      })
      .map((log, index) => {
        const agentName = log.agent?.toUpperCase() || 'Agent';
        const status = log.status || 'completed';
        const details = log.details || {};
        let title = `${agentName} - ${status}`;

        if (log.agent === 'job_discovery' && log.status === 'success') {
          title = `Found ${details.jobs_count || 'new'} roles matching your profile`;
        } else if (log.agent === 'job_parsing' && log.status === 'success') {
          const jobTitle = details.title ? details.title.substring(0, 40) : 'Job';
          title = `Parsed job: ${jobTitle}`;
        } else if (log.agent === 'job_match' && log.status === 'success') {
          // Use fit_score from the joined fit_scores table, not from details
          const score = log.fit_score !== undefined ? log.fit_score : (details.score !== undefined ? details.score : '?');
          const decision = log.decision || details.decision || 'pending';
          title = `Scored job - ${score}% fit (${decision})`;
        } else if (log.agent === 'job_match' && log.status === 'failed') {
          title = 'Failed to score job';
        }

        const createdAt = new Date(log.created_at);
        const now = new Date();
        const diffMs = now.getTime() - createdAt.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        let timestamp = 'just now';

        if (diffMins < 1) {
          timestamp = 'just now';
        } else if (diffMins < 60) {
          timestamp = `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
          timestamp = `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        } else {
          timestamp = createdAt.toLocaleDateString();
        }

        return {
          type: index === 0 ? ('latest' as const) : (undefined as any),
          title,
          timestamp,
        };
      });
  };

  const activityEvents = activityLogs.length > 0 ? formatActivityEvents(activityLogs) : [
    {
      type: 'latest' as const,
      title: 'No activity yet',
      timestamp: 'Start a job search to see activity',
    },
  ];

  const greeting = profile?.name ? `Good morning, ${profile.name.split(' ')[0]}` : 'Good morning';
  const today = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date());

  return (
    <div>
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
      {/* Header */}
      <header className="flex items-start justify-between mb-10">
        <div>
          <h1
            className="text-4xl font-semibold mb-2"
            style={{
              letterSpacing: '-0.03em',
              color: 'var(--text)',
            }}
          >
            {greeting}
          </h1>
          <p
            className="text-sm"
            style={{ color: 'var(--muted)', fontWeight: 450 }}
          >
            {today}
          </p>
        </div>

        {/* Theme toggle & scan info */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={toggleTheme}
            className="w-9 h-9 flex items-center justify-center border rounded-lg transition-all"
            style={{
              borderColor: 'var(--border)',
              backgroundColor: 'var(--card)',
              color: 'var(--muted)',
            }}
            title="Toggle theme"
          >
            {isDark ? <Sun size={15} /> : <Moon size={15} />}
          </button>

          <div
            className="flex items-center gap-2 border rounded-lg px-3 py-2 text-xs h-9"
            style={{
              borderColor: 'var(--border)',
              backgroundColor: 'var(--card)',
              color: 'var(--muted)',
            }}
          >
            <RotateCw size={13} style={{ color: 'var(--faint)' }} />
            Last scan: 2 minutes ago
          </div>
        </div>
      </header>

      {/* Stats Row */}
      <section className="grid grid-cols-4 gap-4 mb-10">
        <StatCard label="Jobs Found" value={stats.jobs_found} />
        <StatCard label="Applied" value={stats.applied} showDivider />
        <StatCard label="Interviews" value={stats.interviews} showDivider />
        <StatCard label="Needs Approval" value={stats.needs_approval} showDivider showDot />
      </section>

      {/* Agent Activity */}
      <section className="mb-11">
        <div className="flex items-center justify-between mb-5">
          <h2
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: 'var(--muted)' }}
          >
            Agent Activity
          </h2>
          <a
            href="#"
            className="text-xs font-medium"
            style={{ color: 'var(--accent)' }}
          >
            View all activity →
          </a>
        </div>

        <div className="relative">
          {/* Timeline line - centered through dots */}
          <div
            className="absolute left-1.5 top-4 bottom-4 w-0.5"
            style={{ backgroundColor: 'var(--border)', transform: 'translateX(-50%)' }}
          />

          {/* Activity items */}
          <div className="space-y-3">
            {activityEvents.map((event, i) => (
              <div key={i} className="relative flex pl-10 py-1.5 animate-slide-left"
                style={{ animationDelay: `${0.04 + i * 0.08}s` }}>
                {/* Node */}
                <div
                  className="absolute left-0 top-3.5 w-3 h-3 rounded-full flex-shrink-0"
                  style={
                    event.type === 'latest'
                      ? {
                        backgroundColor: 'var(--text)',
                        boxShadow: '0 0 0 4px var(--accent-bg)',
                      }
                      : {
                        backgroundColor: 'var(--bg)',
                        border: '1.5px solid var(--border-strong)',
                      }
                  }
                />

                {/* Content */}
                <div>
                  <div
                    className="text-sm font-medium"
                    style={{
                      color: event.type === 'latest' ? 'var(--text)' : 'var(--muted)',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {event.title.split(' — ').map((part, j) => (
                      <span key={j}>
                        {j === 1 ? (
                          <span style={{ color: 'var(--text)', fontWeight: 500 }}>
                            {part}
                          </span>
                        ) : (
                          part
                        )}
                        {j === 0 && ' — '}
                      </span>
                    ))}
                  </div>
                  <div
                    className="text-xs mt-0.5"
                    style={{ color: 'var(--faint)' }}
                  >
                    {event.timestamp}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Jobs Queue */}
      <section>
        <div className="flex items-center justify-between mb-5">
          <h2
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: 'var(--muted)' }}
          >
            Jobs Queue
          </h2>
          <span
            className="text-xs"
            style={{ color: 'var(--faint)' }}
          >
            3 awaiting review
          </span>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {jobs.length > 0 ? (
            jobs.map((job, i) => (
              <JobCard
                key={job.id}
                job={job}
                delay={0.06 + i * 0.1}
                onViewDetails={() => setSelectedJob(job)}
              />
            ))
          ) : (
            <>
              <JobCardSkeleton />
              <JobCardSkeleton />
              <JobCardSkeleton />
            </>
          )}
        </div>
      </section>

      {/* Job Details Modal */}
      {selectedJob && (
        <JobDetailsModal job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  showDivider = false,
  showDot = false,
}: {
  label: string;
  value: number;
  showDivider?: boolean;
  showDot?: boolean;
}) {
  return (
    <div
      style={{
        paddingLeft: showDivider ? '24px' : 0,
        borderLeft: showDivider ? '1px solid var(--border-soft)' : 'none',
      }}
    >
      <div className="flex items-center gap-2 mb-3.5">
        {showDot && (
          <div
            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: 'var(--accent)' }}
          />
        )}
        <label
          className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: 'var(--faint)' }}
        >
          {label}
        </label>
      </div>
      <div
        className="text-4xl font-semibold"
        style={{
          letterSpacing: '-0.03em',
          color: 'var(--text)',
          lineHeight: 1,
        }}
      >
        {value}
      </div>
    </div>
  );
}

interface JobCardProps {
  job: Job;
  delay: number;
  onViewDetails?: () => void;
}

function JobCard({ job, delay, onViewDetails }: JobCardProps) {
  // Calculate stroke dashoffset based on fit score (0-100)
  // Full circle = 163.36, so offset = (100 - score) * 1.6336
  const fitScore = Math.round(job.fit_score || 75);
  const dashOffset = (100 - fitScore) * 1.6336;
  const location = job.location ? job.location.split(',')[0] : 'Location N/A';

  return (
    <div
      className="border rounded-2xl p-6 card-shadow hover:card-shadow-hover transition-all animate-fade-up hover:scale-101 hover:-translate-y-1.5"
      style={{
        borderColor: 'var(--border)',
        backgroundColor: 'var(--card)',
        animationDelay: `${delay}s`,
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.transform = 'translateY(-6px) scale(1.012)';
        el.style.boxShadow = 'var(--card-shadow-hover)';
        el.style.borderColor = 'var(--border-strong)';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.transform = 'translateY(0) scale(1)';
        el.style.boxShadow = 'var(--card-shadow)';
        el.style.borderColor = 'var(--border)';
      }}
    >
      {/* Top row: Company/Title + Score Ring */}
      <div className="flex items-start justify-between mb-4.5">
        <div>
          <div
            className="text-xs font-medium mb-0.5"
            style={{ color: 'var(--faint)' }}
          >
            {job.company}
          </div>
          <div
            className="text-base font-semibold"
            style={{
              color: 'var(--text)',
              letterSpacing: '-0.02em',
              lineHeight: 1.3,
            }}
          >
            {job.title}
          </div>
        </div>

        {/* Fit Score Ring */}
        <div className="relative w-14 h-14 flex-shrink-0">
          <svg
            width="56"
            height="56"
            viewBox="0 0 64 64"
            style={{ transform: 'rotate(-90deg)' }}
          >
            <circle
              cx="32"
              cy="32"
              r="26"
              fill="none"
              stroke="var(--track)"
              strokeWidth="5"
            />
            <circle
              cx="32"
              cy="32"
              r="26"
              fill="none"
              stroke="var(--ring)"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray="163.36"
              strokeDashoffset={dashOffset}
              style={{
                transition: 'stroke-dashoffset 1.1s cubic-bezier(0.2, 0.8, 0.2, 1)',
              }}
            />
          </svg>
          <div
            className="absolute inset-0 flex items-center justify-center text-sm font-semibold"
            style={{ color: 'var(--text)' }}
          >
            {fitScore}
          </div>
        </div>
      </div>

      {/* Modality pill */}
      <div className="flex items-center gap-2 mb-5">
        <span
          className="text-xs font-medium border rounded-full px-3 py-1.5"
          style={{
            color: 'var(--muted)',
            borderColor: 'var(--border)',
          }}
        >
          {job.modality}
        </span>
        <span
          className="text-xs"
          style={{ color: 'var(--faint)' }}
        >
          Fit score
        </span>
      </div>

      {/* Buttons */}
      <div className="flex gap-2">
        <button
          onClick={onViewDetails}
          className="flex-1 text-xs font-medium py-2.5 border rounded-xl transition-all"
          style={{
            color: 'var(--muted)',
            backgroundColor: 'var(--card)',
            borderColor: 'var(--border)',
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.backgroundColor = 'var(--sidebar-active)';
            el.style.borderColor = 'var(--border-strong)';
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.backgroundColor = 'var(--card)';
            el.style.borderColor = 'var(--border)';
          }}
        >
          View Details
        </button>
        <button
          className="flex-1 text-xs font-semibold py-2.5 border rounded-xl transition-all"
          style={{
            color: 'var(--primary-text)',
            backgroundColor: 'var(--primary-bg)',
            borderColor: 'var(--primary-bg)',
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.backgroundColor = 'var(--primary-hover)';
            el.style.borderColor = 'var(--primary-hover)';
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.backgroundColor = 'var(--primary-bg)';
            el.style.borderColor = 'var(--primary-bg)';
          }}
        >
          Approve
        </button>
      </div>
    </div>
  );
}

function JobCardSkeleton() {
  return (
    <div
      className="border rounded-2xl p-6 card-shadow"
      style={{
        borderColor: 'var(--border)',
        backgroundColor: 'var(--card)',
      }}
    >
      <div className="space-y-4">
        <div className="w-24 h-4 skeleton-block" />
        <div className="w-full h-6 skeleton-block" />
        <div className="w-32 h-4 skeleton-block" />
        <div className="flex gap-2 mt-5">
          <div className="flex-1 h-9 skeleton-block" />
          <div className="flex-1 h-9 skeleton-block" />
        </div>
      </div>
    </div>
  );
}

interface JobDetailsModalProps {
  job: Job;
  onClose: () => void;
}

function JobDetailsModal({ job, onClose }: JobDetailsModalProps) {
  const getScoreColor = (score?: number) => {
    if (!score && score !== 0) return '#9ca3af';
    if (score >= 85) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, []);

  return (
    <>
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
        style={{ animation: 'fadeIn 0.2s ease-in-out' }}
      />

      <div
        className="fixed inset-4 md:inset-auto md:left-1/2 md:top-1/2 md:w-2/3 md:max-w-2xl border rounded-2xl p-8 overflow-y-auto z-50"
        style={{
          borderColor: 'var(--border)',
          backgroundColor: 'var(--card)',
          transform: 'md:translate(-50%, -50%)',
          maxHeight: '90vh',
          animation: 'slideUp 0.3s ease-out',
        }}
      >
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 hover:bg-opacity-20 transition-all"
          style={{
            color: 'var(--muted)',
          }}
        >
          <X size={20} />
        </button>

        <div className="mb-6 pr-10">
          <h2
            className="text-2xl font-semibold mb-2"
            style={{
              color: 'var(--text)',
              letterSpacing: '-0.02em',
            }}
          >
            {job.title}
          </h2>
          <p
            className="text-sm mb-4"
            style={{ color: 'var(--muted)' }}
          >
            {job.company}
          </p>

          <div className="flex flex-wrap gap-4">
            <div>
              <span className="text-xs" style={{ color: 'var(--faint)' }}>
                Location
              </span>
              <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                {job.location || 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-xs" style={{ color: 'var(--faint)' }}>
                Modality
              </span>
              <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                {job.modality || 'Unknown'}
              </p>
            </div>
            {job.fit_score !== undefined && (
              <div>
                <span className="text-xs" style={{ color: 'var(--faint)' }}>
                  Fit Score
                </span>
                <div className="flex items-center gap-2">
                  <div
                    className="w-8 h-8 rounded-full border-2 flex items-center justify-center"
                    style={{
                      borderColor: getScoreColor(job.fit_score),
                      backgroundColor: 'var(--bg)',
                    }}
                  >
                    <span
                      className="text-xs font-bold"
                      style={{ color: getScoreColor(job.fit_score) }}
                    >
                      {Math.round(job.fit_score)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {(job.strengths || job.gaps) && (
          <div className="mb-6 pb-6 border-b" style={{ borderColor: 'var(--border)' }}>
            {job.strengths && job.strengths.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold mb-2" style={{ color: '#10b981' }}>
                  ✓ Strengths
                </h3>
                <ul className="space-y-1">
                  {job.strengths.map((strength, i) => (
                    <li key={i} className="text-xs" style={{ color: 'var(--muted)' }}>
                      • {strength}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {job.gaps && job.gaps.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-2" style={{ color: '#ef4444' }}>
                  ✗ Gaps
                </h3>
                <ul className="space-y-1">
                  {job.gaps.map((gap, i) => (
                    <li key={i} className="text-xs" style={{ color: 'var(--muted)' }}>
                      • {gap}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {job.required_skills && job.required_skills.length > 0 && (
          <div className="mb-6 pb-6 border-b" style={{ borderColor: 'var(--border)' }}>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text)' }}>
              Required Skills
            </h3>
            <div className="flex flex-wrap gap-2">
              {job.required_skills.map((skill, i) => (
                <span
                  key={i}
                  className="text-xs px-3 py-1.5 rounded-full border"
                  style={{
                    borderColor: 'var(--border)',
                    color: 'var(--muted)',
                  }}
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text)' }}>
            Description
          </h3>
          <p
            className="text-sm leading-relaxed whitespace-pre-wrap"
            style={{ color: 'var(--muted)' }}
          >
            {job.description_raw || 'No description available'}
          </p>
        </div>
      </div>
    </>
  );
}
