'use client';

import { usePathname } from 'next/navigation';
import { Sidebar } from '@/components/Sidebar';
import { ScoutProvider } from '@/contexts/ScoutContext';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const showSidebar = !pathname.startsWith('/dashboard') && !pathname.startsWith('/profile') && !pathname.startsWith('/applications') && !pathname.startsWith('/jobs') && !pathname.startsWith('/approvals') && !pathname.startsWith('/activity') && !pathname.startsWith('/auth');
  const isDashboard = pathname.startsWith('/dashboard');
  const isProfile = pathname.startsWith('/profile');
  const isApplications = pathname.startsWith('/applications');
  const isJobs = pathname.startsWith('/jobs');
  const isApprovals = pathname.startsWith('/approvals');
  const isActivity = pathname.startsWith('/activity');
  const isAuth = pathname.startsWith('/auth');

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
      </head>
      <body
        style={{
          backgroundColor: 'var(--bg)',
          color: 'var(--text)',
        }}
      >
        <ScoutProvider>
          <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--bg)' }}>
            {showSidebar && <Sidebar />}
            <main
              className="flex-1 overflow-y-auto"
              style={{ backgroundColor: 'var(--bg)' }}
            >
              {isDashboard || isProfile || isApplications || isJobs || isApprovals || isActivity || isAuth ? children : (
                <div className="max-w-5xl mx-auto px-12 py-10 pb-16">
                  {children}
                </div>
              )}
            </main>
          </div>
        </ScoutProvider>
      </body>
    </html>
  );
}
