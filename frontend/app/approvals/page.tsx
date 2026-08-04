'use client';

import { useEffect, useState } from 'react';
import { getApplications, getJob, approveApplication, dismissApplication, getTailoredCV, getCVProfile, autoApplyForJob } from '@/lib/api';
import { Application, Job } from '@/lib/types';
import { generateCVHTML, downloadCVAsHTML } from '@/lib/cvGenerator';
import { ScoutSidebar } from '@/components/ScoutSidebar';
import { ScoutLoading } from '@/components/ScoutLoading';
import { useScout } from '@/contexts/ScoutContext';
import { X } from 'lucide-react';

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
  const { setIsLoading } = useScout();
  const [isDark, setIsDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [pendingJobs, setPendingJobs] = useState<PendingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [priorityCountry, setPriorityCountry] = useState<string | null>(null);
  const [stats, setStats] = useState<{ needs_approval: number }>({ needs_approval: 0 });
  const [tailoringModalData, setTailoringModalData] = useState<{
    job: Job;
    tailored: TailoredCV;
  } | null>(null);

  useEffect(() => {
    const isDarkMode = document.documentElement.getAttribute('data-dark') === 'true';
    setIsDark(isDarkMode);
    const handleThemeChange = () => {
      setIsDark(document.documentElement.getAttribute('data-dark') === 'true');
    };
    window.addEventListener('storage', handleThemeChange);
    return () => window.removeEventListener('storage', handleThemeChange);
  }, []);

  const loadPendingJobs = async () => {
    try {
      setLoading(true);
      setIsLoading(true);
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

      const applications = await getApplications(100);
      const pending = applications.filter(app => app.status === 'pending_approval');

      const jobsData: PendingJob[] = [];
      for (const app of pending) {
        try {
          const jobData = await getJob(app.job_id);
          const job = jobData.job || jobData;

          const fitScore = (app as any).fit_score || job.fit_score || 0;
          if (fitScore >= 60) {
            jobsData.push({
              application: app,
              job: job,
            });
          }
        } catch (err) {
          console.error(`Failed to fetch job ${app.job_id}:`, err);
        }
      }

      const deduplicatedJobs = deduplicateByJobContent(jobsData);

      deduplicatedJobs.sort((a, b) => {
        const aInPriorityCountry = priorityCountry && (a.job?.location || '').includes(priorityCountry);
        const bInPriorityCountry = priorityCountry && (b.job?.location || '').includes(priorityCountry);

        if (aInPriorityCountry && !bInPriorityCountry) return -1;
        if (!aInPriorityCountry && bInPriorityCountry) return 1;

        return ((b.application as any).fit_score || 0) - ((a.application as any).fit_score || 0);
      });

      setPendingJobs(deduplicatedJobs);
      setStats({ needs_approval: deduplicatedJobs.length });
      console.log('[APPROVALS] Pending jobs count:', deduplicatedJobs.length);
      console.log('[APPROVALS] Stats set to:', { needs_approval: deduplicatedJobs.length });
    } catch (err) {
      console.error('Failed to load pending jobs:', err);
      setError('Failed to load pending jobs. Please try again.');
    } finally {
      setLoading(false);
      setIsLoading(false);
    }
  };

  const deduplicateByJobContent = (jobs: PendingJob[]): PendingJob[] => {
    const seen = new Set<string>();
    const deduped: PendingJob[] = [];

    for (const item of jobs) {
      const title = item.job?.title || '';
      const desc = item.job?.description_raw || '';
      const descPreview = desc.substring(0, 100);
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
  }, [priorityCountry]);

  const handleApprove = async (applicationId: string, jobId: string, job: Job) => {
    try {
      await approveApplication(applicationId);

      try {
        const tailored = await getTailoredCV(jobId);
        setTailoringModalData({ job, tailored });
      } catch (err) {
        console.warn('Could not fetch tailored CV:', err);
      }

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
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg)' }}>
      <ScoutSidebar isDark={isDark} setIsDark={setIsDark} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} stats={stats} />

      <main style={{ flex: 1, maxWidth: '900px', margin: '0 auto', padding: '44px 50px 70px', width: '100%' }}>
        <h1 style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '34px',
          fontWeight: 400,
          margin: '0 0 8px',
          color: 'var(--text)',
        }}>
          Roles waiting on your yes
        </h1>
        <p style={{
          margin: '0 0 26px',
          fontSize: '14px',
          color: 'var(--muted)',
        }}>
          Jobs that need your approval (fit score 60-84) · {pendingJobs.length} pending
        </p>

        {error && (
          <div style={{
            margin: '0 0 20px',
            padding: '14px 18px',
            borderRadius: '16px',
            backgroundColor: 'var(--card)',
            color: 'var(--color-accent-700)',
            fontSize: '13px',
            boxShadow: 'inset 0 2px 6px rgba(32,30,29,.15)',
          }}>
            {error}
          </div>
        )}

        {loading ? (
          <ScoutLoading message="Loading approvals..." />
        ) : pendingJobs.length === 0 ? (
          <div style={{
            borderRadius: '22px',
            backgroundColor: 'var(--card)',
            padding: '50px 20px',
            textAlign: 'center',
            boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16)',
          }}>
            <p style={{
              margin: '0 0 6px',
              fontSize: '16px',
              color: 'var(--text)',
            }}>
              No pending approvals
            </p>
            <p style={{
              margin: 0,
              fontSize: '13px',
              color: 'var(--muted)',
            }}>
              All your job reviews are up to date!
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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

        {tailoringModalData && (
          <TailoringModal
            job={tailoringModalData.job}
            tailored={tailoringModalData.tailored}
            onClose={() => setTailoringModalData(null)}
          />
        )}
      </main>
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
      const response = await autoApplyForJob(application.id);

      if (response && response.result) {
        setAutoApplyResult({
          status: response.result.status,
          method: response.result.method,
          action: response.result.action,
          what_i_tried: response.result.what_i_tried,
          why_i_need_help: response.result.why_i_need_help,
          error: response.result.error
        });
      } else {
        console.error('[AUTO_APPLY] Invalid response structure', response);
        setAutoApplyError('Invalid response from server');
      }
    } catch (err) {
      console.error('Auto-apply failed:', err);
      setAutoApplyError(err instanceof Error ? err.message : 'Auto-apply failed. Please try again.');
    } finally {
      setIsAutoApplying(false);
    }
  };

  const fitScore = application.fit_score !== undefined ? Math.round(application.fit_score) : (job.fit_score !== undefined ? Math.round(job.fit_score) : 0);
  const getScoreRingColor = (score: number) => score >= 70 ? '#7a8a5e' : '#c67139';
  const location = job.location ? job.location.split(',')[0] : 'Location N/A';
  const isBusy = isApproving || isDismissing || isAutoApplying;

  return (
    <div style={{
      borderRadius: '24px',
      backgroundColor: 'var(--card)',
      padding: '26px',
      boxShadow: 'inset 0 4px 12px rgba(32,30,29,.18), inset 0 -1px 0 rgba(255,255,255,.4)',
      animation: `ainFadeUp 0.55s cubic-bezier(.2,.8,.2,1) ${delay}s backwards`,
    }}>
      {/* 3-column grid layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '2fr auto auto',
        gap: '20px',
        alignItems: 'flex-start',
        marginBottom: '16px',
      }}>
        {/* Left: Job info */}
        <div>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '19px',
            color: 'var(--text)',
            marginBottom: '4px',
          }}>
            {job.title}
          </div>
          <div style={{
            fontSize: '13px',
            color: 'var(--muted)',
            marginBottom: '12px',
          }}>
            {job.company}
          </div>

          {/* Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            <span style={{
              fontSize: '11px',
              padding: '4px 12px',
              borderRadius: '999px',
              color: 'var(--muted)',
              boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
            }}>
              {job.modality || 'unknown'}
            </span>
            <span style={{
              fontSize: '11px',
              padding: '4px 12px',
              borderRadius: '999px',
              color: 'var(--muted)',
              boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
            }}>
              {location}
            </span>
            <EligibilityBadge job={job} />
          </div>
        </div>

        {/* Center: Score ring */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '6px',
        }}>
          <div style={{ position: 'relative', width: '58px', height: '58px' }}>
            <svg width="58" height="58" viewBox="0 0 64 64" style={{ transform: 'rotate(-90deg)' }}>
              <circle cx="32" cy="32" r="26" fill="none" stroke="var(--track)" strokeWidth="5" />
              <circle
                cx="32"
                cy="32"
                r="26"
                fill="none"
                stroke={getScoreRingColor(fitScore)}
                strokeWidth="5"
                strokeLinecap="round"
                strokeDasharray={163.36}
                strokeDashoffset={163.36 * (1 - fitScore / 100)}
              />
            </svg>
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              fontWeight: 700,
              fontFamily: 'var(--font-body)',
              color: getScoreRingColor(fitScore),
            }}>
              {fitScore}
            </div>
          </div>
          <span style={{ fontSize: '10.5px', color: 'var(--muted)' }}>Fit Score</span>
        </div>

        {/* Right: Action buttons */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          minWidth: '130px',
        }}>
          <button
            onClick={handleApproveClick}
            disabled={isBusy}
            style={{
              padding: '9px 0',
              borderRadius: '999px',
              border: 'none',
              fontFamily: 'var(--font-body)',
              fontSize: '12.5px',
              fontWeight: 700,
              background: 'var(--bg)',
              color: '#7a8a5e',
              boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)',
              cursor: isBusy ? 'not-allowed' : 'pointer',
              opacity: isBusy ? 0.6 : 1,
              transition: 'all 0.25s',
            }}
            onMouseEnter={(e) => !isBusy && (e.currentTarget.style.boxShadow = 'inset 0 3px 7px rgba(32,30,29,.25)')}
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
          >
            {isApproving ? 'Approving…' : 'Approve'}
          </button>
          <button
            onClick={handleAutoApplyClick}
            disabled={isBusy}
            style={{
              padding: '9px 0',
              borderRadius: '999px',
              border: 'none',
              fontFamily: 'var(--font-body)',
              fontSize: '12.5px',
              fontWeight: 700,
              background: 'var(--bg)',
              color: '#c67139',
              boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)',
              cursor: isBusy ? 'not-allowed' : 'pointer',
              opacity: isBusy ? 0.6 : 1,
              transition: 'all 0.25s',
            }}
            onMouseEnter={(e) => !isBusy && (e.currentTarget.style.boxShadow = 'inset 0 3px 7px rgba(32,30,29,.25)')}
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
          >
            {isAutoApplying ? 'Applying…' : 'Auto-Apply'}
          </button>
          <button
            onClick={handleDismissClick}
            disabled={isBusy}
            style={{
              padding: '9px 0',
              borderRadius: '999px',
              border: 'none',
              fontFamily: 'var(--font-body)',
              fontSize: '12.5px',
              fontWeight: 700,
              background: 'var(--bg)',
              color: 'var(--muted)',
              boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
              cursor: isBusy ? 'not-allowed' : 'pointer',
              opacity: isBusy ? 0.6 : 1,
              transition: 'all 0.25s',
            }}
            onMouseEnter={(e) => !isBusy && (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(32,30,29,.15)')}
          >
            {isDismissing ? 'Dismissing…' : 'Dismiss'}
          </button>
        </div>
      </div>

      {/* Eligibility details */}
      <EligibilityDetails job={job} />

      {/* Description snippet */}
      {job.description_raw && (
        <p style={{
          margin: 0,
          fontSize: '12.5px',
          lineHeight: '1.6',
          color: 'var(--muted)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}>
          {job.description_raw.substring(0, 200)}
        </p>
      )}

      {/* Auto-Apply result */}
      {autoApplyResult && (
        <div style={{
          marginTop: '14px',
          borderRadius: '16px',
          padding: '16px',
          boxShadow: 'inset 0 2px 6px rgba(32,30,29,.16)',
          backgroundColor: 'var(--bg)',
        }}>
          {autoApplyResult.status === 'applied' ? (
            <>
              <p style={{
                margin: '0 0 6px',
                fontSize: '13px',
                fontWeight: 700,
                color: '#7a8a5e',
              }}>
                ✓ Applied Successfully
              </p>
              <p style={{
                margin: 0,
                fontSize: '11.5px',
                color: 'var(--muted)',
              }}>
                Applied via <b style={{ color: 'var(--text)' }}>{autoApplyResult.method || 'form'}</b>
              </p>
            </>
          ) : (
            <>
              <p style={{
                margin: '0 0 10px',
                fontSize: '13px',
                fontWeight: 700,
                color: '#c67139',
              }}>
                Manual Action Required
              </p>
              <div style={{ marginBottom: '10px' }}>
                <p style={{
                  margin: '0 0 3px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--text)',
                }}>
                  What I tried:
                </p>
                <p style={{
                  margin: 0,
                  fontSize: '11.5px',
                  color: 'var(--muted)',
                }}>
                  {autoApplyResult.what_i_tried || 'I attempted to apply for this job'}
                </p>
              </div>
              <div style={{ marginBottom: '10px' }}>
                <p style={{
                  margin: '0 0 3px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--text)',
                }}>
                  Why I need your help:
                </p>
                <p style={{
                  margin: 0,
                  fontSize: '11.5px',
                  color: 'var(--muted)',
                }}>
                  {autoApplyResult.why_i_need_help || 'The application requires manual completion'}
                </p>
              </div>
              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '11.5px',
                    fontWeight: 700,
                    color: '#c67139',
                    textDecoration: 'none',
                    padding: '8px 14px',
                    borderRadius: '999px',
                    boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)',
                    backgroundColor: 'var(--card)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'inset 0 3px 7px rgba(32,30,29,.25)')}
                  onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
                >
                  Open Job Page ↗
                </a>
              )}
            </>
          )}
        </div>
      )}

      {/* Auto-Apply error */}
      {autoApplyError && (
        <div style={{
          marginTop: '14px',
          padding: '12px 14px',
          borderRadius: '16px',
          backgroundColor: 'var(--bg)',
          color: 'var(--color-accent-700)',
          fontSize: '11.5px',
          boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
        }}>
          {autoApplyError}
        </div>
      )}
    </div>
  );
}

