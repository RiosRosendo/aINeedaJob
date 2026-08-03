'use client';

import { useEffect, useState } from 'react';
import { getScoredJobs, getJobs } from '@/lib/api';
import { ScoutSidebar } from '@/components/ScoutSidebar';
import { Job } from '@/lib/types';
import { X, Search } from 'lucide-react';

type DecisionFilter = 'all' | 'apply' | 'review' | 'ignore';
type ModalityFilter = 'all' | 'remote' | 'hybrid' | 'on-site';

const getScoreRingColor = (score: number): string => {
  return score >= 70 ? '#7a8a5e' : '#c67139';
};

const getDecisionColor = (fitScore?: number): { color: string; bgColor: string } => {
  if (!fitScore && fitScore !== 0) return { color: 'var(--muted)', bgColor: 'transparent' };
  if (fitScore >= 85) return { color: 'var(--color-accent-2-800)', bgColor: 'transparent' };
  if (fitScore >= 60) return { color: 'var(--color-accent-700)', bgColor: 'transparent' };
  return { color: 'var(--muted)', bgColor: 'transparent' };
};

export default function JobsPage() {
  const [isDark, setIsDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [priorityCountry, setPriorityCountry] = useState<string | null>(null);

  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>('all');
  const [modalityFilter, setModalityFilter] = useState<ModalityFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showIgnored, setShowIgnored] = useState(false);

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.setAttribute('data-dark', '');
    } else {
      root.removeAttribute('data-dark');
    }
  }, [isDark]);

  useEffect(() => {
    const loadJobs = async () => {
      try {
        setLoading(true);
        setError(null);

        const profileResponse = await fetch('http://localhost:8001/api/users/profile', {
          headers: {
            'x-user-id': localStorage.getItem('user_id') || '',
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
          },
        });
        if (profileResponse.ok) {
          const profile = await profileResponse.json();
          setPriorityCountry(profile.priority_country || null);
        }

        const [scoredData, allJobsData] = await Promise.all([
          getScoredJobs(1000),
          getJobs(1000),
        ]);
        setJobs(scoredData);
        setTotalJobs(allJobsData.length);
      } catch (err) {
        console.error('Failed to load jobs:', err);
        setError('Failed to load jobs. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadJobs();
  }, []);

  const getDecision = (fitScore?: number): 'apply' | 'review' | 'ignore' => {
    if (!fitScore && fitScore !== 0) return 'ignore';
    if (fitScore >= 85) return 'apply';
    if (fitScore >= 60) return 'review';
    return 'ignore';
  };

  const filteredJobs = jobs.filter(job => {
    const decision = getDecision(job.fit_score);

    if (!showIgnored && (!job.fit_score || job.fit_score === 0)) {
      return false;
    }

    if (decisionFilter !== 'all' && decision !== decisionFilter) {
      return false;
    }

    if (modalityFilter !== 'all') {
      const jobModality = (job.modality || 'on-site').toLowerCase();
      if (jobModality !== modalityFilter) {
        return false;
      }
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const titleMatch = (job.title || '').toLowerCase().includes(query);
      const companyMatch = (job.company || '').toLowerCase().includes(query);
      if (!titleMatch && !companyMatch) {
        return false;
      }
    }

    return true;
  });

  const sortedJobs = filteredJobs.sort((a, b) => {
    const aInPriorityCountry = priorityCountry && (a.location || '').includes(priorityCountry);
    const bInPriorityCountry = priorityCountry && (b.location || '').includes(priorityCountry);

    if (aInPriorityCountry && !bInPriorityCountry) return -1;
    if (!aInPriorityCountry && bInPriorityCountry) return 1;

    return (b.fit_score || 0) - (a.fit_score || 0);
  });

  const getDecisionCounts = () => {
    const allJobs = jobs.filter(j => !showIgnored && (!j.fit_score || j.fit_score === 0) ? false : true);
    const applyJobs = allJobs.filter(j => getDecision(j.fit_score) === 'apply').length;
    const reviewJobs = allJobs.filter(j => getDecision(j.fit_score) === 'review').length;
    const ignoreJobs = allJobs.filter(j => getDecision(j.fit_score) === 'ignore').length;
    return { apply: applyJobs, review: reviewJobs, ignore: ignoreJobs };
  };

  const counts = getDecisionCounts();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)' }}>
      <ScoutSidebar isDark={isDark} setIsDark={setIsDark} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      <main style={{ flex: 1, maxWidth: '980px', margin: '0 auto', width: '100%', padding: '44px 50px 70px', boxSizing: 'border-box' }}>
        {/* Header */}
        <div style={{ marginBottom: '44px' }}>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '34px', fontWeight: 400, color: 'var(--text)', margin: '0 0 8px', letterSpacing: '-0.015em' }}>
            All the roles Scout has found
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--muted)', margin: 0 }}>
            {sortedJobs.length} of {jobs.length} scored jobs · {jobs.length} of {totalJobs} total discovered
          </p>
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

        {/* Search Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '10px 16px',
          borderRadius: '999px',
          background: 'transparent',
          boxShadow: 'inset 0 2px 5px rgba(32,30,29,.16)',
          marginBottom: '35.2px',
        }}>
          <Search size={18} style={{ color: 'var(--muted)', flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Search by title or company…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1,
              border: 'none',
              background: 'transparent',
              color: 'var(--text)',
              fontSize: '14px',
              fontFamily: 'var(--font-body)',
              outline: 'none',
            }}
          />
        </div>

        {/* Filters Row */}
        <div style={{ display: 'flex', gap: '44px', marginBottom: '35.2px', flexWrap: 'wrap' }}>
          {/* Decision Filter */}
          <div>
            <label style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', margin: '0 0 8.8px', display: 'block' }}>
              Decision
            </label>
            <div style={{ display: 'flex', gap: '8.8px' }}>
              {(['all', 'apply', 'review', 'ignore'] as DecisionFilter[]).map(option => {
                const isActive = decisionFilter === option;
                let count = 0;
                if (option === 'all') count = filteredJobs.length;
                else if (option === 'apply') count = counts.apply;
                else if (option === 'review') count = counts.review;
                else count = counts.ignore;

                return (
                  <button
                    key={option}
                    onClick={() => setDecisionFilter(option)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      padding: '7px 12px',
                      borderRadius: '999px',
                      border: 'none',
                      background: isActive ? '#fff' : 'transparent',
                      color: isActive ? 'var(--color-accent-700)' : 'var(--muted)',
                      fontFamily: 'var(--font-body)',
                      fontSize: '13px',
                      fontWeight: isActive ? 700 : 400,
                      cursor: 'pointer',
                      boxShadow: isActive ? 'inset 0 2px 5px rgba(32,30,29,.2)' : 'inset 0 1px 3px rgba(32,30,29,.15)',
                      transition: 'all 0.25s',
                    }}
                  >
                    {option.charAt(0).toUpperCase() + option.slice(1)} · {count}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Modality Filter */}
          <div>
            <label style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', margin: '0 0 8.8px', display: 'block' }}>
              Modality
            </label>
            <div style={{ display: 'flex', gap: '8.8px' }}>
              {(['all', 'remote', 'hybrid', 'on-site'] as ModalityFilter[]).map(option => {
                const isActive = modalityFilter === option;
                return (
                  <button
                    key={option}
                    onClick={() => setModalityFilter(option)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      padding: '7px 12px',
                      borderRadius: '999px',
                      border: 'none',
                      background: isActive ? '#fff' : 'transparent',
                      color: isActive ? 'var(--color-accent-700)' : 'var(--muted)',
                      fontFamily: 'var(--font-body)',
                      fontSize: '13px',
                      fontWeight: isActive ? 700 : 400,
                      cursor: 'pointer',
                      boxShadow: isActive ? 'inset 0 2px 5px rgba(32,30,29,.2)' : 'inset 0 1px 3px rgba(32,30,29,.15)',
                      transition: 'all 0.25s',
                    }}
                  >
                    {option.charAt(0).toUpperCase() + option.slice(1)}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Show Ignored Toggle */}
          <div>
            <label style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted)', margin: '0 0 8.8px', display: 'block' }}>
              Filter
            </label>
            <button
              onClick={() => setShowIgnored(!showIgnored)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '7px 12px',
                borderRadius: '999px',
                border: 'none',
                background: showIgnored ? '#fff' : 'transparent',
                color: showIgnored ? 'var(--color-accent-700)' : 'var(--muted)',
                fontFamily: 'var(--font-body)',
                fontSize: '13px',
                fontWeight: showIgnored ? 700 : 400,
                cursor: 'pointer',
                boxShadow: showIgnored ? 'inset 0 2px 5px rgba(32,30,29,.2)' : 'inset 0 1px 3px rgba(32,30,29,.15)',
                transition: 'all 0.25s',
              }}
            >
              <span>{showIgnored ? '✓' : '○'}</span>
              Show ignored
            </button>
          </div>
        </div>

        {/* Empty State */}
        {!loading && sortedJobs.length === 0 && (
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
              No jobs found
            </p>
            <p style={{ fontSize: '13px', color: 'var(--muted)', margin: 0 }}>
              Try adjusting your filters or search query
            </p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
            Loading jobs...
          </div>
        )}

        {/* Jobs List */}
        {!loading && sortedJobs.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '13.2px' }}>
            {sortedJobs.map((job, index) => (
              <JobRow key={job.id} job={job} onViewDetails={() => setSelectedJob(job)} delay={index * 0.04} />
            ))}
          </div>
        )}

        {/* Job Details Modal */}
        {selectedJob && (
          <JobDetailsModal job={selectedJob} onClose={() => setSelectedJob(null)} />
        )}
      </main>
    </div>
  );
}

