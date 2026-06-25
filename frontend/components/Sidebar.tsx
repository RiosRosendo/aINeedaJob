'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { getApplications } from '@/lib/api';

interface NavItem {
  label: string;
  href: string;
  badge?: number;
}

const NAV_ITEMS_BASE: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Jobs', href: '/jobs' },
  { label: 'Approvals', href: '/approvals' },
  { label: 'Applications', href: '/applications' },
  { label: 'Profile', href: '/profile' },
];

export function Sidebar() {
  const pathname = usePathname();
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [approvalsCount, setApprovalsCount] = useState<number>(0);
  const [navItems, setNavItems] = useState<NavItem[]>(NAV_ITEMS_BASE);

  useEffect(() => {
    const loadApprovalsCount = async () => {
      try {
        // Get all applications (high limit to ensure we get all pending approvals)
        const applications = await getApplications(1000);
        const count = applications.filter(app => app.status === 'pending_approval').length;
        setApprovalsCount(count);
        setNavItems(NAV_ITEMS_BASE.map(item =>
          item.href === '/approvals' && count > 0 ? { ...item, badge: count } : item
        ));
      } catch (error) {
        console.error('Failed to load approvals count:', error);
      }
    };

    loadApprovalsCount();
  }, []);

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-60 border-r flex flex-col"
      style={{
        borderColor: 'var(--border-soft)',
        backgroundColor: 'var(--bg)',
      }}
    >
      {/* Logo */}
      <div
        className="h-16 flex items-center px-6 border-b"
        style={{ borderColor: 'var(--border-soft)' }}
      >
        <div
          className="w-6 h-6 border-2 rounded-md flex items-center justify-center mr-3"
          style={{ borderColor: 'var(--logo-border)' }}
        >
          <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: 'var(--text)' }} />
        </div>
        <span
          className="text-sm font-semibold tracking-tight"
          style={{ letterSpacing: '-0.02em', color: 'var(--text)' }}
        >
          aINeedJob
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4">
        {navItems.map((item, index) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');

          return (
            <Link
              key={item.href}
              href={item.href}
              className="relative block px-6 py-2.5 cursor-pointer transition-colors"
              style={{
                backgroundColor: isActive ? 'var(--sidebar-active)' : 'transparent',
              }}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <div className="flex items-center justify-between">
                <span
                  className="text-sm font-medium tracking-tight"
                  style={{
                    color: isActive ? 'var(--text)' : 'var(--muted)',
                    transition: 'color 0.18s',
                  }}
                >
                  {item.label}
                </span>
                {item.badge && (
                  <span
                    className="text-xs font-semibold px-2 py-1 rounded"
                    style={{
                      color: 'var(--accent)',
                      backgroundColor: 'var(--accent-bg)',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </div>

              {/* Hover/Active underline */}
              <div
                className="absolute bottom-1 left-6 h-1 bg-current rounded-sm transition-all"
                style={{
                  width:
                    isActive || hoveredIndex === index
                      ? 'calc(100% - 48px)'
                      : '0',
                  color: 'var(--text)',
                  transitionDuration: '0.28s',
                  transitionTimingFunction: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
                }}
              />
            </Link>
          );
        })}
      </nav>

      {/* Agent Status */}
      <div
        className="border-t p-4"
        style={{ borderColor: 'var(--border-soft)' }}
      >
        <div
          className="flex items-center gap-3 p-2.5 border rounded-lg"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          {/* Animated Equalizer */}
          <div className="flex items-end gap-1 h-3.5 w-3">
            <div
              className="w-0.5 rounded-sm"
              style={{
                height: '8px',
                backgroundColor: 'var(--text)',
                animation: 'equalizer-a 1.05s ease-in-out infinite',
              }}
            />
            <div
              className="w-0.5 rounded-sm"
              style={{
                height: '8px',
                backgroundColor: 'var(--text)',
                animation: 'equalizer-b 1.35s ease-in-out infinite',
              }}
            />
            <div
              className="w-0.5 rounded-sm"
              style={{
                height: '8px',
                backgroundColor: 'var(--text)',
                animation: 'equalizer-c 0.92s ease-in-out infinite',
              }}
            />
          </div>

          {/* Status Text */}
          <div className="flex flex-col gap-0.5 flex-1">
            <span
              className="text-xs font-medium"
              style={{ color: 'var(--text)' }}
            >
              Agent running
            </span>
            <span
              className="text-xs"
              style={{ color: 'var(--faint)', letterSpacing: '0.01em' }}
            >
              Active · scanning roles
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
