'use client';

import { useEffect, useState } from 'react';
import { getUserProfile, updateUserProfile } from '@/lib/api';
import { UserProfile } from '@/lib/types';
import { X } from 'lucide-react';

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState<Partial<UserProfile>>({});

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getUserProfile();

        setProfile(data);
        setFormData({
          target_roles: data.target_roles || [],
          tech_stack: data.tech_stack || [],
          preferred_countries: data.preferred_countries || [],
          preferred_modality: data.preferred_modality || null,
          salary_min: data.salary_min || 0,
        });
      } catch (err) {
        console.error('Failed to load profile:', err);
        setError('Failed to load profile. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);
      await updateUserProfile(formData);
      setProfile(formData as UserProfile);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save profile:', err);
      setError('Failed to save profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const addTargetRole = () => {
    const roles = formData.target_roles || [];
    setFormData({
      ...formData,
      target_roles: [...roles, ''],
    });
  };

  const removeTargetRole = (index: number) => {
    const roles = formData.target_roles || [];
    setFormData({
      ...formData,
      target_roles: roles.filter((_, i) => i !== index),
    });
  };

  const updateTargetRole = (index: number, value: string) => {
    const roles = formData.target_roles || [];
    const newRoles = [...roles];
    newRoles[index] = value;
    setFormData({
      ...formData,
      target_roles: newRoles,
    });
  };

  const addTechStack = () => {
    const stack = formData.tech_stack || [];
    setFormData({
      ...formData,
      tech_stack: [...stack, ''],
    });
  };

  const removeTechStack = (index: number) => {
    const stack = formData.tech_stack || [];
    setFormData({
      ...formData,
      tech_stack: stack.filter((_, i) => i !== index),
    });
  };

  const updateTechStack = (index: number, value: string) => {
    const stack = formData.tech_stack || [];
    const newStack = [...stack];
    newStack[index] = value;
    setFormData({
      ...formData,
      tech_stack: newStack,
    });
  };

  if (loading) {
    return (
      <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '40px' }}>
        Loading profile...
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold mb-2" style={{ color: 'var(--text)' }}>
          Profile Settings
        </h1>
        <p style={{ color: 'var(--muted)' }}>
          Customize your job preferences and skills
        </p>
      </div>

      {error && (
        <div
          className="mb-6 p-4 border rounded-lg"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: '#fee',
            color: '#c00',
          }}
        >
          {error}
        </div>
      )}

      {success && (
        <div
          className="mb-6 p-4 border rounded-lg"
          style={{
            borderColor: '#10b981',
            backgroundColor: '#f0fdf4',
            color: '#10b981',
          }}
        >
          Profile saved successfully!
        </div>
      )}

      <form className="space-y-8">
        {/* Target Roles */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Target Roles
          </h2>

          {/* Display roles as tags/chips */}
          {(formData.target_roles || []).length > 0 ? (
            <div className="mb-4 flex flex-wrap gap-2">
              {(formData.target_roles || []).map((role, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 px-3 py-2 rounded-full text-sm"
                  style={{
                    backgroundColor: 'var(--primary-bg)',
                    color: 'var(--primary-text)',
                    border: '1px solid var(--primary-bg)',
                  }}
                >
                  <span>{role}</span>
                  <button
                    type="button"
                    onClick={() => removeTargetRole(index)}
                    className="ml-1 font-semibold hover:opacity-70 transition-opacity"
                    style={{ color: 'var(--primary-text)', cursor: 'pointer' }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>
              No target roles added yet
            </p>
          )}

          <button
            type="button"
            onClick={addTargetRole}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              backgroundColor: 'var(--primary-bg)',
              color: 'var(--primary-text)',
              border: '1px solid var(--primary-bg)',
            }}
          >
            + Add Role
          </button>

          {/* Input field for adding new role (appears when adding) */}
          {(formData.target_roles || []).length === 0 && (
            <input
              type="text"
              placeholder="e.g., AI Engineer"
              className="w-full mt-3 px-4 py-2 border rounded-lg text-sm outline-none"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text)',
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                  setFormData({
                    ...formData,
                    target_roles: [...(formData.target_roles || []), e.currentTarget.value],
                  });
                  e.currentTarget.value = '';
                }
              }}
            />
          )}
        </section>

        {/* Tech Stack */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Tech Stack
          </h2>

          {/* Display tech as tags/chips */}
          {(formData.tech_stack || []).length > 0 ? (
            <div className="mb-4 flex flex-wrap gap-2">
              {(formData.tech_stack || []).map((tech, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 px-3 py-2 rounded-full text-sm"
                  style={{
                    backgroundColor: 'var(--accent-bg)',
                    color: 'var(--accent)',
                    border: '1px solid var(--accent-bg)',
                  }}
                >
                  <span>{tech}</span>
                  <button
                    type="button"
                    onClick={() => removeTechStack(index)}
                    className="ml-1 font-semibold hover:opacity-70 transition-opacity"
                    style={{ color: 'var(--accent)', cursor: 'pointer' }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>
              No technologies added yet
            </p>
          )}

          <button
            type="button"
            onClick={addTechStack}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              backgroundColor: 'var(--primary-bg)',
              color: 'var(--primary-text)',
              border: '1px solid var(--primary-bg)',
            }}
          >
            + Add Technology
          </button>

          {/* Input field for adding new tech (appears when adding) */}
          {(formData.tech_stack || []).length === 0 && (
            <input
              type="text"
              placeholder="e.g., Python"
              className="w-full mt-3 px-4 py-2 border rounded-lg text-sm outline-none"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text)',
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                  setFormData({
                    ...formData,
                    tech_stack: [...(formData.tech_stack || []), e.currentTarget.value],
                  });
                  e.currentTarget.value = '';
                }
              }}
            />
          )}
        </section>

        {/* Preferred Modality */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Work Arrangement
          </h2>
          <select
            value={formData.preferred_modality || ''}
            onChange={(e) =>
              setFormData({
                ...formData,
                preferred_modality: e.target.value === '' ? null : (e.target.value as 'remote' | 'hybrid' | 'on-site'),
              })
            }
            className="w-full px-4 py-2 border rounded-lg text-sm outline-none"
            style={{
              borderColor: 'var(--border)',
              backgroundColor: 'var(--bg)',
              color: 'var(--text)',
            }}
          >
            <option value="">Any</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="on-site">On-site</option>
          </select>
        </section>

        {/* Preferred Countries */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Preferred Countries
          </h2>

          {/* Display countries as chips */}
          {(formData.preferred_countries || []).length > 0 ? (
            <div className="mb-4 flex flex-wrap gap-2">
              {(formData.preferred_countries || []).map((country, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 px-3 py-2 rounded-full text-sm"
                  style={{
                    backgroundColor: 'var(--primary-bg)',
                    color: 'var(--primary-text)',
                    border: '1px solid var(--primary-bg)',
                  }}
                >
                  <span>{country}</span>
                  <button
                    type="button"
                    onClick={() => {
                      const countries = formData.preferred_countries || [];
                      setFormData({
                        ...formData,
                        preferred_countries: countries.filter((_, i) => i !== index),
                      });
                    }}
                    className="ml-1 font-semibold hover:opacity-70 transition-opacity"
                    style={{ color: 'var(--primary-text)', cursor: 'pointer' }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>
              No countries selected
            </p>
          )}

          <input
            type="text"
            placeholder="Type country and press Enter (e.g., US)"
            className="w-full px-4 py-2 border rounded-lg text-sm outline-none"
            style={{
              borderColor: 'var(--border)',
              backgroundColor: 'var(--bg)',
              color: 'var(--text)',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                const country = e.currentTarget.value.trim().toUpperCase();
                const countries = formData.preferred_countries || [];
                if (!countries.includes(country)) {
                  setFormData({
                    ...formData,
                    preferred_countries: [...countries, country],
                  });
                }
                e.currentTarget.value = '';
              }
            }}
          />
        </section>

        {/* Salary Minimum */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Salary Expectations
          </h2>
          <div>
            <label
              className="block text-xs font-semibold mb-2"
              style={{ color: 'var(--faint)' }}
            >
              Minimum Annual Salary (USD)
            </label>
            <input
              type="number"
              value={formData.salary_min || 0}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  salary_min: parseInt(e.target.value) || 0,
                })
              }
              placeholder="100000"
              className="w-full px-4 py-2 border rounded-lg text-sm outline-none"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
          </div>
        </section>

        {/* Save Button */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2.5 rounded-lg font-medium text-sm transition-all"
            style={{
              backgroundColor: 'var(--primary-bg)',
              color: 'var(--primary-text)',
              opacity: saving ? 0.6 : 1,
              cursor: saving ? 'not-allowed' : 'pointer',
            }}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
}
