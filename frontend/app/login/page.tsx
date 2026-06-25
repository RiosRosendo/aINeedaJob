'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Mail, Lock } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();

      // Save token to localStorage
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user_id', data.user_id);

      // Save token to cookie (30 minutes = 1800 seconds)
      document.cookie = `access_token=${data.access_token}; path=/; max-age=1800`;

      // Redirect to dashboard
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg)' }}>
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
            Welcome Back
          </h1>
          <p style={{ color: 'var(--muted)' }}>
            Sign in to your aINeedJob account
          </p>
        </div>

        {/* Card */}
        <div
          className="border rounded-lg p-8"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          {/* Error Message */}
          {error && (
            <div
              className="mb-6 p-4 border rounded-lg"
              style={{
                borderColor: '#dc2626',
                backgroundColor: 'rgba(220, 38, 38, 0.1)',
                color: '#dc2626',
              }}
            >
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            {/* Email */}
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--text)' }}
              >
                Email
              </label>
              <div
                className="flex items-center gap-3 border rounded-lg px-4 py-3"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--bg)',
                }}
              >
                <Mail size={18} style={{ color: 'var(--muted)' }} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="flex-1 outline-none text-sm"
                  style={{
                    backgroundColor: 'transparent',
                    color: 'var(--text)',
                  }}
                  required
                  disabled={loading}
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--text)' }}
              >
                Password
              </label>
              <div
                className="flex items-center gap-3 border rounded-lg px-4 py-3"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--bg)',
                }}
              >
                <Lock size={18} style={{ color: 'var(--muted)' }} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="flex-1 outline-none text-sm"
                  style={{
                    backgroundColor: 'transparent',
                    color: 'var(--text)',
                  }}
                  required
                  disabled={loading}
                />
              </div>
            </div>

            {/* Login Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg font-medium text-sm transition-all mt-6"
              style={{
                backgroundColor: 'var(--primary-bg)',
                color: 'var(--primary-text)',
                opacity: loading ? 0.6 : 1,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Divider */}
          <div
            className="my-6 flex items-center gap-4"
            style={{
              color: 'var(--border)',
            }}
          >
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border)' }} />
            <span style={{ color: 'var(--muted)', fontSize: '12px' }}>or</span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border)' }} />
          </div>

          {/* Register Link */}
          <p style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '14px' }}>
            Don't have an account?{' '}
            <Link
              href="/register"
              style={{
                color: 'var(--primary-bg)',
                textDecoration: 'none',
                fontWeight: '500',
              }}
            >
              Sign up
            </Link>
          </p>
        </div>

        {/* Footer */}
        <div
          style={{
            textAlign: 'center',
            marginTop: '24px',
            color: 'var(--faint)',
            fontSize: '12px',
          }}
        >
          <p>aINeedJob © 2026. Autonomous career agent.</p>
        </div>
      </div>
    </div>
  );
}
