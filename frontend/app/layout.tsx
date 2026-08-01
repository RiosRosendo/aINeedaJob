'use client';

import { usePathname } from 'next/navigation';
import { Sidebar } from '@/components/Sidebar';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const showSidebar = !pathname.startsWith('/dashboard');
  const isDashboard = pathname.startsWith('/dashboard');

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
        <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--bg)' }}>
          {showSidebar && <Sidebar />}
          <main
            className="flex-1 overflow-y-auto"
            style={{ backgroundColor: 'var(--bg)' }}
          >
            {isDashboard ? children : (
              <div className="max-w-5xl mx-auto px-12 py-10 pb-16">
                {children}
              </div>
            )}
          </main>
        </div>
      </body>
    </html>
  );
}
