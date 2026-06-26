'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, Check, ChevronRight, ChevronLeft, Loader } from 'lucide-react';

type Step = 1 | 2 | 3 | 4;

interface ExtractedData {
  skills: string[];
  roles: string[];
  experience_years: number;
  education: string[];
  projects: string[];
  languages: string[];
  summary: string;
}

interface OnboardingState {
  extracted_data: ExtractedData | null;
  target_roles: string[];
  preferred_countries: string[];
  preferred_modality: 'remote' | 'hybrid' | 'on-site' | null;
  salary_min: number;
  countryInput: string;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [state, setState] = useState<OnboardingState>({
    extracted_data: null,
    target_roles: [],
    preferred_countries: ['US'],
    preferred_modality: 'remote',
    salary_min: 0,
    countryInput: '',
  });

  const handleCVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8001/api/cv/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'x-user-id': localStorage.getItem('user_id') || '',
        },
        body: formData,
      });

      if (!response.ok) {
        const error_data = await response.json();
        throw new Error(error_data.detail || 'Failed to upload CV');
      }

      const data = await response.json();
      setState(prev => ({
        ...prev,
        extracted_data: data.extracted_data,
        target_roles: data.extracted_data.roles.slice(0, 3), // Top 3 roles
      }));

      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process CV');
    } finally {
      setLoading(false);
    }
  };

  const saveProfile = async () => {
    setLoading(true);
    setError(null);

    try {
      const payload = {
        target_roles: state.target_roles,
        tech_stack: state.extracted_data?.skills || [],
        preferred_countries: state.preferred_countries,
        preferred_modality: state.preferred_modality,
        salary_min: state.salary_min || null,
      };

      console.log('[ONBOARDING] Saving profile with payload:', payload);

      const response = await fetch('http://localhost:8001/api/users/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'x-user-id': localStorage.getItem('user_id') || '',
        },
        body: JSON.stringify(payload),
      });

      console.log('[ONBOARDING] Profile save response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        console.log('[ONBOARDING] Profile save error response:', errorData);
        throw new Error(errorData.detail || 'Failed to save profile');
      }

      const data = await response.json();
      console.log('[ONBOARDING] Profile saved successfully:', data);
      setStep(4);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to save profile';
      console.log('[ONBOARDING] Profile save error:', errorMsg);
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('[ONBOARDING] Triggering job search with roles:', state.target_roles);

      const response = await fetch('http://localhost:8001/api/jobs/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'x-user-id': localStorage.getItem('user_id') || '',
        },
        body: JSON.stringify({
          user_id: localStorage.getItem('user_id'),
          roles: state.target_roles && state.target_roles.length > 0 ? state.target_roles : ['AI Engineer'],
        }),
      });

      console.log('[ONBOARDING] Job search triggered, status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        console.log('[ONBOARDING] Job search error:', errorData);
      }

      // Redirect to dashboard regardless of search result
      router.push('/dashboard');
    } catch (err) {
      console.log('[ONBOARDING] Job search failed:', err);
      // Still redirect to dashboard even if search fails
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg)' }}>
      <div className="w-full max-w-2xl mx-auto px-6">
        {/* Progress Bar */}
        <div className="mb-12">
          <div className="flex justify-between mb-4">
            {[1, 2, 3, 4].map((s) => (
              <div key={s} className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-all ${
                    s < step
                      ? 'bg-green-500 text-white'
                      : s === step
                      ? 'bg-blue-500 text-white'
                      : 'border-2 border-gray-600 text-gray-600'
                  }`}
                  style={{
                    backgroundColor:
                      s < step
                        ? '#10b981'
                        : s === step
                        ? 'var(--primary-bg)'
                        : 'transparent',
                    borderColor:
                      s <= step ? 'transparent' : 'var(--border)',
                    color: s <= step ? 'white' : 'var(--muted)',
                  }}
                >
                  {s < step ? <Check size={18} /> : s}
                </div>
                {s < 4 && (
                  <div
                    className="w-8 h-0.5"
                    style={{
                      backgroundColor:
                        s < step ? '#10b981' : 'var(--border)',
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div
          className="border rounded-2xl p-8"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
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

          {/* Step 1: Upload CV */}
          {step === 1 && (
            <div>
              <h2 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
                Upload Your CV
              </h2>
              <p style={{ color: 'var(--muted)', marginBottom: '24px' }}>
                Let's start by uploading your resume. We'll extract your skills, experience, and roles automatically.
              </p>

              <div
                className="border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all hover:border-opacity-100"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'rgba(var(--primary-bg-rgb), 0.03)',
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={40} style={{ color: 'var(--muted)', margin: '0 auto 12px' }} />
                <p className="font-medium mb-2" style={{ color: 'var(--text)' }}>
                  Drag and drop your PDF here
                </p>
                <p style={{ color: 'var(--muted)', fontSize: '14px' }}>
                  or click to select a file
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleCVUpload}
                  className="hidden"
                />
              </div>

              <p style={{ color: 'var(--faint)', fontSize: '12px', marginTop: '16px' }}>
                We support PDF files up to 10MB
              </p>
            </div>
          )}

          {/* Step 2: Review Profile */}
          {step === 2 && state.extracted_data && (
            <div>
              <h2 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
                Review Your Profile
              </h2>
              <p style={{ color: 'var(--muted)', marginBottom: '24px' }}>
                We've extracted the following information from your CV. Review and adjust as needed.
              </p>

              <div className="space-y-6">
                {/* Summary */}
                <div>
                  <label style={{ color: 'var(--text)', fontSize: '14px', fontWeight: 500 }}>
                    Professional Summary
                  </label>
                  <p style={{ color: 'var(--muted)', marginTop: '6px' }}>
                    {state.extracted_data.summary || 'No summary found'}
                  </p>
                </div>

                {/* Experience */}
                <div>
                  <label style={{ color: 'var(--text)', fontSize: '14px', fontWeight: 500 }}>
                    Years of Experience
                  </label>
                  <p style={{ color: 'var(--muted)', marginTop: '6px' }}>
                    {state.extracted_data.experience_years} years
                  </p>
                </div>

                {/* Top Roles */}
                <div>
                  <label style={{ color: 'var(--text)', fontSize: '14px', fontWeight: 500 }}>
                    Target Roles
                  </label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {state.extracted_data.roles.map((role, i) => (
                      <span
                        key={i}
                        className="px-3 py-1.5 rounded-full text-sm font-medium"
                        style={{
                          backgroundColor: 'var(--primary-bg)',
                          color: 'var(--primary-text)',
                        }}
                      >
                        {role}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Skills */}
                <div>
                  <label style={{ color: 'var(--text)', fontSize: '14px', fontWeight: 500 }}>
                    Key Skills ({state.extracted_data.skills.length})
                  </label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {state.extracted_data.skills.slice(0, 10).map((skill, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1.5 rounded-lg text-xs border"
                        style={{
                          borderColor: 'var(--border)',
                          color: 'var(--muted)',
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                    {state.extracted_data.skills.length > 10 && (
                      <span style={{ color: 'var(--faint)', fontSize: '12px', marginTop: '4px' }}>
                        +{state.extracted_data.skills.length - 10} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Preferences */}
          {step === 3 && (
            <PreferencesStep state={state} setState={setState} />
          )}

          {/* Step 4: Complete */}
          {step === 4 && (
            <div className="text-center">
              {loading ? (
                <>
                  <div
                    className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
                    style={{ backgroundColor: 'var(--primary-bg)' }}
                  >
                    <Loader size={32} color="white" className="animate-spin" />
                  </div>
                  <h2 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
                    Finding jobs for you...
                  </h2>
                  <p style={{ color: 'var(--muted)', marginBottom: '24px' }}>
                    Analyzing your profile and searching our database.
                  </p>
                </>
              ) : (
                <>
                  <div
                    className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
                    style={{ backgroundColor: '#10b981' }}
                  >
                    <Check size={32} color="white" />
                  </div>
                  <h2 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
                    All Set!
                  </h2>
                  <p style={{ color: 'var(--muted)', marginBottom: '24px' }}>
                    Your profile is ready. Redirecting to dashboard...
                  </p>
                </>
              )}
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex gap-3 mt-8 pt-8 border-t" style={{ borderColor: 'var(--border)' }}>
            {step > 1 && step < 4 && (
              <button
                onClick={() => setStep((step - 1) as Step)}
                className="flex-1 py-3 rounded-lg border font-medium transition-all flex items-center justify-center gap-2"
                style={{
                  borderColor: 'var(--border)',
                  color: 'var(--text)',
                  backgroundColor: 'var(--bg)',
                }}
              >
                <ChevronLeft size={18} />
                Back
              </button>
            )}

            {step < 3 && (
              <button
                onClick={() => setStep((step + 1) as Step)}
                disabled={loading || (step === 1 && !state.extracted_data)}
                className="flex-1 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  backgroundColor: 'var(--primary-bg)',
                  color: 'var(--primary-text)',
                }}
              >
                {loading ? <Loader size={18} className="animate-spin" /> : <ChevronRight size={18} />}
                {loading ? 'Processing...' : 'Continue'}
              </button>
            )}

            {step === 3 && (
              <>
                <button
                  onClick={handleComplete}
                  className="flex-1 py-3 rounded-lg border font-medium transition-all"
                  style={{
                    borderColor: 'var(--border)',
                    color: 'var(--text)',
                    backgroundColor: 'var(--bg)',
                  }}
                >
                  Skip
                </button>
                <button
                  onClick={saveProfile}
                  disabled={loading}
                  className="flex-1 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: 'var(--primary-bg)',
                    color: 'var(--primary-text)',
                  }}
                >
                  {loading ? <Loader size={18} className="animate-spin" /> : <Check size={18} />}
                  {loading ? 'Saving...' : 'Complete Setup'}
                </button>
              </>
            )}

            {step === 4 && (
              <button
                onClick={handleComplete}
                className="flex-1 py-3 rounded-lg font-medium transition-all"
                style={{
                  backgroundColor: 'var(--primary-bg)',
                  color: 'var(--primary-text)',
                }}
              >
                Go to Dashboard
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface PreferencesStepProps {
  state: OnboardingState;
  setState: React.Dispatch<React.SetStateAction<OnboardingState>>;
}

function PreferencesStep({ state, setState }: PreferencesStepProps) {
  const suggestedCountries = ['US', 'Canada', 'Mexico', 'Japan', 'Remote'];

  const handleAddCountry = () => {
    const trimmed = state.countryInput.trim().toUpperCase();
    if (trimmed && !state.preferred_countries.includes(trimmed)) {
      setState(prev => ({
        ...prev,
        preferred_countries: [...prev.preferred_countries, trimmed],
        countryInput: '',
      }));
    }
  };

  const handleRemoveCountry = (country: string) => {
    setState(prev => ({
      ...prev,
      preferred_countries: prev.preferred_countries.filter(c => c !== country),
    }));
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
        Set Your Preferences
      </h2>
      <p style={{ color: 'var(--muted)', marginBottom: '24px' }}>
        Tell us about your ideal job to help us find better matches. (All optional)
      </p>

      <div className="space-y-6">
        {/* Modality */}
        <div>
          <label style={{ color: 'var(--text)', fontSize: '14px', fontWeight: 500, display: 'block', marginBottom: '10px' }}>
            Work Modality
          </label>
          <div className="grid grid-cols-4 gap-3">
            {(['Any', 'remote', 'hybrid', 'on-site'] as const).map((mod) => (
              <button
                key={mod}
                onClick={() => setState(prev => ({
                  ...prev,
                  preferred_modality: mod === 'Any' ? null : (mod as 'remote' | 'hybrid' | 'on-site')
                }))}
                className="p-3 rounded-lg border-2 transition-all text-center"
                style={{
                  borderColor:
                    (mod === 'Any' && state.preferred_modality === null) ||
                    state.preferred_modality === mod
                      ? 'var(--primary-bg)'
                      : 'var(--border)',
                  backgroundColor:
                    (mod === 'Any' && state.preferred_modality === null) ||
                    state.preferred_modality === mod
                      ? 'rgba(var(--primary-bg-rgb), 0.1)'
                      : 'transparent',
                  color: 'var(--text)',
                  fontSize: '14px',
                  fontWeight: 500,
                }}
              >
                {mod === 'Any' ? 'Any' : mod.charAt(0).toUpperCase() + mod.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Salary */}
        <div>
          <label style={{ color: 'var(--text)', fontSize: '14px', fontWeight: 500, display: 'block', marginBottom: '10px' }}>
            Minimum Salary (USD/year)
          </label>
          <input
            type="number"
            value={state.salary_min || ''}
            onChange={(e) => setState(prev => ({ ...prev, salary_min: parseInt(e.target.value) || 0 }))}
            placeholder="e.g., 100000"
            className="w-full px-4 py-3 rounded-lg border outline-none"
            style={{
              borderColor: 'var(--border)',
              backgroundColor: 'var(--bg)',
              color: 'var(--text)',
            }}
          />
        </div>

        {/* Countries */}
        <div>
          <label style={{ color: 'var(--text)', fontSize: '14px', fontWeight: 500, display: 'block', marginBottom: '10px' }}>
            Preferred Countries
          </label>

          {/* Input */}
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={state.countryInput}
              onChange={(e) => setState(prev => ({ ...prev, countryInput: e.target.value }))}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddCountry();
                }
              }}
              placeholder="Type country name and press Enter"
              className="flex-1 px-4 py-3 rounded-lg border outline-none"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
            <button
              onClick={handleAddCountry}
              className="px-4 py-3 rounded-lg font-medium"
              style={{
                backgroundColor: 'var(--primary-bg)',
                color: 'var(--primary-text)',
              }}
            >
              Add
            </button>
          </div>

          {/* Selected Countries */}
          <div className="flex flex-wrap gap-2 mb-3">
            {state.preferred_countries.map((country) => (
              <div
                key={country}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
                style={{
                  backgroundColor: 'var(--primary-bg)',
                  color: 'var(--primary-text)',
                }}
              >
                {country}
                <button
                  onClick={() => handleRemoveCountry(country)}
                  className="ml-1 hover:opacity-70 transition-opacity"
                  style={{ fontSize: '16px', lineHeight: '1' }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          {/* Suggestions */}
          <div>
            <p style={{ color: 'var(--faint)', fontSize: '12px', marginBottom: '8px' }}>
              Quick add:
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestedCountries.map((country) => (
                <button
                  key={country}
                  onClick={() => {
                    if (!state.preferred_countries.includes(country)) {
                      setState(prev => ({
                        ...prev,
                        preferred_countries: [...prev.preferred_countries, country],
                      }));
                    }
                  }}
                  className="px-2.5 py-1.5 rounded-lg text-xs border transition-all hover:border-opacity-100"
                  style={{
                    borderColor: 'var(--border)',
                    color: state.preferred_countries.includes(country) ? 'var(--primary-text)' : 'var(--muted)',
                    backgroundColor: state.preferred_countries.includes(country) ? 'var(--primary-bg)' : 'transparent',
                  }}
                >
                  {country}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
