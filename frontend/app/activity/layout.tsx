'use client';

import './activity.css';
import { ScoutSidebar } from '@/components/ScoutSidebar';

export default function ActivityLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=Caprasimo&family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <ScoutSidebar isDark={false} setIsDark={() => {}} sidebarOpen={true} setSidebarOpen={() => {}} stats={{ needs_approval: 0 }} />
        <main style={{ flex: 1, overflowY: 'auto', backgroundColor: 'var(--bg)' }}>
          {children}
        </main>
      </div>
    </>
  );
}
