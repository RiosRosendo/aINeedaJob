'use client';

import { useState } from 'react';
import { Mail, Lock, User } from 'lucide-react';

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirm, setRegisterConfirm] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8001/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginEmail, password: loginPassword }),
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.detail || 'Login failed');
        setLoading(false);
        return;
      }

      const data = await response.json();
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('access_token', data.access_token);
      window.location.href = '/dashboard';
    } catch (err) {
      setError('Connection failed. Please try again.');
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (registerPassword !== registerConfirm) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    if (registerPassword.length < 8) {
      setError('Password must be at least 8 characters');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('http://localhost:8001/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: registerName,
          email: registerEmail,
          password: registerPassword,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.detail || 'Registration failed');
        setLoading(false);
        return;
      }

      const data = await response.json();
      localStorage.setItem('user_id', data.user_id);
      localStorage.setItem('access_token', data.access_token);
      window.location.href = '/onboarding';
    } catch (err) {
      setError('Connection failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
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

          <form onSubmit={isLogin ? handleLogin : handleRegister}>
            {!isLogin && (
              <div className="form-group">
                <label className="form-label">Full name</label>
                <div className="form-field">
                  <User size={16} color="var(--faint)" />
                  <input
                    type="text"
                    value={registerName}
                    onChange={(e) => setRegisterName(e.target.value)}
                    placeholder="Your name"
                    required
                    disabled={loading}
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
                  value={isLogin ? loginEmail : registerEmail}
                  onChange={(e) => (isLogin ? setLoginEmail(e.target.value) : setRegisterEmail(e.target.value))}
                  placeholder="you@example.com"
                  required
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div className="form-field">
                <Lock size={16} color="var(--faint)" />
                <input
                  type="password"
                  value={isLogin ? loginPassword : registerPassword}
                  onChange={(e) => (isLogin ? setLoginPassword(e.target.value) : setRegisterPassword(e.target.value))}
                  placeholder="••••••••"
                  required
                  disabled={loading}
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
                    value={registerConfirm}
                    onChange={(e) => setRegisterConfirm(e.target.value)}
                    placeholder="••••••••"
                    required
                    disabled={loading}
                  />
                </div>
              </div>
            )}

            <button type="submit" className="submit-button" disabled={loading}>
              {loading ? (isLogin ? 'Signing in…' : 'Creating account…') : isLogin ? 'Sign in' : 'Create account'}
            </button>
          </form>

          <div className="divider">
            <div className="divider-line"></div>
            <span className="divider-text">or</span>
            <div className="divider-line"></div>
          </div>

          <p className="auth-toggle">
            {isLogin ? "Don't have an account? " : 'Already have an account? '}
            <a onClick={() => setIsLogin(!isLogin)}>{isLogin ? 'Sign up' : 'Sign in'}</a>
          </p>
        </div>

        <p className="auth-footer">aiNeedJob © 2026. Autonomous career agent.</p>
      </div>
    </div>
  );
}
