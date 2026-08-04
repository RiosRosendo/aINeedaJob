'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ScoutLoading } from '@/components/ScoutLoading';
import { useScout } from '@/contexts/ScoutContext';

interface ActivityLog {
  id: string;
  agent: string;
  status: string;
  details?: any;
  created_at: string;
  job_id?: string;
  job_title?: string;
  job_company?: string;
  fit_score?: number;
}

type FilterType = 'all' | 'job_discovery' | 'job_parsing' | 'job_match' | 'verification' | 'decision' | 'autonomous_cycle' | 'cleanup';

const filterLabels: Record<FilterType, string> = {
  all: 'All',
  job_discovery: 'Discovery',
  job_parsing: 'Parsing',
  job_match: 'Scoring',
  verification: 'Verification',
  decision: 'Decisions',
  autonomous_cycle: 'Autonomous',
  cleanup: 'Cleanup',
};

const mapAgentToFilterType = (agent: string): FilterType => {
  if (agent === 'job_verification') return 'verification';
  if (agent === 'job_discovery') return 'job_discovery';
  if (agent === 'job_parsing') return 'job_parsing';
  if (agent === 'job_match') return 'job_match';
  if (agent === 'decision') return 'decision';
  if (agent === 'autonomous_cycle') return 'autonomous_cycle';
  if (agent === 'cleanup') return 'cleanup';
  return 'all';
};

const agentDisplayNames: Record<string, string> = {
  job_verification: 'Verification',
  job_discovery: 'Discovery',
  job_parsing: 'Parsing',
  job_match: 'Scoring',
  decision: 'Decision',
  autonomous_cycle: 'Autonomous',
  cleanup: 'Cleanup',
  verification: 'Verification',
};