interface JobRowProps {
  job: Job;
  onViewDetails: () => void;
  delay: number;
}

function JobRow({ job, onViewDetails, delay }: JobRowProps) {
  const getDecision = (fitScore?: number): 'apply' | 'review' | 'ignore' => {
    if (!fitScore && fitScore !== 0) return 'ignore';
    if (fitScore >= 85) return 'apply';
    if (fitScore >= 60) return 'review';
    return 'ignore';
  };

  const decision = getDecision(job.fit_score);
  const fitScore = job.fit_score !== undefined ? Math.round(job.fit_score) : null;
  const location = job.location || 'Location N/A';
  const createdDate = new Date(job.created_at);
  const dateStr = createdDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const getDecisionLabel = (decision: 'apply' | 'review' | 'ignore'): string => {
    switch (decision) {
      case 'apply':
        return 'Apply';
      case 'review':
        return 'Review';
      case 'ignore':
        return 'Ignore';
    }
  };

  const getDecisionColor = (fitScore?: number): string => {
    if (!fitScore && fitScore !== 0) return 'var(--muted)';
    if (fitScore >= 85) return '#7a8a5e';
    if (fitScore >= 60) return '#c67139';
    return 'var(--muted)';
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
      transition: 'opacity 0.3s',
      animation: `ainFadeUp 0.5s ease-out forwards`,
      animationDelay: `${Math.min(delay, 0.4)}s`,
    }}>
      {/* Left: Job Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', color: 'var(--text)', margin: '0 0 4.4px', fontWeight: 400 }}>
          {job.title}
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--muted)', margin: '0 0 4.4px' }}>
          {job.company} · {location}
        </p>
        <p style={{ fontSize: '11px', color: 'var(--muted)', margin: '0 0 8.8px' }}>
          Found {dateStr} · {job.status}
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
          <span style={{
            fontSize: '11px',
            padding: '3px 10px',
            borderRadius: 'calc(16px * 0.75)',
            background: 'transparent',
            color: 'var(--muted)',
            boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
          }}>
            {job.modality || 'unknown'}
          </span>
          <span style={{
            fontSize: '11px',
            padding: '3px 10px',
            borderRadius: 'calc(16px * 0.75)',
            background: 'transparent',
            color: 'var(--muted)',
            boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
          }}>
            {location}
          </span>
        </div>
        {/* View Details Button */}
        <button
          onClick={onViewDetails}
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
            fontSize: '12px',
            cursor: 'pointer',
            boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
            transition: 'all 0.25s',
            marginTop: '8px',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
          onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(32,30,29,.15)')}
        >
          View Details
        </button>
      </div>

      {/* Right: Score Ring + Decision + Button */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8.8px', width: '110px', flexShrink: 0 }}>
        {/* Progress Ring */}
        {fitScore !== null && (
          <>
            <svg width="64" height="64" viewBox="0 0 64 64" style={{ overflow: 'visible' }}>
              <circle cx="32" cy="32" r="26" fill="none" stroke="var(--track)" strokeWidth="6" />
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
              <text x="32" y="37" textAnchor="middle" fill={getScoreRingColor(fitScore)} style={{ fontSize: '18px', fontWeight: '700', fontFamily: 'var(--font-body)' }}>
                {fitScore}
              </text>
            </svg>

            {/* Decision Label */}
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: 'calc(16px * 0.75)',
              background: 'var(--bg)',
              color: getDecisionColor(fitScore),
              fontSize: '13px',
              fontFamily: 'var(--font-heading)',
              boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
            }}>
              {getDecisionLabel(decision)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

interface JobDetailsModalProps {
  job: Job;
  onClose: () => void;
}

function JobDetailsModal({ job, onClose }: JobDetailsModalProps) {
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, []);

  return (
    <>
      {/* Overlay */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,.5)',
          zIndex: 40,
        }}
        onClick={onClose}
      />

      {/* Modal */}
      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '90%',
          maxWidth: '600px',
          maxHeight: '80vh',
          zIndex: 1000,
          padding: '32px',
          borderRadius: '24px',
          backgroundColor: 'var(--card)',
          boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)',
          overflowY: 'auto',
        }}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            padding: '8px',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <X size={20} />
        </button>

        {/* Header */}
        <div style={{ marginBottom: '24px', paddingRight: '32px' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '24px', fontWeight: 400, color: 'var(--text)', margin: '0 0 8px', letterSpacing: '-0.02em' }}>
            {job.title}
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--muted)', margin: '0 0 16px' }}>
            {job.company}
          </p>

          {/* Meta */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--muted)', display: 'block' }}>Location</span>
              <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', margin: '4px 0 0' }}>
                {job.location || 'N/A'}
              </p>
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--muted)', display: 'block' }}>Modality</span>
              <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', margin: '4px 0 0' }}>
                {job.modality || 'Unknown'}
              </p>
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--muted)', display: 'block' }}>Salary</span>
              <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', margin: '4px 0 0' }}>
                {job.salary_min && job.salary_max
                  ? `$${job.salary_min.toLocaleString()}-${job.salary_max.toLocaleString()}`
                  : 'Not specified'}
              </p>
            </div>
            {job.fit_score !== undefined && (
              <div>
                <span style={{ fontSize: '11px', color: 'var(--muted)', display: 'block' }}>Fit Score</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                  <svg width="32" height="32" viewBox="0 0 64 64">
                    <circle cx="32" cy="32" r="26" fill="none" stroke="var(--track)" strokeWidth="6" />
                    <circle
                      cx="32"
                      cy="32"
                      r="26"
                      fill="none"
                      stroke={getScoreRingColor(Math.round(job.fit_score))}
                      strokeWidth="6"
                      strokeDasharray={163.36}
                      strokeDashoffset={163.36 * (1 - job.fit_score / 100)}
                      strokeLinecap="round"
                      style={{
                        transform: 'rotate(-90deg)',
                        transformOrigin: '32px 32px',
                      }}
                    />
                    <text x="32" y="36" textAnchor="middle" fontSize="14" fontWeight="700" fill={getScoreRingColor(Math.round(job.fit_score))} fontFamily="var(--font-body)">
                      {Math.round(job.fit_score)}
                    </text>
                  </svg>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Strengths & Gaps */}
        {(job.strengths || job.gaps) && (
          <div style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid var(--border)' }}>
            {job.strengths && job.strengths.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 8px', color: 'var(--color-accent-2-800)' }}>
                  ✓ Strengths
                </h3>
                <ul style={{ margin: 0, paddingLeft: '16px' }}>
                  {job.strengths.map((strength, i) => (
                    <li key={i} style={{ fontSize: '13px', color: 'var(--muted)', margin: '4px 0' }}>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {job.gaps && job.gaps.length > 0 && (
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 8px', color: 'var(--color-accent-700)' }}>
                  ✗ Gaps
                </h3>
                <ul style={{ margin: 0, paddingLeft: '16px' }}>
                  {job.gaps.map((gap, i) => (
                    <li key={i} style={{ fontSize: '13px', color: 'var(--muted)', margin: '4px 0' }}>
                      {gap}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Skills */}
        {job.required_skills && job.required_skills.length > 0 && (
          <div style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid var(--border)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 12px', color: 'var(--text)' }}>
              Required Skills
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {job.required_skills.map((skill, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: '11px',
                    padding: '4px 12px',
                    borderRadius: 'calc(16px * 0.75)',
                    background: 'transparent',
                    color: 'var(--muted)',
                    boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
                  }}
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Description */}
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 12px', color: 'var(--text)' }}>
            Description
          </h3>
          <p style={{ fontSize: '13px', lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--muted)', margin: 0 }}>
            {job.description_raw || 'No description available'}
          </p>
        </div>
      </div>
    </>
  );
}