interface EligibilityBadgeProps {
  job: Job;
}

function EligibilityBadge({ job }: EligibilityBadgeProps) {
  const eligibility = (job as any).eligibility_note;

  if (!eligibility) {
    return null;
  }

  const getColors = () => {
    if (!eligibility.eligible) {
      return { color: 'var(--muted)', label: 'Not eligible' };
    }
    if (eligibility.visa_required) {
      return { color: '#c67139', label: 'Visa may be required' };
    }
    return { color: '#7a8a5e', label: 'No visa required' };
  };

  const { color, label } = getColors();

  return (
    <span style={{
      fontSize: '11px',
      fontWeight: 600,
      padding: '4px 12px',
      borderRadius: '999px',
      color,
      boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
    }} title={eligibility.reason}>
      {label}
    </span>
  );
}

function EligibilityDetails({ job }: { job: Job }) {
  const eligibility = (job as any).eligibility_note;

  if (!eligibility) {
    return null;
  }

  const getColor = () => {
    if (!eligibility.eligible) {
      return 'var(--muted)';
    }
    if (eligibility.visa_required) {
      return '#c67139';
    }
    return '#7a8a5e';
  };

  const color = getColor();

  return (
    <div style={{
      borderRadius: '16px',
      padding: '14px 16px',
      boxShadow: 'inset 0 2px 6px rgba(32,30,29,.15)',
      marginBottom: '14px',
      backgroundColor: 'var(--bg)',
    }}>
      <p style={{
        margin: '0 0 6px',
        fontSize: '12px',
        fontWeight: 600,
        color,
      }}>
        ℹ {eligibility.reason}
      </p>
      {eligibility.visa_type && (
        <p style={{
          margin: '0 0 4px',
          fontSize: '11.5px',
          color: 'var(--muted)',
        }}>
          <b>Visa type:</b> {eligibility.visa_type}
        </p>
      )}
      <p style={{
        margin: 0,
        fontSize: '11.5px',
        color: 'var(--muted)',
      }}>
        <b>Recommendation:</b> {eligibility.recommendation}
      </p>
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
    const loadCVProfile = async () => {
      try {
        const data = await getCVProfile();
        setCVData(data);
      } catch (err) {
        console.warn('Failed to load CV profile:', err);
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
      const htmlContent = await generateCVHTML(job, tailored, cvData);
      const firstName = cvData.name?.split(' ')[0] || 'CV';
      const lastName = cvData.name?.split(' ').slice(1).join('_') || '';
      const jobTitleSlug = job.title?.toLowerCase().replace(/\s+/g, '_') || 'position';
      const date = new Date().toISOString().split('T')[0];
      const filename = `${firstName}_${lastName}_${jobTitleSlug}_${date}.html`.replace(/_{2,}/g, '_');

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
      <div
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,.5)',
          zIndex: 40,
        }}
        onClick={onClose}
      />

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
          borderRadius: '24px',
          backgroundColor: 'var(--card)',
          boxShadow: 'inset 0 4px 12px rgba(32,30,29,.18)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'ainModalUp 0.3s ease-out',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '26px',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div>
            <h2 style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '24px',
              fontWeight: 400,
              margin: 0,
              color: 'var(--text)',
            }}>
              ✨ CV Tailored
            </h2>
            <p style={{
              fontSize: '14px',
              margin: '6px 0 0',
              color: 'var(--muted)',
            }}>
              {job.title} at {job.company}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              padding: '8px',
              cursor: 'pointer',
              color: 'var(--muted)',
              transition: 'opacity 0.25s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.7')}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '26px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
        }}>
          {/* Professional Summary */}
          <section>
            <h3 style={{
              fontSize: '12px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              margin: '0 0 12px',
              color: 'var(--text)',
            }}>
              Professional Summary
            </h3>
            <p style={{
              fontSize: '13px',
              lineHeight: '1.6',
              padding: '14px 16px',
              borderRadius: '16px',
              margin: 0,
              backgroundColor: 'var(--bg)',
              color: 'var(--muted)',
              boxShadow: 'inset 0 2px 6px rgba(32,30,29,.15)',
            }}>
              {tailored.summary}
            </p>
          </section>

          {/* Highlighted Skills */}
          {tailored.highlighted_skills && tailored.highlighted_skills.length > 0 && (
            <section>
              <h3 style={{
                fontSize: '12px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                margin: '0 0 12px',
                color: 'var(--text)',
              }}>
                Highlighted Skills
              </h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {tailored.highlighted_skills.map((skill, i) => (
                  <span
                    key={i}
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      padding: '6px 12px',
                      borderRadius: '999px',
                      backgroundColor: '#dde5cc',
                      color: '#7a8a5e',
                      boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
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
              <h3 style={{
                fontSize: '12px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                margin: '0 0 12px',
                color: 'var(--text)',
              }}>
                Relevant Projects to Emphasize
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {tailored.relevant_projects.map((project, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '14px 16px',
                      borderRadius: '16px',
                      backgroundColor: 'var(--bg)',
                      boxShadow: 'inset 0 2px 6px rgba(32,30,29,.15)',
                    }}
                  >
                    <h4 style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      margin: '0 0 8px',
                      color: 'var(--text)',
                    }}>
                      {project.name}
                    </h4>
                    <p style={{
                      fontSize: '12px',
                      lineHeight: '1.5',
                      margin: 0,
                      color: 'var(--muted)',
                    }}>
                      {project.why_relevant}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* What Was Tailored */}
          {tailored.tailoring_notes && (
            <section>
              <h3 style={{
                fontSize: '12px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                margin: '0 0 12px',
                color: 'var(--text)',
              }}>
                What Was Tailored
              </h3>
              <p style={{
                fontSize: '13px',
                lineHeight: '1.6',
                padding: '14px 16px',
                borderRadius: '16px',
                margin: 0,
                backgroundColor: 'var(--bg)',
                color: 'var(--muted)',
                fontStyle: 'italic',
                boxShadow: 'inset 0 2px 6px rgba(32,30,29,.15)',
              }}>
                {tailored.tailoring_notes}
              </p>
            </section>
          )}

          {/* AI note */}
          <p style={{
            fontSize: '11px',
            textAlign: 'center',
            color: 'var(--faint)',
            margin: 0,
            fontStyle: 'italic',
          }}>
            Your CV has been customized using AI to highlight relevant experience for this role.
          </p>
        </div>

        {/* Footer Actions */}
        <div style={{
          padding: '20px 26px',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          gap: '12px',
        }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '10px 16px',
              borderRadius: '999px',
              border: 'none',
              fontFamily: 'var(--font-body)',
              fontSize: '13px',
              fontWeight: 400,
              background: 'var(--bg)',
              color: 'var(--muted)',
              boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
              cursor: 'pointer',
              transition: 'all 0.25s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(32,30,29,.15)')}
          >
            Close
          </button>
          <button
            onClick={handleDownloadCV}
            disabled={isDownloading || !cvData}
            style={{
              flex: 1,
              padding: '10px 16px',
              borderRadius: '999px',
              border: 'none',
              fontFamily: 'var(--font-body)',
              fontSize: '13px',
              fontWeight: 700,
              background: 'var(--bg)',
              color: '#c67139',
              boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)',
              cursor: isDownloading || !cvData ? 'not-allowed' : 'pointer',
              opacity: isDownloading || !cvData ? 0.6 : 1,
              transition: 'all 0.25s',
            }}
            onMouseEnter={(e) => !isDownloading && !cvData && (e.currentTarget.style.boxShadow = 'inset 0 3px 7px rgba(32,30,29,.25)')}
            onMouseLeave={(e) => (e.currentTarget.style.boxShadow = 'inset 0 2px 5px rgba(32,30,29,.2)')}
          >
            {isDownloading ? 'Generating…' : 'Download CV'}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes ainModalUp {
          from {
            opacity: 0;
            transform: translate(-50%, -46%);
          }
          to {
            opacity: 1;
            transform: translate(-50%, -50%);
          }
        }
      `}</style>
    </>
  );
}
