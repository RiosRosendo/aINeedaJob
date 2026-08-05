'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Mail, Lock, User } from 'lucide-react';
import './auth.css';

export default function AuthPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogin = async () => {
    const res = await fetch('http://localhost:8001/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('access_token', data.access_token);
      document.cookie = `access_token=${data.access_token}; path=/`;
      router.push('/dashboard');
    } else {
      setError(data.detail || 'Login failed');
    }
  };

  const handleRegister = async () => {
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    const res = await fetch('http://localhost:8001/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (res.ok) {
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('access_token', data.access_token);
      document.cookie = `access_token=${data.access_token}; path=/`;
      router.push('/onboarding');
    } else {
      setError(data.detail || 'Registration failed');
    }
  };

  if (!mounted) return null;

  return (
    <div className="auth-container" suppressHydrationWarning>
      <div className="auth-card">
        <div className="auth-header">
          <div className="scout-mascot">
            <div className="scout-shadow"></div>
            <div className="scout-blob"></div>
            <div className="scout-highlight"></div>
            <div className="scout-eye scout-eye-left"></div>
            <div className="scout-eye scout-eye-right"></div>
            <div className="scout-mouth"></div>
          </div>
          <h1>{isLogin ? 'Welcome back' : 'Get started'}</h1>
          <p>{isLogin ? "Scout's been keeping watch — sign in to catch up" : 'Meet Scout — your autonomous job-search agent'}</p>
        </div>

        <div className="auth-form-card">
          {error && <div className="auth-error">{error}</div>}

          <div>
            {!isLogin && (
              <div className="form-group">
                <label className="form-label">Full name</label>
                <div className="form-field">
                  <User size={16} color="var(--faint)" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your name"
                  />
                </div>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Email</label>
              <div className="form-field">
                <Mail size={16} color="var(--faint)" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div className="form-field">
                <Lock size={16} color="var(--faint)" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              {!isLogin && <p style={{ fontSize: '11.5px', color: 'var(--faint)', margin: '6px 0 0' }}>At least 8 characters recommended</p>}
            </div>

            {!isLogin && (
              <div className="form-group">
                <label className="form-label">Confirm password</label>
                <div className="form-field">
                  <Lock size={16} color="var(--faint)" />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
              </div>
            )}

            <button
              onClick={isLogin ? handleLogin : handleRegister}
              className="submit-button"
            >
              {isLogin ? 'Sign in' : 'Create account'}
            </button>
          </div>

          <div className="divider">
            <div className="divider-line"></div>
            <span className="divider-text">or</span>
            <div className="divider-line"></div>
          </div>

          <p className="auth-toggle">
            {isLogin ? "Don't have an account? " : 'Already have an account? '}
            <a onClick={() => {setIsLogin(!isLogin); setError('');}}>
              {isLogin ? 'Sign up' : 'Sign in'}
            </a>
          </p>
        </div>

        <p className="auth-footer">aiNeedJob © 2026. Autonomous career agent.</p>
      </div>
    </div>
  );
}
