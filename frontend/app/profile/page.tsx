'use client';

import { useEffect, useState, useRef } from 'react';
import { getUserProfile, updateUserProfile } from '@/lib/api';
import { UserProfile } from '@/lib/types';
import { X, Mail, Upload } from 'lucide-react';

interface GmailStatus {
  connected: boolean;
  email: string | null;
  expires_at: string | null;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState<Partial<UserProfile>>({});

  const [gmailStatus, setGmailStatus] = useState<GmailStatus>({
    connected: false,
    email: null,
    expires_at: null,
  });
  const [gmailLoading, setGmailLoading] = useState(false);
  const [gmailError, setGmailError] = useState<string | null>(null);

  const [cvUploading, setCvUploading] = useState(false);
  const [cvSuccess, setCvSuccess] = useState<string | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const skillDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const roleDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const languageDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const lastSkillInputRef = useRef<string>('');
  const lastRoleInputRef = useRef<string>('');
  const lastLanguageInputRef = useRef<string>('');

  const [languages, setLanguages] = useState<Array<{language: string; level: string}>>([]);
  const [skillSuggestions, setSkillSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [roleSuggestions, setRoleSuggestions] = useState<string[]>([]);
  const [showRoleSuggestions, setShowRoleSuggestions] = useState<{[key: number]: boolean}>({});
  const [countrySuggestions, setCountrySuggestions] = useState<string[]>([]);
  const [showCountrySuggestions, setShowCountrySuggestions] = useState(false);
  const [languageSuggestions, setLanguageSuggestions] = useState<string[]>([]);
  const [showLanguageSuggestions, setShowLanguageSuggestions] = useState<{[key: number]: boolean}>({});
  const [nationality, setNationality] = useState<string>('');
  const [profileIncomplete, setProfileIncomplete] = useState(false);

  const isProfileComplete = () => {
    return (
      (formData.target_roles && formData.target_roles.length > 0) &&
      (formData.tech_stack && formData.tech_stack.length > 0)
    );
  };

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getUserProfile();

        setProfile(data);
        const formDataToSet = {
          target_roles: data.target_roles || [],
          tech_stack: data.tech_stack || [],
          preferred_countries: data.preferred_countries || [],
          priority_country: data.priority_country || null,
          preferred_modality: data.preferred_modality || null,
          salary_min: data.salary_min || 0,
          cv_data: data.cv_data || {},
        };
        setFormData(formDataToSet);

        // Load languages from cv_data if they exist
        if (data.cv_data && data.cv_data.languages && Array.isArray(data.cv_data.languages)) {
          const parsedLanguages = data.cv_data.languages
            .map((lang: any) => {
              if (typeof lang === 'object' && lang.language && lang.level) {
                return {
                  language: lang.language.trim() || '',
                  level: lang.level.trim() || 'Intermediate',
                };
              }
              return null;
            })
            .filter((l: any) => l && l.language);

          if (parsedLanguages.length > 0) {
            setLanguages(parsedLanguages);
            console.log('[PROFILE LOAD] Loaded languages from cv_data:', parsedLanguages);
          }
        }

        // Load nationality from cv_data if it exists
        if (data.cv_data && data.cv_data.nationality) {
          setNationality(data.cv_data.nationality);
          console.log('[PROFILE LOAD] Loaded nationality from cv_data:', data.cv_data.nationality);
        }

        // Check if profile is complete
        const hasRoles = formDataToSet.target_roles && formDataToSet.target_roles.length > 0;
        const hasSkills = formDataToSet.tech_stack && formDataToSet.tech_stack.length > 0;
        if (!hasRoles || !hasSkills) {
          setProfileIncomplete(true);
        }
      } catch (err) {
        console.error('Failed to load profile:', err);
        setError('Failed to load profile. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    const checkGmailCallback = () => {
      const params = new URLSearchParams(window.location.search);
      if (params.has('gmail_connected')) {
        setGmailError(null);
        // Clean up URL
        window.history.replaceState({}, document.title, '/profile');
        // Reload Gmail status
        setTimeout(() => loadGmailStatus(), 500);
      } else if (params.has('gmail_error')) {
        const error = params.get('gmail_error');
        setGmailError(`Gmail connection failed: ${error}`);
        // Clean up URL
        window.history.replaceState({}, document.title, '/profile');
      }
    };

    loadProfile();
    loadGmailStatus();
    checkGmailCallback();
  }, []);

  const loadGmailStatus = async () => {
    try {
      setGmailLoading(true);
      setGmailError(null);
      const response = await fetch('http://localhost:8001/api/gmail/status', {
        headers: {
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('[GMAIL STATUS] Response:', data);

      setGmailStatus({
        connected: data.connected || false,
        email: data.email || null,
        expires_at: data.expires_at || null,
      });
    } catch (err) {
      console.error('Failed to load Gmail status:', err);
      setGmailError(null); // Don't show error for status check failures
    } finally {
      setGmailLoading(false);
    }
  };

  const handleConnectGmail = async () => {
    try {
      setGmailLoading(true);
      setGmailError(null);
      const response = await fetch('http://localhost:8001/api/gmail/auth', {
        headers: {
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `HTTP ${response.status}`;
        console.error('[GMAIL AUTH] Error response:', errorData);
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('[GMAIL AUTH] Success:', data);

      if (data.auth_url) {
        console.log('[GMAIL AUTH] Redirecting to Google OAuth...');
        window.location.href = data.auth_url;
      } else {
        setGmailError('Failed to generate OAuth URL from backend');
        setGmailLoading(false);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error('[GMAIL AUTH] Error:', errorMsg);
      setGmailError(`Gmail connection failed: ${errorMsg}`);
      setGmailLoading(false);
    }
  };

  const handleDisconnectGmail = async () => {
    try {
      setGmailLoading(true);
      setGmailError(null);
      const response = await fetch('http://localhost:8001/api/gmail/disconnect', {
        method: 'POST',
        headers: {
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('[GMAIL DISCONNECT] Response:', data);

      // Reload status after disconnect
      await loadGmailStatus();
    } catch (err) {
      console.error('Failed to disconnect Gmail:', err);
      setGmailError('Failed to disconnect Gmail. Please try again.');
    } finally {
      setGmailLoading(false);
    }
  };

  const handleCvUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    console.log('[CV UPLOAD] Function called, file:', event.target.files?.[0]?.name);
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setCvUploading(true);
      setCvError(null);
      setCvSuccess(null);

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8001/api/cv/upload', {
        method: 'POST',
        headers: {
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `HTTP ${response.status}`;
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('[CV UPLOAD] Response:', data);

      const extractedData = data.extracted_data;
      const skillsCount = extractedData.skills?.length || 0;
      const projectsCount = extractedData.projects?.length || 0;

      console.log('[CV] Extracted roles:', extractedData.roles);

      // Replace tech_stack completely with extracted skills
      // New CV is source of truth - old skills are discarded
      setFormData((prev) => {
        const updatedCvData = {
          ...prev.cv_data,
          nationality: extractedData.nationality || prev.cv_data?.nationality,
          experience: extractedData.experience || [],
          projects: extractedData.projects || [],
          education: extractedData.education || [],
        };
        return {
          ...prev,
          tech_stack: extractedData.skills || [],
          target_roles: extractedData.roles || prev.target_roles,
          cv_data: updatedCvData,
        };
      });

      // Set languages from CV - parse correctly (structured format)
      if (extractedData.languages && extractedData.languages.length > 0) {
        const parsedLanguages = extractedData.languages
          .map((lang: any) => {
            if (typeof lang === 'object' && lang.language && lang.level) {
              // Already structured correctly - validate fields
              return {
                language: lang.language.trim() || '',
                level: lang.level.trim() || 'Intermediate',
              };
            } else if (typeof lang === 'string') {
              // Fallback: parse string like "Spanish Native" or "English B2"
              const parts = lang.trim().split(/\s+/);
              if (parts.length >= 2) {
                return {
                  language: parts[0],
                  level: parts.slice(1).join(' '),
                };
              } else if (parts.length === 1) {
                return {
                  language: parts[0],
                  level: 'Intermediate',
                };
              }
            }
            return null;
          })
          .filter((l: any) => l && l.language); // Filter out invalid entries

        if (parsedLanguages.length > 0) {
          setLanguages(parsedLanguages);
        }
      }

      setCvSuccess(
        `CV processed - ${skillsCount} skills extracted, ${projectsCount} projects found`
      );

      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Auto-save after 2 seconds
      setTimeout(() => {
        handleSave();
      }, 2000);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error('[CV UPLOAD] Error:', errorMsg);
      setCvError(`CV upload failed: ${errorMsg}`);
    } finally {
      setCvUploading(false);
    }
  };

  const normalizeSkillName = (skill: string): string => {
    // Remove spaces and special chars, lowercase for comparison
    return skill.toLowerCase().replace(/[^a-z0-9]/g, '');
  };

  const deduplicateSkills = (existingSkills: string[], newSkills: string[]): string[] => {
    // Track normalized -> original mapping, keeping the cleanest version
    const seen: {[key: string]: string} = {};

    // Process existing skills first
    (existingSkills || []).forEach((skill) => {
      if (!skill) return;
      const normalized = normalizeSkillName(skill);
      if (!seen[normalized]) {
        seen[normalized] = skill;
      }
    });

    // Process new skills, replacing if better formatted
    (newSkills || []).forEach((skill) => {
      if (!skill) return;
      const normalized = normalizeSkillName(skill);

      if (!seen[normalized]) {
        seen[normalized] = skill;
      } else {
        // Keep version with more capitals/spaces (better formatted)
        const existing = seen[normalized];
        const newHasMoreCaps = (skill.match(/[A-Z]/g) || []).length > (existing.match(/[A-Z]/g) || []).length;
        const newHasMoreSpaces = (skill.match(/\s/g) || []).length > (existing.match(/\s/g) || []).length;

        if (newHasMoreCaps || newHasMoreSpaces) {
          seen[normalized] = skill;
        }
      }
    });

    return Object.values(seen).sort();
  };

  const getSkillSuggestions = async (currentInput: string) => {
    // Cancel previous pending call
    if (skillDebounceRef.current) {
      clearTimeout(skillDebounceRef.current);
    }

    // Only call if input has changed and length >= 2
    if (currentInput.trim().length < 2 || currentInput === lastSkillInputRef.current) {
      if (currentInput.trim().length === 0) {
        setSkillSuggestions([]);
      }
      return;
    }

    lastSkillInputRef.current = currentInput;

    // Debounce 500ms
    skillDebounceRef.current = setTimeout(async () => {
      if (!currentInput.trim() || (formData.tech_stack || []).length === 0) {
        setSkillSuggestions([]);
        return;
      }

      try {
        const response = await fetch('http://localhost:8001/api/jobs/suggest-skills', {
          method: 'POST',
          headers: {
            'x-user-id': localStorage.getItem('user_id') || '',
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            current_skills: formData.tech_stack || [],
            input_skill: currentInput,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setSkillSuggestions(data.suggestions || []);
          setShowSuggestions(true);
        }
      } catch (err) {
        console.error('Failed to get skill suggestions:', err);
      }
    }, 500);
  };

  const getRoleSuggestions = async (currentInput: string) => {
    // Cancel previous pending call
    if (roleDebounceRef.current) {
      clearTimeout(roleDebounceRef.current);
    }

    // Only call if input has changed and length >= 2
    if (currentInput.trim().length < 2 || currentInput === lastRoleInputRef.current) {
      if (currentInput.trim().length === 0) {
        setRoleSuggestions([]);
      }
      return;
    }

    lastRoleInputRef.current = currentInput;

    // Debounce 500ms
    roleDebounceRef.current = setTimeout(async () => {
      if (!currentInput.trim()) {
        setRoleSuggestions([]);
        return;
      }

      try {
        const response = await fetch('http://localhost:8001/api/jobs/suggest-roles', {
          method: 'POST',
          headers: {
            'x-user-id': localStorage.getItem('user_id') || '',
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            current_skills: formData.tech_stack || [],
            current_roles: formData.target_roles || [],
            input_role: currentInput,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setRoleSuggestions(data.suggestions || []);
        }
      } catch (err) {
        console.error('[ROLES] Fetch error:', err);
      }
    }, 500);
  };

  const getCountrySuggestions = async (currentInput: string) => {
    if (!currentInput.trim()) {
      setCountrySuggestions([]);
      return;
    }

    console.log('[COUNTRIES] Fetching suggestions for:', currentInput);

    try {
      const response = await fetch('http://localhost:8001/api/jobs/countries/available', {
        method: 'GET',
        headers: {
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
          'Content-Type': 'application/json',
        },
      });

      console.log('[COUNTRIES] Response status:', response.status);
      if (response.ok) {
        const data = await response.json();
        const allCountries = data.countries || [];
        console.log('[COUNTRIES] All countries received:', allCountries.length);

        // Filter countries that contain the input
        const filtered = allCountries.filter(country =>
          country.toLowerCase().includes(currentInput.toLowerCase()) &&
          !(formData.preferred_countries || []).includes(country.toUpperCase())
        );

        console.log('[COUNTRIES] Filtered suggestions:', filtered);
        setCountrySuggestions(filtered);
      } else {
        const errorText = await response.text();
        console.error('[COUNTRIES] API error response:', response.status, errorText);
      }
    } catch (err) {
      console.error('[COUNTRIES] Fetch error:', err);
    }
  };

  const getLanguageSuggestions = async (currentInput: string) => {
    // Cancel previous pending call
    if (languageDebounceRef.current) {
      clearTimeout(languageDebounceRef.current);
    }

    // Only call if input has changed and length >= 2
    if (currentInput.trim().length < 2 || currentInput === lastLanguageInputRef.current) {
      if (currentInput.trim().length === 0) {
        setLanguageSuggestions([]);
      }
      return;
    }

    lastLanguageInputRef.current = currentInput;

    // Debounce 500ms
    languageDebounceRef.current = setTimeout(async () => {
      if (!currentInput.trim()) {
        setLanguageSuggestions([]);
        return;
      }

      try {
        const response = await fetch('http://localhost:8001/api/jobs/suggest-languages', {
          method: 'POST',
          headers: {
            'x-user-id': localStorage.getItem('user_id') || '',
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            target_countries: formData.preferred_countries || [],
            current_languages: languages.map(l => l.language),
          }),
        });

        if (response.ok) {
          const data = await response.json();

          // Further filter by user input
          const filtered = data.suggestions.filter((lang: string) =>
            lang.toLowerCase().includes(currentInput.toLowerCase())
          );

          setLanguageSuggestions(filtered);
        }
      } catch (err) {
        console.error('[LANGS] Fetch error:', err);
      }
    }, 500);
  };

  const validateLanguages = (): boolean => {
    // Check if any language entry has empty language name
    for (const lang of languages) {
      if (!lang.language || !lang.language.trim()) {
        setError('Please enter a language name or remove empty language entries.');
        return false;
      }
    }
    return true;
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      // Validate languages before saving
      if (!validateLanguages()) {
        setSaving(false);
        return;
      }

      console.log('[SAVE] Languages being saved:', languages);
      console.log('[SAVE] FormData being sent:', formData);

      // Include languages and nationality in cv_data when saving
      const profileToSave = {
        ...formData,
        cv_data: {
          ...formData.cv_data,
          languages: languages,
          nationality: nationality
        }
      };

      console.log('[SAVE] Complete profile with languages:', profileToSave);

      await updateUserProfile(profileToSave);
      setProfile(profileToSave as UserProfile);
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

  const addLanguage = () => {
    setLanguages([...languages, {language: '', level: 'Intermediate'}]);
  };

  const removeLanguage = (index: number) => {
    setLanguages(languages.filter((_, i) => i !== index));
  };

  const updateLanguage = (index: number, field: 'language' | 'level', value: string) => {
    const newLanguages = [...languages];
    newLanguages[index] = {...newLanguages[index], [field]: value};
    setLanguages(newLanguages);
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

      {profileIncomplete && (
        <div
          className="mb-6 p-4 border rounded-lg flex items-start gap-3"
          style={{
            borderColor: '#f59e0b',
            backgroundColor: '#fffbeb',
            color: '#d97706',
          }}
        >
          <div style={{ fontSize: '20px', marginTop: '2px' }}>⚠️</div>
          <div>
            <strong>Your profile is incomplete.</strong> Upload your CV or add your skills and target roles to enable job search. Job discovery is paused until your profile is complete.
          </div>
        </div>
      )}

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

      {cvError && (
        <div
          className="mb-6 p-4 border rounded-lg"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: '#fee',
            color: '#c00',
          }}
        >
          {cvError}
        </div>
      )}

      {cvSuccess && (
        <div
          className="mb-6 p-4 border rounded-lg"
          style={{
            borderColor: '#10b981',
            backgroundColor: '#f0fdf4',
            color: '#10b981',
          }}
        >
          {cvSuccess}
        </div>
      )}

      {/* CV Upload Section */}
      <section
        className="border rounded-lg p-6 mb-8"
        style={{
          borderColor: 'var(--border)',
          backgroundColor: 'var(--card)',
        }}
      >
        <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
          Upload CV
        </h2>
        <p style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>
          Upload your CV (PDF) to automatically extract skills, roles, and experience
        </p>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleCvUpload}
          className="hidden"
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={cvUploading}
          className="flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium transition-opacity"
          style={{
            backgroundColor: 'var(--primary-bg)',
            color: 'var(--primary-text)',
            border: '1px solid var(--primary-bg)',
            opacity: cvUploading ? 0.6 : 1,
            cursor: cvUploading ? 'not-allowed' : 'pointer',
          }}
        >
          <Upload size={16} />
          {cvUploading ? 'Processing...' : 'Upload New CV (PDF)'}
        </button>
      </section>

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

          {/* Display roles as editable inputs with autocomplete */}
          {(formData.target_roles || []).length > 0 && (
            <div className="mb-4 space-y-2">
              {(formData.target_roles || []).map((role, index) => (
                <div key={index} className="flex items-center gap-2 relative">
                  <input
                    type="text"
                    value={role}
                    placeholder="e.g., AI Engineer"
                    onChange={(e) => {
                      updateTargetRole(index, e.target.value);
                      if (e.target.value.trim()) {
                        getRoleSuggestions(e.target.value);
                        setShowRoleSuggestions({...showRoleSuggestions, [index]: true});
                      }
                    }}
                    onBlur={() => setTimeout(() => setShowRoleSuggestions({...showRoleSuggestions, [index]: false}), 200)}
                    onFocus={() => {
                      if (role.trim()) {
                        getRoleSuggestions(role);
                        setShowRoleSuggestions({...showRoleSuggestions, [index]: true});
                      }
                    }}
                    className="flex-1 px-3 py-2 border rounded-lg text-sm outline-none"
                    style={{
                      borderColor: 'var(--border)',
                      backgroundColor: 'var(--bg)',
                      color: 'var(--text)',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => removeTargetRole(index)}
                    className="px-2 py-1 font-semibold hover:opacity-70 transition-opacity"
                    style={{ color: 'var(--muted)', cursor: 'pointer' }}
                  >
                    ×
                  </button>

                  {showRoleSuggestions[index] && roleSuggestions.length > 0 && (
                    <div
                      className="absolute top-full left-0 right-0 mt-1 bg-card border rounded-lg shadow-lg z-10"
                      style={{
                        borderColor: 'var(--border)',
                        backgroundColor: 'var(--card)',
                      }}
                    >
                      {roleSuggestions.map((suggestion, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => {
                            updateTargetRole(index, suggestion);
                            setShowRoleSuggestions({...showRoleSuggestions, [index]: false});
                            setRoleSuggestions([]);
                          }}
                          className="w-full text-left px-4 py-2 hover:opacity-70 transition-opacity text-sm"
                          style={{ color: 'var(--text)' }}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {(formData.target_roles || []).length === 0 && (
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
        </section>

        {/* Skills */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Skills
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
              No skills added yet
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
            + Add Skill
          </button>

          {/* Input field for adding new tech with autocomplete */}
          <div className="w-full mt-3 relative">
            <input
              type="text"
              placeholder="e.g., Python"
              className="w-full px-4 py-2 border rounded-lg text-sm outline-none"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text)',
              }}
              onChange={(e) => getSkillSuggestions(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                  setFormData({
                    ...formData,
                    tech_stack: [...(formData.tech_stack || []), e.currentTarget.value],
                  });
                  e.currentTarget.value = '';
                  setShowSuggestions(false);
                  setSkillSuggestions([]);
                }
              }}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              onFocus={(e) => {
                if (e.currentTarget.value.trim()) {
                  getSkillSuggestions(e.currentTarget.value);
                }
              }}
            />

            {showSuggestions && skillSuggestions.length > 0 && (
              <div
                className="absolute top-full left-0 right-0 mt-1 bg-card border rounded-lg shadow-lg z-10"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--card)',
                }}
              >
                {skillSuggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setFormData({
                        ...formData,
                        tech_stack: [...(formData.tech_stack || []), suggestion],
                      });
                      setShowSuggestions(false);
                      setSkillSuggestions([]);
                    }}
                    className="w-full text-left px-4 py-2 hover:opacity-70 transition-opacity text-sm"
                    style={{ color: 'var(--text)' }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Languages */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Languages
          </h2>

          {languages.length > 0 ? (
            <div className="mb-4 space-y-2">
              {languages.map((lang, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 p-3 border rounded-lg relative"
                  style={{
                    borderColor: 'var(--border)',
                    backgroundColor: 'var(--bg)',
                  }}
                >
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      placeholder="e.g. Spanish"
                      value={lang.language}
                      onChange={(e) => {
                        updateLanguage(index, 'language', e.target.value);
                        if (e.target.value.trim()) {
                          getLanguageSuggestions(e.target.value);
                          setShowLanguageSuggestions({...showLanguageSuggestions, [index]: true});
                        }
                      }}
                      onBlur={() => setTimeout(() => setShowLanguageSuggestions({...showLanguageSuggestions, [index]: false}), 200)}
                      onFocus={() => {
                        if (lang.language.trim()) {
                          getLanguageSuggestions(lang.language);
                          setShowLanguageSuggestions({...showLanguageSuggestions, [index]: true});
                        }
                      }}
                      className="w-full px-2 py-1 border rounded text-sm outline-none"
                      style={{
                        borderColor: 'var(--border)',
                        backgroundColor: 'var(--card)',
                        color: 'var(--text)',
                      }}
                    />
                    {showLanguageSuggestions[index] && languageSuggestions.length > 0 && (
                      <div
                        className="absolute top-full left-0 right-0 mt-1 bg-card border rounded-lg shadow-lg z-10"
                        style={{
                          borderColor: 'var(--border)',
                          backgroundColor: 'var(--card)',
                        }}
                      >
                        {languageSuggestions.slice(0, 5).map((suggestion, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              updateLanguage(index, 'language', suggestion);
                              setShowLanguageSuggestions({...showLanguageSuggestions, [index]: false});
                              setLanguageSuggestions([]);
                            }}
                            className="w-full text-left px-3 py-1 hover:opacity-70 transition-opacity text-sm"
                            style={{ color: 'var(--text)' }}
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <select
                    value={lang.level}
                    onChange={(e) => updateLanguage(index, 'level', e.target.value)}
                    className="px-2 py-1 border rounded text-sm outline-none"
                    style={{
                      borderColor: 'var(--border)',
                      backgroundColor: 'var(--card)',
                      color: 'var(--text)',
                    }}
                  >
                    <option value="Native">Native</option>
                    <option value="Fluent">Fluent</option>
                    <option value="Advanced">Advanced</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Beginner">Beginner</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => removeLanguage(index)}
                    className="ml-1 font-semibold hover:opacity-70 transition-opacity"
                    style={{ color: 'var(--muted)', cursor: 'pointer' }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>
              No languages added yet
            </p>
          )}

          <button
            type="button"
            onClick={addLanguage}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              backgroundColor: 'var(--primary-bg)',
              color: 'var(--primary-text)',
              border: '1px solid var(--primary-bg)',
            }}
          >
            + Add Language
          </button>
        </section>

        {/* Nationality / Citizenship */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Nationality / Citizenship
          </h2>

          <div>
            <label
              className="block text-xs font-semibold mb-2"
              style={{ color: 'var(--faint)' }}
            >
              Nationality
            </label>
            <input
              type="text"
              placeholder="e.g. Mexican, American, Brazilian"
              value={nationality}
              onChange={(e) => setNationality(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg text-sm outline-none"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text)',
              }}
            />
          </div>
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

          <div className="w-full relative">
            <input
              type="text"
              placeholder="Type country and press Enter (e.g., US)"
              className="w-full px-4 py-2 border rounded-lg text-sm outline-none"
              style={{
                borderColor: 'var(--border)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text)',
              }}
              onChange={(e) => {
                if (e.currentTarget.value.trim()) {
                  getCountrySuggestions(e.currentTarget.value);
                  setShowCountrySuggestions(true);
                }
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
                  setCountrySuggestions([]);
                  setShowCountrySuggestions(false);
                }
              }}
              onBlur={() => setTimeout(() => setShowCountrySuggestions(false), 200)}
              onFocus={(e) => {
                if (e.currentTarget.value.trim()) {
                  getCountrySuggestions(e.currentTarget.value);
                  setShowCountrySuggestions(true);
                }
              }}
            />

            {showCountrySuggestions && countrySuggestions.length > 0 && (
              <div
                className="absolute top-full left-0 right-0 mt-1 bg-card border rounded-lg shadow-lg z-10"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--card)',
                }}
              >
                {countrySuggestions.map((country, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      const countries = formData.preferred_countries || [];
                      setFormData({
                        ...formData,
                        preferred_countries: [...countries, country.toUpperCase()],
                      });
                      setShowCountrySuggestions(false);
                      setCountrySuggestions([]);
                    }}
                    className="w-full text-left px-4 py-2 hover:opacity-70 transition-opacity text-sm"
                    style={{ color: 'var(--text)' }}
                  >
                    {country}
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Priority Country */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Priority Country
          </h2>
          <p style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '12px' }}>
            Select one country to prioritize (must be in your preferred countries list)
          </p>
          <select
            value={formData.priority_country || ''}
            onChange={(e) =>
              setFormData({
                ...formData,
                priority_country: e.target.value === '' ? null : e.target.value,
              })
            }
            className="w-full px-4 py-2 border rounded-lg text-sm outline-none"
            style={{
              borderColor: 'var(--border)',
              backgroundColor: 'var(--bg)',
              color: 'var(--text)',
            }}
          >
            <option value="">None - Search all countries equally</option>
            {(formData.preferred_countries || []).map((country) => (
              <option key={country} value={country}>
                {country}
              </option>
            ))}
          </select>
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

        {/* Email Integration */}
        <section
          className="border rounded-lg p-6"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Mail size={20} style={{ color: 'var(--primary-text)' }} />
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>
              Email Integration
            </h2>
          </div>

          {gmailError && (
            <div
              className="mb-4 p-3 rounded-lg text-sm"
              style={{
                backgroundColor: '#fee',
                color: '#c00',
                borderColor: '#fcc',
                border: '1px solid',
              }}
            >
              {gmailError}
            </div>
          )}

          {gmailLoading ? (
            <div style={{ color: 'var(--muted)' }}>Loading Gmail status...</div>
          ) : gmailStatus.connected ? (
            <div>
              <div
                className="mb-4 p-4 rounded-lg flex items-center justify-between"
                style={{
                  backgroundColor: '#f0fdf4',
                  borderColor: '#d1fae5',
                  border: '1px solid',
                }}
              >
                <div className="flex items-center gap-3">
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: '#10b981',
                      flexShrink: 0,
                    }}
                  />
                  <div>
                    <p style={{ color: '#10b981', fontWeight: '500', marginBottom: '4px' }}>
                      Gmail Connected
                    </p>
                    <p style={{ color: '#6b7280', fontSize: '14px' }}>
                      {gmailStatus.email}
                    </p>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleDisconnectGmail}
                className="px-4 py-2 rounded-lg font-medium text-sm transition-all"
                style={{
                  backgroundColor: '#fef2f2',
                  color: '#dc2626',
                  border: '1px solid #fee2e2',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#fee2e2';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#fef2f2';
                }}
              >
                Disconnect Gmail
              </button>
            </div>
          ) : (
            <div>
              <p style={{ color: 'var(--muted)', marginBottom: '16px', fontSize: '14px' }}>
                Connect Gmail to enable automatic email monitoring for interview invites and company replies.
              </p>
              <button
                type="button"
                onClick={handleConnectGmail}
                disabled={gmailLoading}
                className="px-6 py-2.5 rounded-lg font-medium text-sm transition-all text-white"
                style={{
                  backgroundColor: '#3b82f6',
                  opacity: gmailLoading ? 0.6 : 1,
                  cursor: gmailLoading ? 'not-allowed' : 'pointer',
                }}
                onMouseEnter={(e) => {
                  if (!gmailLoading) {
                    e.currentTarget.style.backgroundColor = '#2563eb';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#3b82f6';
                }}
              >
                {gmailLoading ? 'Connecting...' : 'Connect Gmail'}
              </button>
            </div>
          )}
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