export default function ActivityPage() {
  const router = useRouter();
  const { setIsLoading } = useScout();
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<FilterType>('all');
  const [counts, setCounts] = useState<Record<FilterType, number>>({
    all: 0,
    job_discovery: 0,
    job_parsing: 0,
    job_match: 0,
    verification: 0,
    decision: 0,
    autonomous_cycle: 0,
    cleanup: 0,
  });

  const fetchLogs = async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setIsLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const userId = localStorage.getItem('user_id');
      const accessToken = localStorage.getItem('access_token');

      const response = await fetch('http://localhost:8001/api/jobs/logs?limit=100', {
        headers: {
          'x-user-id': userId || '',
          'Authorization': `Bearer ${accessToken || ''}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('[ACTIVITY] Logs fetched:', data.length, data[0]);
        setLogs(data);
        applyFilter('all', data);
        updateCounts(data);
      }
    } catch (err) {
      console.error('Failed to fetch activity logs:', err);
    } finally {
      if (showLoading) {
        setLoading(false);
        setIsLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  };

  const updateCounts = (logData: ActivityLog[]) => {
    const newCounts: Record<FilterType, number> = {
      all: logData.length,
      job_discovery: 0,
      job_parsing: 0,
      job_match: 0,
      verification: 0,
      decision: 0,
      autonomous_cycle: 0,
      cleanup: 0,
    };

    logData.forEach((log) => {
      const filterType = mapAgentToFilterType(log.agent);
      if (filterType !== 'all') {
        newCounts[filterType]++;
      }
    });

    setCounts(newCounts);
  };

  const applyFilter = (filterType: FilterType, logData: ActivityLog[]) => {
    setFilter(filterType);
    if (filterType === 'all') {
      setFilteredLogs(logData);
    } else {
      setFilteredLogs(logData.filter((log) => mapAgentToFilterType(log.agent) === filterType));
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const getRelativeTime = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatActivityEvents = (logs: ActivityLog[]) => {
    return logs.map((log, index) => {
      const details = log.details || {};
      let title = '';

      if (log.agent === 'job_discovery' && log.status === 'success') {
        title = `Found ${details.count || details.jobs_count || 'new'} roles matching your profile`;
      } else if (log.agent === 'job_discovery' && log.status === 'failed') {
        title = 'Failed to discover new jobs';
      } else if (log.agent === 'job_parsing' && log.status === 'success') {
        const jobName = details.title || details.job_title || 'Job';
        title = `Parsed: ${jobName.substring(0, 40)}`;
      } else if (log.agent === 'job_parsing' && log.status === 'failed') {
        title = 'Failed to parse job description';
      } else if (log.agent === 'job_match' && log.status === 'success') {
        const jobName = log.job_title || 'Position';
        const company = log.job_company || 'Company';
        const score = log.fit_score || '?';
        title = `Scored job — ${jobName} at ${company} (${score}%)`;
      } else if (log.agent === 'job_match' && log.status === 'failed') {
        title = 'Failed to score job';
      } else if (log.agent === 'autonomous_cycle') {
        const action = details.action || log.status;
        title = `Autonomous cycle: ${action}${details.reasoning ? ' — ' + details.reasoning.substring(0, 40) : ''}`;
      } else if (log.agent === 'decision') {
        const jobName = log.job_title || details.title || '';
        const company = log.job_company || details.company || '';
        const action = details.decision || details.action || log.status;
        const location = company ? ` at ${company}` : '';
        title = `${action}${jobName ? ` — ${jobName}${location}` : ''}`;
      } else if (log.agent === 'cleanup' && log.status === 'success') {
        title = `Cleaned up ${details.duplicates_deleted || 0} duplicate jobs`;
      } else if (log.agent === 'verification' && log.status === 'success') {
        title = `Verified job URL — ${details.reason || 'active'}`;
      } else if (log.agent === 'verification' && log.status === 'expired') {
        title = `Job URL expired — ${details.reason || 'no longer available'}`;
      } else if (log.agent === 'job_verification') {
        const status = details.verified ? 'active' : 'expired';
        const reason = details.reason || '';
        const jobName = log.job_title || '';
        title = jobName
          ? `Verified ${jobName} — ${status}`
          : `Job ${status}${reason ? ' (' + reason + ')' : ''}`;
      } else {
        title = `${log.agent.charAt(0).toUpperCase() + log.agent.slice(1)} — ${log.status}`;
      }

      const timestamp = getRelativeTime(new Date(log.created_at));

      return { title, timestamp, isLatest: index === 0 };
    });
  };

  if (loading) {
    return <ScoutLoading message="Loading activity..." />;
  }

  return (
    <div className="activity-container">
      <div className="activity-header">
        <a className="activity-back-link" onClick={() => router.back()} style={{ color: 'var(--color-accent)' }}>
          ← Back to Dashboard
        </a>

        <div className="activity-title-row">
          <div>
            <h1>Agent activity</h1>
            <p className="activity-subtitle">Everything Scout has done, most recent first</p>
          </div>
          <button className="activity-refresh-btn" onClick={() => fetchLogs(false)} disabled={refreshing}>
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="activity-filters">
        {(Object.keys(filterLabels) as FilterType[]).map((filterType) => (
          <button
            key={filterType}
            className={`filter-tab ${filter === filterType ? 'active' : ''}`}
            onClick={() => applyFilter(filterType, logs)}
          >
            {filterLabels[filterType]}
            <span className="filter-count">({counts[filterType]})</span>
          </button>
        ))}
      </div>

      {filteredLogs.length === 0 ? (
        <div className="activity-empty">
          <div className="activity-empty-title">No activity yet</div>
          <p className="activity-empty-subtitle">Start searching to see Scout's work here</p>
        </div>
      ) : (
        <div style={{ background: 'var(--card)', borderRadius: '16px', padding: '16px' }}>
          {filteredLogs.map((event, i) => (
            <div key={i} style={{ display: 'flex', gap: '14px', padding: '10px 0', borderBottom: '1px solid rgba(32,30,29,.08)', animation: `ainSlideLeft .5s cubic-bezier(.2,.8,.2,1) ${i * 0.08}s backwards` }}>
              <div
                style={{
                  width: '6px',
                  flex: '0 0 6px',
                  borderRadius: '4px',
                  background: i === 0 ? 'var(--color-accent)' : 'var(--faint)',
                  alignSelf: 'stretch',
                  boxShadow: i === 0 ? '0 0 5px var(--color-accent)' : 'none',
                }}
              />
              <div>
                <div style={{ fontSize: '13px', fontWeight: i === 0 ? 600 : 400, color: i === 0 ? 'var(--text)' : 'var(--muted)' }}>
                  {formatActivityEvents([filteredLogs[i]])[0].title}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--faint)', marginTop: '2px' }}>
                  {formatActivityEvents([filteredLogs[i]])[0].timestamp}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
