'use client';

import { useEffect, useState } from 'react';
import { getApplications, getJob, approveApplication, dismissApplication, getTailoredCV, getCVProfile, autoApplyForJob } from '@/lib/api';
import { Application, Job } from '@/lib/types';
import { generateCVHTML, downloadCVAsHTML } from '@/lib/cvGenerator';
import { X, ExternalLink } from 'lucide-react';

interface PendingJob {
  application: Application;
  job: Job;
}

interface TailoredCV {
  summary: string;
  highlighted_skills: string[];
  relevant_projects: Array<{ name: string; why_relevant: string }>;
  tailoring_notes: string;
}

export default function ApprovalsPage() {
  const [pendingJobs, setPendingJobs] = useState<PendingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tailoringModalData, setTailoringModalData] = useState<{
    job: Job;
    tailored: TailoredCV;
  } | null>(null);

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

      // Deduplicate by job title + description hash (handles duplicate job listings)
      const deduplicatedJobs = deduplicateByJobContent(jobsData);

      // Sort by fit_score descending (highest score first)
      deduplicatedJobs.sort((a, b) => ((b.application as any).fit_score || 0) - ((a.application as any).fit_score || 0));

      setPendingJobs(deduplicatedJobs);
    } catch (err) {
      console.error('Failed to load pending jobs:', err);
      setError('Failed to load pending jobs. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Deduplicate jobs by title + first 100 chars of description
  const deduplicateByJobContent = (jobs: PendingJob[]): PendingJob[] => {
    const seen = new Set<string>();
    const deduped: PendingJob[] = [];

    for (const item of jobs) {
      const title = item.job?.title || '';
      const desc = item.job?.description_raw || '';
      const descPreview = desc.substring(0, 100);

      // Create a simple hash-like key from title + description
      const key = title + '|' + descPreview;

      if (!seen.has(key)) {
        seen.add(key);
        deduped.push(item);
      }
    }

    return deduped;
  };

  useEffect(() => {
    loadPendingJobs();
  }, []);

  const handleApprove = async (applicationId: string, jobId: string, job: Job) => {
    try {
      await approveApplication(applicationId);

      // Fetch tailored CV after approval
      try {
        const tailored = await getTailoredCV(jobId);
        setTailoringModalData({ job, tailored });
      } catch (err) {
        console.warn('Could not fetch tailored CV:', err);
        // Continue even if tailoring fails - approval was still successful
      }

      // Reload the pending jobs list
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

      {/* CV Tailoring Modal */}
      {tailoringModalData && (
        <TailoringModal
          job={tailoringModalData.job}
          tailored={tailoringModalData.tailored}
          onClose={() => setTailoringModalData(null)}
        />
      )}
    </div>
  );
}

interface ApprovalCardProps {
  application: Application;
  job: Job;
  onApprove: (id: string, jobId: string, job: Job) => void;
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
  const [isAutoApplying, setIsAutoApplying] = useState(false);
  const [autoApplyResult, setAutoApplyResult] = useState<any>(null);
  const [autoApplyError, setAutoApplyError] = useState<string | null>(null);

  const handleApproveClick = async () => {
    setIsApproving(true);
    try {
      await onApprove(application.id, application.job_id, job);
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

  const handleAutoApplyClick = async () => {
    setIsAutoApplying(true);
    setAutoApplyError(null);
    setAutoApplyResult(null);
    try {
      const result = await autoApplyForJob(application.id);
      setAutoApplyResult(result);
      console.log('[AUTO_APPLY] Result:', result);
    } catch (err) {
      console.error('Auto-apply failed:', err);
      setAutoApplyError(err instanceof Error ? err.message : 'Auto-apply failed. Please try again.');
    } finally {
      setIsAutoApplying(false);
    }
  };

  const fitScore = application.fit_score !== undefined ? Math.round(application.fit_score) : (job.fit_score !== undefined ? Math.round(job.fit_score) : 0);
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
            disabled={isApproving || isDismissing || isAutoApplying}
            className="px-4 py-2 rounded-lg font-medium text-sm transition-all"
            style={{
              backgroundColor: '#10b981',
              color: 'white',
              opacity: isApproving || isDismissing || isAutoApplying ? 0.6 : 1,
              cursor: isApproving || isDismissing || isAutoApplying ? 'not-allowed' : 'pointer',
            }}
          >
            {isApproving ? 'Approving...' : 'Approve'}
          </button>
          <button
            onClick={handleAutoApplyClick}
            disabled={isApproving || isDismissing || isAutoApplying}
            className="px-4 py-2 rounded-lg font-medium text-sm transition-all"
            style={{
              backgroundColor: '#3b82f6',
              color: 'white',
              opacity: isApproving || isDismissing || isAutoApplying ? 0.6 : 1,
              cursor: isApproving || isDismissing || isAutoApplying ? 'not-allowed' : 'pointer',
            }}
          >
            {isAutoApplying ? 'Applying...' : 'Auto-Apply'}
          </button>
          <button
            onClick={handleDismissClick}
            disabled={isApproving || isDismissing || isAutoApplying}
            className="px-4 py-2 rounded-lg font-medium text-sm transition-all"
            style={{
              backgroundColor: 'var(--border)',
              color: 'var(--muted)',
              opacity: isApproving || isDismissing || isAutoApplying ? 0.6 : 1,
              cursor: isApproving || isDismissing || isAutoApplying ? 'not-allowed' : 'pointer',
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

      {/* Auto-Apply Result */}
      {autoApplyResult && (
        <div
          className="mt-4 p-3 rounded-lg border"
          style={{
            backgroundColor: autoApplyResult.status === 'applied' ? '#f0fdf4' : '#fef3c7',
            borderColor: autoApplyResult.status === 'applied' ? '#d1fae5' : '#fcd34d',
          }}
        >
          <p
            className="text-sm font-medium mb-1"
            style={{
              color: autoApplyResult.status === 'applied' ? '#10b981' : '#d97706',
            }}
          >
            {autoApplyResult.status === 'applied'
              ? `Applied via ${autoApplyResult.method || 'form'}`
              : 'Manual application required'}
          </p>
          {autoApplyResult.action && (
            <p
              className="text-xs"
              style={{
                color: autoApplyResult.status === 'applied' ? '#6b7280' : '#92400e',
              }}
            >
              {autoApplyResult.action}
            </p>
          )}
          {autoApplyResult.status !== 'applied' && job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 text-xs font-medium"
              style={{
                color: '#d97706',
              }}
            >
              Open Job Page <ExternalLink size={12} />
            </a>
          )}
        </div>
      )}

      {/* Auto-Apply Error */}
      {autoApplyError && (
        <div
          className="mt-4 p-3 rounded-lg border"
          style={{
            backgroundColor: '#fee',
            borderColor: '#fcc',
            color: '#c00',
          }}
        >
          <p className="text-xs font-medium">{autoApplyError}</p>
        </div>
      )}
    </div>
  );
}

interface TailoringModalProps {
  job: Job;
  tailored: TailoredCV;
  onClose: () => void;
}

function TailoringModal({ job, tailored, onClose }: TailoringModalProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [cvData, setCVData] = useState<any>(null);

  useEffect(() => {
    // Fetch user's CV profile for CV generation
    const loadCVProfile = async () => {
      try {
        const data = await getCVProfile();
        setCVData(data);
      } catch (err) {
        console.warn('Failed to load CV profile for download:', err);
      }
    };
    loadCVProfile();
  }, []);

  const handleDownloadCV = async () => {
    if (!cvData) {
      console.error('CV profile not loaded');
      return;
    }

    try {
      setIsDownloading(true);

      // Generate HTML CV dynamically from database
      const htmlContent = await generateCVHTML(job, tailored, cvData);

      // Create filename: firstname_lastname_jobtitle_date.html
      const firstName = cvData.name?.split(' ')[0] || 'CV';
      const lastName = cvData.name?.split(' ').slice(1).join('_') || '';
      const jobTitleSlug = job.title?.toLowerCase().replace(/\s+/g, '_') || 'position';
      const date = new Date().toISOString().split('T')[0];
      const filename = `${firstName}_${lastName}_${jobTitleSlug}_${date}.html`.replace(/_{2,}/g, '_');

      // Trigger download
      downloadCVAsHTML(filename, htmlContent);

      console.log('[CV] Download triggered:', filename);
    } catch (err) {
      console.error('[CV] Download failed:', err);
    } finally {
      setIsDownloading(false);
    }
  };

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
          borderColor: 'var(--border)',
          backgroundColor: 'var(--card)',
          animation: 'slideUp 0.3s ease-out',
        }}
      >
        {/* Header */}
        <div
          className="sticky top-0 flex items-center justify-between p-6 border-b"
          style={{ borderColor: 'var(--border)', backgroundColor: 'var(--card)' }}
        >
          <div>
            <h2
              className="text-2xl font-bold"
              style={{
                color: 'var(--text)',
                letterSpacing: '-0.02em',
              }}
            >
              ✨ CV Tailored
            </h2>
            <p
              className="text-sm mt-1"
              style={{ color: 'var(--muted)' }}
            >
              {job.title} at {job.company}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:opacity-70 transition-opacity"
            style={{ color: 'var(--muted)' }}
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Professional Summary */}
          <section>
            <h3
              className="text-sm font-bold mb-3 uppercase tracking-wider"
              style={{ color: 'var(--text)' }}
            >
              Professional Summary
            </h3>
            <p
              className="text-sm leading-relaxed p-4 rounded-lg border"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--muted)',
              }}
            >
              {tailored.summary}
            </p>
          </section>

          {/* Highlighted Skills */}
          {tailored.highlighted_skills && tailored.highlighted_skills.length > 0 && (
            <section>
              <h3
                className="text-sm font-bold mb-3 uppercase tracking-wider"
                style={{ color: 'var(--text)' }}
              >
                Highlighted Skills
              </h3>
              <div className="flex flex-wrap gap-2">
                {tailored.highlighted_skills.map((skill, i) => (
                  <span
                    key={i}
                    className="text-xs font-medium px-3 py-1.5 rounded-full"
                    style={{
                      backgroundColor: '#10b98120',
                      color: '#10b981',
                      border: '1px solid #10b98140',
                    }}
                  >
                    ✓ {skill}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Relevant Projects */}
          {tailored.relevant_projects && tailored.relevant_projects.length > 0 && (
            <section>
              <h3
                className="text-sm font-bold mb-3 uppercase tracking-wider"
                style={{ color: 'var(--text)' }}
              >
                Relevant Projects to Emphasize
              </h3>
              <div className="space-y-3">
                {tailored.relevant_projects.map((project, i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg border"
                    style={{
                      borderColor: 'var(--border)',
                      backgroundColor: 'var(--bg)',
                    }}
                  >
                    <h4
                      className="text-sm font-semibold mb-2"
                      style={{ color: 'var(--text)' }}
                    >
                      {project.name}
                    </h4>
                    <p
                      className="text-xs leading-relaxed"
                      style={{ color: 'var(--muted)' }}
                    >
                      {project.why_relevant}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Tailoring Notes */}
          {tailored.tailoring_notes && (
            <section>
              <h3
                className="text-sm font-bold mb-3 uppercase tracking-wider"
                style={{ color: 'var(--text)' }}
              >
                What Was Tailored
              </h3>
              <p
                className="text-sm leading-relaxed p-4 rounded-lg border italic"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--bg)',
                  color: 'var(--muted)',
                }}
              >
                {tailored.tailoring_notes}
              </p>
            </section>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-lg font-medium text-sm transition-all"
              style={{
                backgroundColor: 'var(--sidebar-active)',
                color: 'var(--text)',
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
              Close
            </button>
            <button
              onClick={handleDownloadCV}
              disabled={isDownloading || !cvData}
              className="flex-1 px-4 py-2.5 rounded-lg font-medium text-sm text-white transition-all"
              style={{
                backgroundColor: isDownloading || !cvData ? '#9ca3af' : '#3b82f6',
                cursor: isDownloading || !cvData ? 'not-allowed' : 'pointer',
              }}
              onMouseEnter={(e) => {
                if (!isDownloading && cvData) {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.backgroundColor = '#2563eb';
                }
              }}
              onMouseLeave={(e) => {
                if (!isDownloading && cvData) {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.backgroundColor = '#3b82f6';
                }
              }}
            >
              {isDownloading ? '⏳ Generating...' : '⬇️ Download CV'}
            </button>
          </div>

          {/* Callout */}
          <div
            className="p-4 rounded-lg border"
            style={{
              borderColor: '#3b82f6',
              backgroundColor: '#3b82f620',
            }}
          >
            <p
              className="text-xs"
              style={{ color: '#3b82f6' }}
            >
              💡 Your CV has been customized for this role using AI. The highlighted skills and projects above are optimized for ATS scoring and relevance.
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </>
  );
}
