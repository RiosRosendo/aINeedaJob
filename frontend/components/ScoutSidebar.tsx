'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Home, Briefcase, CheckCircle, FileText, User, LogOut, Sun, Moon } from 'lucide-react';

interface ScoutSidebarProps {
  isDark: boolean;
  setIsDark: (value: boolean) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (value: boolean) => void;
  stats?: { needs_approval: number };
}

const injectStyles = () => {
  if (typeof window === 'undefined') return;
  if (document.getElementById('scout-sidebar-styles')) return;

  const style = document.createElement('style');
  style.id = 'scout-sidebar-styles';
  style.textContent = `
    @keyframes ainBreathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }
    @keyframes ainLook { 0%, 12% { transform: translate(0, 0); } 20%, 32% { transform: translate(-3px, 1px); } 40%, 52% { transform: translate(3px, -1px); } 60%, 72% { transform: translate(-2px, 2px); } 80%, 100% { transform: translate(0, 0); } }
    @keyframes ainBlink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(0.15); } }
    @keyframes ainTalk { 0%, 100% { transform: scaleX(1) scaleY(1); } 30% { transform: scaleX(0.75) scaleY(1.3); } 55% { transform: scaleX(1.15) scaleY(0.7); } 80% { transform: scaleX(0.9) scaleY(1.1); } }
  `;
  document.head.appendChild(style);
};

