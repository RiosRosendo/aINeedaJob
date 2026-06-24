'use client';

import { useEffect, useState } from 'react';
import { getJobs } from '@/lib/api';
import { Job } from '@/lib/types';
import { X, Search } from 'lucide-react';

type DecisionFilter = 'all' | 'apply' | 'review' | 'ignore';
type ModalityFilter = 'all' | 'remote' | 'hybrid' | 'on-site';

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>('all');
  const [modalityFilter, setModalityFilter] = useState<ModalityFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  useEffect(() => {
    const loadJobs = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getJobs(1000);
        setJobs(data);
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

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
          All Jobs
        </h1>
        <p style={{ color: 'var(--muted)' }}>
          {filteredJobs.length} of {jobs.length} jobs found
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
        <div className="flex flex-wrap gap-4">
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
        </div>
      </div>

      {/* Jobs List */}
      {loading ? (
        <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '40px' }}>
          Loading jobs...
        </div>
      ) : filteredJobs.length === 0 ? (
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
          {filteredJobs.map((job, index) => (
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
  const location = job.location ? job.location.split(',')[0] : 'Location N/A';
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
        className="fixed inset-4 md:inset-auto md:left-1/2 md:top-1/2 md:w-2/3 md:max-w-2xl border rounded-2xl p-8 overflow-y-auto z-50"
        style={{
          borderColor: 'var(--border)',
          backgroundColor: 'var(--card)',
          transform: 'md:translate(-50%, -50%)',
          maxHeight: '90vh',
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
          <div className="flex flex-wrap gap-3">
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
                <p
                  className="text-sm font-medium"
                  style={{ color: 'var(--text)' }}
                >
                  {Math.round(job.fit_score)}%
                </p>
              </div>
            )}
          </div>
        </div>

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
