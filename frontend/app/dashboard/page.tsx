'use client';

import { useEffect, useState } from 'react';
import { getUserProfile, getJobsWithStats, getAgentLogs, getPendingApprovalJobs } from '@/lib/api';
import { GlobeMap } from '@/components/GlobeMap';
import { ScoutSidebar } from '@/components/ScoutSidebar';
import { Job, UserProfile, DashboardStats } from '@/lib/types';

const getScoreRingColor = (score: number): string => {
  return score >= 70 ? '#7a8a5e' : '#c67139';
};

// CSS Keyframes - add to head
const injectStyles = () => {
  if (typeof window === 'undefined') return;
  if (document.getElementById('dashboard-styles')) return;

  const style = document.createElement('style');
  style.id = 'dashboard-styles';
  style.textContent = `
    @keyframes ainSway { 0%, 100% { transform: rotate(-4deg); } 50% { transform: rotate(4deg); } }
    @keyframes ainBreathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }
    @keyframes ainLook { 0%, 12% { transform: translate(0, 0); } 20%, 32% { transform: translate(-3px, 1px); } 40%, 52% { transform: translate(3px, -1px); } 60%, 72% { transform: translate(-2px, 2px); } 80%, 100% { transform: translate(0, 0); } }
    @keyframes ainBlink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(0.15); } }
    @keyframes ainTalk { 0%, 100% { transform: scaleX(1) scaleY(1); } 30% { transform: scaleX(0.75) scaleY(1.3); } 55% { transform: scaleX(1.15) scaleY(0.7); } 80% { transform: scaleX(0.9) scaleY(1.1); } }
    @keyframes ainFadeUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes ainSlideLeft { from { opacity: 0; transform: translateX(-16px); } to { opacity: 1; transform: translateX(0); } }

    * { --dbg: var(--bg); --dcard: var(--card); --dactive: var(--active); --dborder: var(--border); --dtext: var(--text); --dmuted: var(--muted); --dfaint: var(--faint); --dtrack: var(--track); --font-heading: 'Caprasimo', serif; --font-body: 'Figtree', sans-serif; }
    body { font-family: var(--font-body); background: var(--dbg); color: var(--dtext); }
    .inset-panel { box-shadow: inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4); }
    .inset-chip { box-shadow: inset 0 1px 3px rgba(32,30,29,.15); }
    .inset-button { box-shadow: inset 0 2px 5px rgba(32,30,29,.2); }
    .nav-item { border-radius: 999px; transition: all .25s; }
    .nav-item:hover { background: var(--dactive); box-shadow: inset 0 2px 4px rgba(32,30,29,.12); }
    .nav-item.active { background: var(--dcard); box-shadow: inset 0 2px 5px rgba(32,30,29,.18), inset 0 -1px 0 rgba(255,255,255,.5); }
  `;
  document.head.appendChild(style);
};


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
  const [isDark, setIsDark] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [weeklySummary, setWeeklySummary] = useState<string>('');
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [lastScanTime, setLastScanTime] = useState<Date | null>(null);
  const [stats, setStats] = useState<DashboardStats>({
    jobs_found: 0,
    applied: 0,
    interviews: 0,
    needs_approval: 0,
  });
  const [loading, setLoading] = useState(true);

  // Design tokens - Light theme
  const lightTheme = {
    '--bg': '#f0e4cf',
    '--card': '#fffaf1',
    '--active': '#ebddc5',
    '--border': 'rgba(32,30,29,.1)',
    '--text': '#201e1d',
    '--muted': '#645c50',
    '--faint': '#82796a',
    '--track': '#dcd3c4',
    '--color-accent': '#c67139',
    '--color-accent-200': '#f4d9c6',
    '--color-accent-700': '#7a3f1f',
    '--color-accent-2': '#7a8a5e',
    '--color-accent-2-200': '#dde5cc',
    '--color-accent-2-800': '#4a5233',
  };

  // Design tokens - Dark theme
  const darkTheme = {
    '--bg': '#2b2118',
    '--card': '#3a2c1e',
    '--active': '#463625',
    '--border': 'rgba(245,234,216,.16)',
    '--text': '#f7ecd9',
    '--muted': '#d1bd9c',
    '--faint': '#a68f72',
    '--track': 'rgba(245,234,216,.16)',
    '--color-accent': '#c67139',
    '--color-accent-200': '#f4d9c6',
    '--color-accent-700': '#7a3f1f',
    '--color-accent-2': '#7a8a5e',
    '--color-accent-2-200': '#dde5cc',
    '--color-accent-2-800': '#4a5233',
  };

  const theme = isDark ? darkTheme : lightTheme;

  useEffect(() => {
    injectStyles();
  }, []);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const profileData = await getUserProfile().catch(() => null);
        const userId = localStorage.getItem('user_id');

        // Fetch summary with auth headers
        const summaryRes = await fetch('http://localhost:8001/api/summary/weekly', {
          headers: { 'x-user-id': userId || '' }
        });
        const summaryData = await summaryRes.json();
        console.log('[SUMMARY RAW]', summaryData);
        console.log('[SUMMARY TEXT]', summaryData?.summary_text);

        // Fetch logs with auth headers
        const logsRes = await fetch('http://localhost:8001/api/jobs/logs?limit=5', {
          headers: { 'x-user-id': userId || '' }
        });
        const logsData = await logsRes.json();
        console.log('[LOGS RAW]', logsData);
        const logs = Array.isArray(logsData) ? logsData : [];

        const [jobsData, pendingJobs] = await Promise.all([
          getJobsWithStats().catch(() => ({ stats: { jobs_found: 0, applied: 0, interviews: 0, needs_approval: 0 } })),
          getPendingApprovalJobs().catch(() => []),
        ]);

        setProfile(profileData);
        setJobs(pendingJobs);
        setActivityLogs(logs);
        setWeeklySummary(summaryData?.summary?.summary_text || '');

        if (logs.length > 0) {
          setLastScanTime(new Date(logs[0].created_at));
        }
        if (jobsData?.stats) {
          setStats(jobsData.stats);
        }
      } catch (error) {
        console.error('Failed to load dashboard:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const formatActivityEvents = (logs: ActivityLog[]) => {
    return logs.map((log, index) => {
      const details = log.details || {};
      let title = '';

      if (log.agent === 'job_discovery' && log.status === 'success') {
        title = `Found ${details.count || details.jobs_count || 'new'} roles matching your profile`;
      } else if (log.agent === 'job_parsing' && log.status === 'success') {
        const jobName = details.title || details.job_title || 'Job';
        title = `Parsed: ${jobName.substring(0, 40)}`;
      } else if (log.agent === 'job_match' && log.status === 'success') {
        const jobName = (log as any).job_title || 'Position';
        const company = (log as any).job_company || 'Company';
        const score = log.fit_score || '?';
        title = `Scored job — ${jobName} at ${company} (${score}%)`;
      } else if (log.agent === 'job_match' && log.status === 'failed') {
        title = 'Failed to score job';
      } else {
        title = `${log.agent.charAt(0).toUpperCase() + log.agent.slice(1)} — ${log.status}`;
      }

      const timestamp = getRelativeTime(new Date(log.created_at));

      return { title, timestamp, isLatest: index === 0 };
    });
  };

  const getRelativeTime = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  const handleRegenerateSummary = async () => {
    try {
      setRegenerating(true);
      const userId = localStorage.getItem('user_id');

      const response = await fetch('http://localhost:8001/api/summary/weekly/regenerate', {
        method: 'POST',
        headers: { 'x-user-id': userId || '' }
      });

      if (response.ok) {
        const data = await response.json();
        console.log('[REGENERATE] Response:', data);
        setWeeklySummary(data?.summary?.summary_text || '');
      }
    } catch (error) {
      console.error('Failed to regenerate summary:', error);
    } finally {
      setRegenerating(false);
    }
  };

  const hour = new Date().getHours();
  const timeGreeting = hour < 12 ? 'Morning' : hour < 18 ? 'Afternoon' : 'Evening';
  const firstName = (profile as any)?.cv_data?.name?.split(' ')[0] || (profile as any)?.name?.split(' ')[0] || '';
  const greeting = `${timeGreeting}, ${firstName || 'there'}. Let's see who's hiring.`;
  const today = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date());

  const activityEvents = activityLogs.length > 0 ? formatActivityEvents(activityLogs) : [
    { title: 'No activity yet', timestamp: 'Start searching', isLatest: true },
  ];

  return (
    <div style={theme as any}>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <ScoutSidebar isDark={isDark} setIsDark={setIsDark} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} stats={stats} />

        {/* Main Content */}
        <main style={{ flex: 1, padding: '44px 60px 70px', maxWidth: '900px', margin: '0 auto', width: '100%' }}>
          {/* Header */}
          <div style={{ marginBottom: '40px' }}>
            <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '44px', fontWeight: 400, color: 'var(--text)', margin: '0 0 8px', lineHeight: 1.12 }}>
              {greeting}
            </h1>
            <p style={{ margin: 0, fontSize: '13.5px', color: 'var(--dmuted)' }}>
              {today}
            </p>
          </div>

          {/* Stats Strip */}
          <section
            className="inset-panel"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '16px',
              marginBottom: '40px',
              borderRadius: '24px',
              background: 'var(--dcard)',
              padding: '20px',
            }}
          >
            {[
              { num: stats.jobs_found, label: 'Jobs found', color: 'var(--color-accent-700)' },
              { num: stats.applied, label: 'Applied', color: 'var(--dfaint)' },
              { num: stats.interviews, label: 'Interviews', color: 'var(--dfaint)' },
              { num: stats.needs_approval, label: 'Needs approval', color: 'var(--dfaint)', showDot: true },
            ].map((stat, i, arr) => (
              <div key={i} style={{ animation: `ainFadeUp .6s cubic-bezier(.2,.8,.2,1) ${i * 0.06}s backwards`, padding: '0 20px', borderRight: i < arr.length - 1 ? '1px solid var(--dborder)' : 'none' }}>
                <div style={{ fontFamily: 'var(--font-heading)', fontSize: '34px', color: 'var(--text)' }}>
                  {stat.num}
                </div>
                <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: stat.color, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {stat.showDot && <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-accent)', boxShadow: '0 0 4px var(--color-accent)' }} />}
                  {stat.label}
                </div>
              </div>
            ))}
          </section>

          {/* Globe */}
          <section style={{ marginBottom: '40px' }}>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '18px', fontWeight: 400, color: '#645C50', margin: '0 0 20px' }}>
              Where Scout is Finding Roles
            </h2>
            <GlobeMap />
          </section>

          {/* Activity + Fresh from Scout */}
          <section style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: '20px', marginBottom: '40px' }}>
            {/* Fresh from Scout */}
            <div
              className="inset-panel"
              style={{
                borderRadius: '22px',
                background: 'var(--dcard)',
                padding: '18px 20px',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                <div style={{ position: 'relative', width: '28px', height: '28px', flex: '0 0 28px' }}>
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      borderRadius: '56% 44% 48% 52% / 50% 55% 45% 50%',
                      background: `radial-gradient(circle at 32% 28%, var(--color-accent-200), var(--color-accent) 60%, var(--color-accent-700))`,
                      boxShadow: '0 2px 4px rgba(32,30,29,.2), inset 0 1px 2px rgba(255,255,255,.3)',
                    }}
                  />
                  <div style={{ position: 'absolute', left: '7px', top: '11px', width: '3px', height: '3px', borderRadius: '50%', background: 'var(--dbg)' }} />
                  <div style={{ position: 'absolute', left: '17px', top: '11px', width: '3px', height: '3px', borderRadius: '50%', background: 'var(--dbg)' }} />
                  <div style={{ position: 'absolute', left: '10px', top: '16px', width: '8px', height: '4px', borderRadius: '0 0 6px 6px', borderBottom: '1px solid var(--dbg)' }} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flex: 1, gap: '12px' }}>
                  <div style={{ fontFamily: 'var(--font-heading)', fontSize: '15px', fontWeight: 400, color: 'var(--text)' }}>
                    Fresh from Scout
                  </div>
                  <button
                    onClick={handleRegenerateSummary}
                    disabled={regenerating}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      border: 'none',
                      background: 'var(--dbg)',
                      color: 'var(--dmuted)',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: regenerating ? 'not-allowed' : 'pointer',
                      opacity: regenerating ? 0.6 : 1,
                      transition: 'all 0.2s',
                      flex: '0 0 auto',
                    }}
                    onMouseEnter={(e) => {
                      if (!regenerating) {
                        (e.target as HTMLButtonElement).style.background = 'var(--dactive)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      (e.target as HTMLButtonElement).style.background = 'var(--dbg)';
                    }}
                  >
                    {regenerating ? 'Regenerating...' : 'Regenerate ↻'}
                  </button>
                </div>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--dmuted)', margin: 0, lineHeight: 1.5 }}>
                "{weeklySummary || 'Loading summary...'}"
              </p>
            </div>

            {/* Agent Activity */}
            <div
              className="inset-panel"
              style={{
                borderRadius: '22px',
                background: 'var(--dcard)',
                padding: '6px 20px',
              }}
            >
              {typeof window !== 'undefined' && (
                <>
                  {console.log('[ACTIVITY] activityLogs state:', activityLogs)}
                  {console.log('[ACTIVITY] formatted:', formatActivityEvents(activityLogs))}
                </>
              )}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '14px 0 6px' }}>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '15px', fontWeight: 400, color: '#645C50', margin: 0 }}>
                  Agent Activity
                </h2>
                <a href="/debug" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-accent)', textDecoration: 'none' }}>
                  View all →
                </a>
              </div>
              {lastScanTime && (
                <p style={{ fontSize: '12px', color: 'var(--dmuted)', margin: '2px 0 16px' }}>
                  Last scan: {getRelativeTime(lastScanTime)}
                </p>
              )}
              <div>
                {activityEvents.slice(0, 3).map((event, i) => (
                  <div key={i} style={{ display: 'flex', gap: '14px', padding: '10px 0', borderBottom: '1px solid rgba(32,30,29,.08)', animation: `ainSlideLeft .5s cubic-bezier(.2,.8,.2,1) ${i * 0.08}s backwards` }}>
                    <div
                      style={{
                        width: '6px',
                        flex: '0 0 6px',
                        borderRadius: '4px',
                        background: i === 0 ? 'var(--color-accent)' : 'var(--dfaint)',
                        alignSelf: 'stretch',
                        boxShadow: i === 0 ? '0 0 5px var(--color-accent)' : 'none',
                      }}
                    />
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: i === 0 ? 600 : 400, color: i === 0 ? 'var(--dtext)' : 'var(--dmuted)' }}>
                        {event.title}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--dfaint)', marginTop: '2px' }}>{event.timestamp}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Jobs Waiting */}
          <section>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '18px', fontWeight: 400, color: '#645C50', margin: 0 }}>
                Jobs Waiting on You
              </h2>
              <span style={{ fontSize: '12px', color: 'var(--dfaint)' }}>{jobs.length} to review</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
              {jobs.slice(0, 3).map((job, i) => (
                <div
                  key={job.id}
                  className="inset-panel"
                  onClick={() => setSelectedJob(job)}
                  style={{
                    borderRadius: '24px',
                    background: 'var(--dcard)',
                    padding: '22px',
                    transition: 'box-shadow .25s',
                    animation: `ainFadeUp .6s cubic-bezier(.2,.8,.2,1) ${(i + 1) * 0.06}s backwards`,
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '180px',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLDivElement).style.boxShadow = 'inset 0 2px 6px rgba(32,30,29,.1), inset 0 -1px 0 rgba(255,255,255,.3)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.boxShadow = 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                    <div>
                      <div style={{ fontSize: '12px', color: 'var(--dfaint)', fontWeight: 600 }}>{job.company}</div>
                      <div style={{ fontFamily: 'var(--font-heading)', fontSize: '17px', color: 'var(--text)', marginTop: '3px' }}>
                        {job.title}
                      </div>
                    </div>
                    {/* Fit Score Circle */}
                    <div style={{ position: 'relative', width: '52px', height: '52px', flex: '0 0 52px' }}>
                      <svg width="52" height="52" viewBox="0 0 64 64" style={{ transform: 'rotate(-90deg)' }}>
                        <circle cx="32" cy="32" r="26" fill="none" stroke="var(--dtrack)" strokeWidth="5" />
                        <circle cx="32" cy="32" r="26" fill="none" stroke={getScoreRingColor(job.fit_score || 75)} strokeWidth="5" strokeLinecap="round" strokeDasharray={`${163.36 * ((job.fit_score || 75) / 100)} ${163.36}`} />
                      </svg>
                      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 700, color: getScoreRingColor(job.fit_score || 75) }}>
                        {job.fit_score || 75}
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: 'auto' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                      <span className="inset-chip" style={{ fontSize: '11px', color: 'var(--color-accent-2-800)', borderRadius: '999px', padding: '4px 12px' }}>
                        {job.modality || 'Remote'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        style={{
                          flex: 1,
                          padding: '10px 0',
                          borderRadius: '999px',
                          border: 'none',
                          background: 'var(--dbg)',
                          color: 'var(--dmuted)',
                          font: '700 12.5px var(--font-body)',
                          cursor: 'pointer',
                          boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
                        }}
                      >
                        Details
                      </button>
                      <button
                        style={{
                          flex: 1,
                          padding: '10px 0',
                          borderRadius: '999px',
                          border: 'none',
                          background: 'var(--dbg)',
                          color: '#7a8a5e',
                          font: '700 12.5px var(--font-body)',
                          cursor: 'pointer',
                          boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)',
                        }}
                      >
                        Approve
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Job Details Modal */}
          {selectedJob && (
            <>
              <div
                style={{
                  position: 'fixed',
                  inset: 0,
                  backgroundColor: 'rgba(0,0,0,.5)',
                  zIndex: 40,
                  backdropFilter: 'blur(2px)',
                }}
                onClick={() => setSelectedJob(null)}
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
                  backgroundColor: 'var(--dcard)',
                  borderRadius: '24px',
                  padding: '32px',
                  overflowY: 'auto',
                  zIndex: 50,
                  boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)',
                }}
              >
                <button
                  onClick={() => setSelectedJob(null)}
                  style={{
                    position: 'absolute',
                    top: '20px',
                    right: '20px',
                    background: 'none',
                    border: 'none',
                    fontSize: '24px',
                    cursor: 'pointer',
                    color: 'var(--dmuted)',
                  }}
                >
                  ✕
                </button>

                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '24px', color: 'var(--text)', margin: '0 0 8px', paddingRight: '30px' }}>
                  {selectedJob.title}
                </h2>
                <p style={{ fontSize: '14px', color: 'var(--dmuted)', margin: '0 0 24px' }}>
                  {selectedJob.company}
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid var(--dborder)' }}>
                  <div>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--faint)', marginBottom: '4px' }}>Location</div>
                    <p style={{ fontSize: '14px', color: 'var(--text)', margin: 0 }}>{selectedJob.location || 'N/A'}</p>
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--faint)', marginBottom: '4px' }}>Modality</div>
                    <p style={{ fontSize: '14px', color: 'var(--text)', margin: 0 }}>{selectedJob.modality || 'Unknown'}</p>
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--faint)', marginBottom: '4px' }}>Fit Score</div>
                    <p style={{ fontSize: '14px', color: 'var(--text)', margin: 0, fontWeight: 700 }}>{selectedJob.fit_score || 75}%</p>
                  </div>
                </div>

                {(selectedJob.strengths || selectedJob.gaps) && (
                  <div style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid var(--dborder)' }}>
                    {selectedJob.strengths && selectedJob.strengths.length > 0 && (
                      <div style={{ marginBottom: '16px' }}>
                        <h3 style={{ fontSize: '12px', fontWeight: 700, color: '#7A8A5E', margin: '0 0 8px', textTransform: 'uppercase' }}>✓ Strengths</h3>
                        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: 'var(--dmuted)' }}>
                          {selectedJob.strengths.map((s, i) => <li key={i} style={{ marginBottom: '4px' }}>{s}</li>)}
                        </ul>
                      </div>
                    )}
                    {selectedJob.gaps && selectedJob.gaps.length > 0 && (
                      <div>
                        <h3 style={{ fontSize: '12px', fontWeight: 700, color: '#C67139', margin: '0 0 8px', textTransform: 'uppercase' }}>✗ Gaps</h3>
                        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: 'var(--dmuted)' }}>
                          {selectedJob.gaps.map((g, i) => <li key={i} style={{ marginBottom: '4px' }}>{g}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {selectedJob.description_raw && (
                  <div style={{ marginBottom: '24px' }}>
                    <h3 style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text)', margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: '.06em' }}>Description</h3>
                    <p style={{ fontSize: '13px', color: 'var(--dmuted)', margin: 0, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                      {selectedJob.description_raw.substring(0, 500)}
                      {selectedJob.description_raw.length > 500 && '...'}
                    </p>
                  </div>
                )}

                <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
                  <button
                    onClick={() => setSelectedJob(null)}
                    style={{
                      flex: 1,
                      padding: '12px 16px',
                      borderRadius: '999px',
                      border: 'none',
                      background: 'var(--dbg)',
                      color: 'var(--dmuted)',
                      font: '600 13px var(--font-body)',
                      cursor: 'pointer',
                      boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
                    }}
                  >
                    Dismiss
                  </button>
                  <button
                    style={{
                      flex: 1,
                      padding: '12px 16px',
                      borderRadius: '999px',
                      border: 'none',
                      background: 'var(--dbg)',
                      color: '#c67139',
                      font: '700 13px var(--font-body)',
                      cursor: 'pointer',
                      boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)',
                    }}
                  >
                    Approve
                  </button>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
