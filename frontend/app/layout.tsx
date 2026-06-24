import type { Metadata } from 'next';
import { Sidebar } from '@/components/Sidebar';
import './globals.css';

export const metadata: Metadata = {
  title: 'aINeedJob Dashboard',
  description: 'Autonomous job search and application agent',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        style={{
          backgroundColor: 'var(--bg)',
          color: 'var(--text)',
        }}
      >
        <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--bg)' }}>
          <Sidebar />
          <main
            className="flex-1 overflow-y-auto"
            style={{ backgroundColor: 'var(--bg)' }}
          >
            <div className="max-w-5xl mx-auto px-12 py-10 pb-16">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