export function ScoutSidebar({ isDark, setIsDark, sidebarOpen, setSidebarOpen, stats }: ScoutSidebarProps) {
  const pathname = usePathname();

  useEffect(() => {
    injectStyles();
  }, []);

  useEffect(() => {
    console.log('[SIDEBAR] Stats prop received:', stats);
  }, [stats]);

  const mascotSize = sidebarOpen ? 120 : 46;
  const eyeSize = Math.round(mascotSize * 0.08);
  const eyeLeft1 = '35%';
  const eyeLeft2 = '57%';
  const eyeTop = '38%';
  const mouthLeft = '32%';
  const mouthTop = '58%';
  const mouthW = '36%';
  const mouthH = Math.round(mascotSize * 0.08);
  const mouthBorder = sidebarOpen ? 2 : 1;

  return (
    <aside
      style={{
        width: sidebarOpen ? '250px' : '88px',
        flexBasis: sidebarOpen ? '250px' : '88px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '26px 0 20px',
        overflow: 'hidden',
        transition: 'width .38s cubic-bezier(.4,0,.2,1), flex-basis .38s cubic-bezier(.4,0,.2,1)',
        background: 'var(--bg)',
        borderRight: '1px solid var(--border)',
      }}
    >
      {/* Logo & Theme Toggle */}
      <div
        onClick={() => setSidebarOpen(!sidebarOpen)}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: sidebarOpen ? '6px' : '0',
          cursor: 'pointer',
          width: '100%',
          marginBottom: '26px',
        }}
      >
        <span style={{ fontFamily: 'var(--font-heading)', fontSize: '38px', fontWeight: 400, color: 'var(--text)', whiteSpace: 'nowrap', textAlign: 'left', lineHeight: '1', letterSpacing: '-2px', display: 'block', transition: 'all 0.38s cubic-bezier(.4,0,.2,1)' }}>
          {sidebarOpen ? 'aiNeedJob' : 'ai'}
        </span>
      </div>

      {/* Scout Mascot */}
      <div
        style={{
          position: 'relative',
          width: `${mascotSize}px`,
          height: `${mascotSize}px`,
          margin: `0 auto ${sidebarOpen ? '8px' : '16px'}`,
          display: 'block',
          transition: 'width .38s cubic-bezier(.4,0,.2,1), height .38s cubic-bezier(.4,0,.2,1), margin .38s cubic-bezier(.4,0,.2,1)',
        }}
      >
        {/* Shadow */}
        <div
          style={{
            position: 'absolute',
            left: '12%',
            bottom: '-10%',
            width: '76%',
            height: '16%',
            borderRadius: '50%',
            background: 'radial-gradient(ellipse, rgba(32,30,29,.32), transparent 70%)',
            filter: 'blur(2px)',
          }}
        />

        {/* Face */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '58% 42% 45% 55% / 45% 55% 45% 55%',
            background: `radial-gradient(circle at 30% 26%, var(--color-accent-200), var(--color-accent) 55%, var(--color-accent-700) 100%)`,
            animation: 'ainBreathe 3.2s ease-in-out infinite',
            boxShadow: '0 10px 20px -6px rgba(32,30,29,.4), inset 0 3px 6px rgba(255,255,255,.35), inset 0 -6px 10px rgba(64,35,16,.35)',
          }}
        />

        {/* Highlight */}
        <div
          style={{
            position: 'absolute',
            left: '18%',
            top: '14%',
            width: '26%',
            height: '16%',
            borderRadius: '50%',
            background: 'rgba(255,255,255,.45)',
            filter: 'blur(2px)',
          }}
        />

        {/* Eyes */}
        <div
          style={{
            position: 'absolute',
            left: eyeLeft1,
            top: eyeTop,
            width: `${eyeSize}px`,
            height: `${eyeSize}px`,
            borderRadius: '50%',
            background: 'var(--bg)',
            animation: 'ainLook 6s ease-in-out infinite, ainBlink 4.5s ease-in-out infinite',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: eyeLeft2,
            top: eyeTop,
            width: `${eyeSize}px`,
            height: `${eyeSize}px`,
            borderRadius: '50%',
            background: 'var(--bg)',
            animation: 'ainLook 6s ease-in-out infinite, ainBlink 4.5s ease-in-out infinite',
          }}
        />

        {/* Mouth */}
        <div
          style={{
            position: 'absolute',
            left: mouthLeft,
            top: mouthTop,
            width: mouthW,
            height: `${mouthH}px`,
            borderRadius: '0 0 16px 16px',
            borderBottom: `${mouthBorder}px solid var(--bg)`,
            animation: 'ainTalk 3.4s ease-in-out infinite',
          }}
        />
      </div>

      {sidebarOpen && (
        <>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: '19px', color: 'var(--text)', marginBottom: '3px', whiteSpace: 'nowrap', marginTop: '6px' }}>
            Scout
          </div>
          <div style={{ fontSize: '12px', color: 'var(--faint)', marginBottom: '26px', textAlign: 'center', padding: '0 20px', whiteSpace: 'nowrap' }}>
            on the clock — watching roles
          </div>
        </>
      )}

      {/* Nav */}
      <nav style={{ width: '100%', padding: '0 16px', display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: 'auto', boxSizing: 'border-box' }}>
        {[
          { icon: Home, label: 'Dashboard', href: '/dashboard', active: pathname === '/dashboard' },
          { icon: Briefcase, label: 'Jobs', href: '/jobs', active: pathname === '/jobs' },
          { icon: CheckCircle, label: 'Approvals', href: '/approvals', badge: stats?.needs_approval, active: pathname === '/approvals' },
          { icon: FileText, label: 'Applications', href: '/applications', active: pathname === '/applications' },
          { icon: User, label: 'Profile', href: '/profile', active: pathname === '/profile' },
        ].map((item, i) => (
          <a
            key={i}
            href={item.href}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '11px',
              padding: '11px 16px',
              background: item.active ? 'var(--card)' : 'transparent',
              textDecoration: 'none',
              borderRadius: '999px',
              transition: 'all .25s',
              boxShadow: item.active ? 'inset 0 2px 5px rgba(32,30,29,.18), inset 0 -1px 0 rgba(255,255,255,.5)' : 'none',
            }}
          >
            <item.icon size={17} style={{ flex: 'none', color: item.active ? 'var(--text)' : 'var(--muted)' }} />
            {sidebarOpen && (
              <>
                <span style={{ fontSize: '14px', fontWeight: item.active ? 700 : 400, color: item.active ? 'var(--text)' : 'var(--muted)', whiteSpace: 'nowrap' }}>
                  {item.label}
                </span>
                {(item.badge || 0) > 0 && (
                  <span style={{ marginLeft: 'auto', fontSize: '11px', fontWeight: 700, padding: '2px 9px', borderRadius: '999px', background: '#7a8a5e', color: '#ffffff' }}>
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </a>
        ))}
      </nav>

      {/* Theme Toggle */}
      {sidebarOpen && (
        <button
          onClick={() => setIsDark(!isDark)}
          style={{
            width: 'calc(100% - 32px)',
            marginTop: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-start',
            gap: '11px',
            padding: '11px 16px',
            borderRadius: '999px',
            border: 'none',
            background: 'var(--card)',
            color: 'var(--muted)',
            font: '400 14px var(--font-body)',
            cursor: 'pointer',
            boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18), inset 0 -1px 0 rgba(255,255,255,.5)',
            marginBottom: '8px',
          }}
        >
          {isDark ? <Sun size={17} /> : <Moon size={17} />}
          <span>{isDark ? 'Light' : 'Dark'}</span>
        </button>
      )}

      {/* Logout */}
      <button
        style={{
          width: 'calc(100% - 32px)',
          marginTop: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-start',
          gap: '11px',
          padding: '11px 16px',
          borderRadius: '999px',
          border: 'none',
          background: 'var(--card)',
          color: 'var(--muted)',
          font: '400 14px var(--font-body)',
          cursor: 'pointer',
          boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18), inset 0 -1px 0 rgba(255,255,255,.5)',
        }}
      >
        <LogOut size={17} style={{ flex: 'none' }} />
        {sidebarOpen && <span>Logout</span>}
      </button>
    </aside>
  );
}
