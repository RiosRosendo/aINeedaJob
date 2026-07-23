'use client';

import { useEffect, useState } from 'react';
import { getScoredJobs, getJobs } from '@/lib/api';
import { Job } from '@/lib/types';
import { X, Search } from 'lucide-react';

type DecisionFilter = 'all' | 'apply' | 'review' | 'ignore';
type ModalityFilter = 'all' | 'remote' | 'hybrid' | 'on-site';

export default function JobsPage() {
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
    const loadJobs = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load user profile to get priority country
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

  // Calculate decision from fit score
  const getDecision = (fitScore?: number): 'apply' | 'review' | 'ignore' => {
    if (!fitScore && fitScore !== 0) return 'ignore';
    if (fitScore >= 85) return 'apply';
    if (fitScore >= 60) return 'review';
    return 'ignore';
  };

  // Filter jobs
  const filteredJobs = jobs.filter(job => {
    const decision = getDecision(job.fit_score);

    // Hide jobs with no score or score=0 by default unless showIgnored is true
    if (!showIgnored && (!job.fit_score || job.fit_score === 0)) {
      return false;
    }

    // Decision filter
    if (decisionFilter !== 'all' && decision !== decisionFilter) {
      return false;
    }

    // Modality filter
    if (modalityFilter !== 'all') {
      const jobModality = (job.modality || 'on-site').toLowerCase();
      if (jobModality !== modalityFilter) {
        return false;
      }
    }

    // Search filter
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

  // Sort filtered jobs: priority country first, then by fit_score descending
  const sortedJobs = filteredJobs.sort((a, b) => {
    // Check if jobs are from priority country
    const aInPriorityCountry = priorityCountry && (a.location || '').includes(priorityCountry);
    const bInPriorityCountry = priorityCountry && (b.location || '').includes(priorityCountry);

    // If only one is from priority country, put it first
    if (aInPriorityCountry && !bInPriorityCountry) return -1;
    if (!aInPriorityCountry && bInPriorityCountry) return 1;

    // Otherwise sort by fit_score descending (highest first)
    return (b.fit_score || 0) - (a.fit_score || 0);
  });

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
          All Jobs
        </h1>
        <p style={{ color: 'var(--muted)' }}>
          {sortedJobs.length} of {jobs.length} scored jobs • {jobs.length} of {totalJobs} total discovered
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

      {/* Filters */}
      <div className="mb-8 space-y-4">
        {/* Search */}
        <div
          className="flex items-center gap-3 border rounded-lg px-4 py-3"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <Search size={18} style={{ color: 'var(--muted)' }} />
          <input
            type="text"
            placeholder="Search by title or company..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 outline-none text-sm"
            style={{
              backgroundColor: 'transparent',
              color: 'var(--text)',
            }}
          />
        </div>

        {/* Filter Row */}
        <div className="flex flex-wrap gap-4 items-start">
          {/* Decision Filter */}
          <div>
            <label
              className="text-xs font-semibold uppercase mb-2 block"
              style={{ color: 'var(--faint)' }}
            >
              Decision
            </label>
            <div className="flex gap-2">
              {(['all', 'apply', 'review', 'ignore'] as DecisionFilter[]).map(
                (option) => (
                  <button
                    key={option}
                    onClick={() => setDecisionFilter(option)}
                    className="px-3 py-2 rounded-lg text-xs font-medium transition-all"
                    style={{
                      backgroundColor:
                        decisionFilter === option ? 'var(--primary-bg)' : 'var(--card)',
                      color:
                        decisionFilter === option ? 'var(--primary-text)' : 'var(--muted)',
                      borderColor: 'var(--border)',
                      border: '1px solid',
                    }}
                  >
                    {option.charAt(0).toUpperCase() + option.slice(1)}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Modality Filter */}
          <div>
            <label
              className="text-xs font-semibold uppercase mb-2 block"
              style={{ color: 'var(--faint)' }}
            >
              Modality
            </label>
            <div className="flex gap-2">
              {(['all', 'remote', 'hybrid', 'on-site'] as ModalityFilter[]).map(
                (option) => (
                  <button
                    key={option}
                    onClick={() => setModalityFilter(option)}
                    className="px-3 py-2 rounded-lg text-xs font-medium transition-all"
                    style={{
                      backgroundColor:
                        modalityFilter === option ? 'var(--primary-bg)' : 'var(--card)',
                      color:
                        modalityFilter === option ? 'var(--primary-text)' : 'var(--muted)',
                      borderColor: 'var(--border)',
                      border: '1px solid',
                    }}
                  >
                    {option.charAt(0).toUpperCase() + option.slice(1)}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Show Ignored Toggle */}
          <div className="pt-6">
            <button
              onClick={() => setShowIgnored(!showIgnored)}
              className="px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2"
              style={{
                backgroundColor: showIgnored ? 'var(--border)' : 'var(--card)',
                color: 'var(--muted)',
                borderColor: 'var(--border)',
                border: '1px solid',
              }}
            >
              <span>{showIgnored ? '✓' : '○'}</span>
              Show ignored
            </button>
          </div>
        </div>
      </div>

      {/* Jobs List */}
      {loading ? (
        <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '40px' }}>
          Loading jobs...
        </div>
      ) : sortedJobs.length === 0 ? (
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
          <p className="text-lg">No jobs found</p>
          <p className="text-sm mt-2">Try adjusting your filters or search query</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sortedJobs.map((job, index) => (
            <JobRow
              key={job.id}
              job={job}
              onViewDetails={() => setSelectedJob(job)}
              delay={index * 0.02}
            />
          ))}
        </div>
      )}

      {/* Job Details Modal */}
      {selectedJob && (
        <JobDetailsModal job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
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

  const getScoreColor = (score?: number) => {
    if (!score && score !== 0) return '#9ca3af';
    if (score >= 85) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const decision = getDecision(job.fit_score);
  const fitScore = job.fit_score !== undefined ? Math.round(job.fit_score) : null;
  const location = job.location ? job.location : 'Location N/A';
  const createdDate = new Date(job.created_at);
  const dateStr = createdDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });

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
        {/* Left: Title and Company */}
        <div className="flex-1 min-w-0">
          <h3
            className="font-semibold text-sm mb-1 truncate"
            style={{
              color: 'var(--text)',
              letterSpacing: '-0.01em',
            }}
          >
            {job.title}
          </h3>
          <p
            className="text-xs mb-3"
            style={{ color: 'var(--muted)' }}
          >
            {job.company}
          </p>
          <div className="flex flex-wrap gap-2">
            {/* Modality */}
            <span
              className="text-xs px-2 py-1 rounded-full border"
              style={{
                borderColor: 'var(--border)',
                color: 'var(--muted)',
              }}
            >
              {job.modality || 'unknown'}
            </span>

            {/* Location */}
            <span
              className="text-xs px-2 py-1 rounded-full border"
              style={{
                borderColor: 'var(--border)',
                color: 'var(--muted)',
              }}
            >
              {location}
            </span>

            {/* Status */}
            <span
              className="text-xs px-2 py-1 rounded-full border"
              style={{
                borderColor: 'var(--border)',
                color: 'var(--faint)',
              }}
            >
              {job.status}
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

        {/* Middle: Fit Score */}
        {fitScore !== null && (
          <div
            className="flex flex-col items-center justify-center flex-shrink-0"
            style={{
              minWidth: '60px',
            }}
          >
            <div
              className="relative w-12 h-12 flex items-center justify-center rounded-full border-2"
              style={{
                borderColor: getScoreColor(job.fit_score),
                backgroundColor: 'var(--bg)',
              }}
            >
              <span
                className="text-sm font-bold"
                style={{ color: getScoreColor(job.fit_score) }}
              >
                {fitScore}
              </span>
            </div>
            <span
              className="text-xs mt-1"
              style={{
                color: 'var(--faint)',
              }}
            >
              {decision.charAt(0).toUpperCase() + decision.slice(1)}
            </span>
          </div>
        )}

        {/* Right: Button */}
        <button
          onClick={onViewDetails}
          className="px-4 py-2 rounded-lg text-xs font-medium flex-shrink-0 transition-all"
          style={{
            backgroundColor: 'var(--sidebar-active)',
            color: 'var(--muted)',
            border: '1px solid var(--border)',
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.backgroundColor = 'var(--border)';
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.backgroundColor = 'var(--sidebar-active)';
          }}
        >
          View Details
        </button>
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
    // Disable body scroll when modal is open
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, []);

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
        style={{ animation: 'fadeIn 0.2s ease-in-out' }}
      />

      {/* Modal */}
      <div
        className="border rounded-2xl overflow-y-auto"
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
          borderColor: 'var(--border)',
          backgroundColor: 'var(--card)',
          animation: 'slideUp 0.3s ease-out',
        }}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 hover:bg-opacity-20 transition-all"
          style={{
            color: 'var(--muted)',
          }}
        >
          <X size={20} />
        </button>

        {/* Header */}
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

          {/* Meta */}
          <div className="flex flex-wrap gap-4">
            <div>
              <span
                className="text-xs"
                style={{ color: 'var(--faint)' }}
              >
                Location
              </span>
              <p
                className="text-sm font-medium"
                style={{ color: 'var(--text)' }}
              >
                {job.location || 'N/A'}
              </p>
            </div>
            <div>
              <span
                className="text-xs"
                style={{ color: 'var(--faint)' }}
              >
                Modality
              </span>
              <p
                className="text-sm font-medium"
                style={{ color: 'var(--text)' }}
              >
                {job.modality || 'Unknown'}
              </p>
            </div>
            <div>
              <span
                className="text-xs"
                style={{ color: 'var(--faint)' }}
              >
                Salary
              </span>
              <p
                className="text-sm font-medium"
                style={{ color: 'var(--text)' }}
              >
                {job.salary_min && job.salary_max
                  ? `$${job.salary_min.toLocaleString()}-${job.salary_max.toLocaleString()}`
                  : 'Not specified'}
              </p>
            </div>
            {job.fit_score !== undefined && (
              <div>
                <span
                  className="text-xs"
                  style={{ color: 'var(--faint)' }}
                >
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

        {/* Strengths & Gaps */}
        {(job.strengths || job.gaps) && (
          <div className="mb-6 pb-6 border-b" style={{ borderColor: 'var(--border)' }}>
            {job.strengths && job.strengths.length > 0 && (
              <div className="mb-4">
                <h3
                  className="text-sm font-semibold mb-2"
                  style={{ color: '#10b981' }}
                >
                  ✓ Strengths
                </h3>
                <ul className="space-y-1">
                  {job.strengths.map((strength, i) => (
                    <li
                      key={i}
                      className="text-xs"
                      style={{ color: 'var(--muted)' }}
                    >
                      • {strength}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {job.gaps && job.gaps.length > 0 && (
              <div>
                <h3
                  className="text-sm font-semibold mb-2"
                  style={{ color: '#ef4444' }}
                >
                  ✗ Gaps
                </h3>
                <ul className="space-y-1">
                  {job.gaps.map((gap, i) => (
                    <li
                      key={i}
                      className="text-xs"
                      style={{ color: 'var(--muted)' }}
                    >
                      • {gap}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Skills */}
        {job.required_skills && job.required_skills.length > 0 && (
          <div className="mb-6 pb-6 border-b" style={{ borderColor: 'var(--border)' }}>
            <h3
              className="text-sm font-semibold mb-3"
              style={{ color: 'var(--text)' }}
            >
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

        {/* Description */}
        <div>
          <h3
            className="text-sm font-semibold mb-3"
            style={{ color: 'var(--text)' }}
          >
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
