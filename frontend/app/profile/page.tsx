'use client';

import { useEffect, useState, useRef } from 'react';
import { getUserProfile, updateUserProfile } from '@/lib/api';
import { UserProfile } from '@/lib/types';
import { Mail, X } from 'lucide-react';
import { ScoutSidebar } from '@/components/ScoutSidebar';

interface GmailStatus {
  connected: boolean;
  email: string | null;
  expires_at: string | null;
}

export default function ProfilePage() {
  const [isDark, setIsDark] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
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

  const [languages, setLanguages] = useState<Array<{language: string; level: string}>>([]);
  const [nationality, setNationality] = useState<string>('');

  const lightTheme = {
    '--bg': '#f0e4cf',
    '--card': '#fffaf1',
    '--active': '#ebddc5',
    '--border': 'rgba(32,30,29,.1)',
    '--text': '#201e1d',
    '--muted': '#645c50',
    '--faint': '#82796a',
    '--track': '#dcd3c4',
    '--color-accent': '#c67139',
    '--color-accent-200': '#f4d9c6',
    '--color-accent-700': '#7a3f1f',
    '--color-accent-2': '#7a8a5e',
    '--color-accent-2-100': '#e8ede0',
    '--color-accent-2-200': '#dde5cc',
    '--color-accent-2-800': '#4a5233',
    '--dbg': '#f0e4cf',
    '--dcard': '#fffaf1',
    '--dtext': '#201e1d',
    '--dmuted': '#645c50',
    '--dfaint': '#82796a',
    '--dactive': '#ebddc5',
    '--dborder': 'rgba(32,30,29,.1)',
  };

  const darkTheme = {
    '--bg': '#2b2118',
    '--card': '#3a2c1e',
    '--active': '#463625',
    '--border': 'rgba(245,234,216,.16)',
    '--text': '#f7ecd9',
    '--muted': '#d1bd9c',
    '--faint': '#a68f72',
    '--track': 'rgba(245,234,216,.16)',
    '--color-accent': '#c67139',
    '--color-accent-200': '#f4d9c6',
    '--color-accent-700': '#7a3f1f',
    '--color-accent-2': '#7a8a5e',
    '--color-accent-2-100': '#4a5233',
    '--color-accent-2-200': '#dde5cc',
    '--color-accent-2-800': '#c9d5ad',
    '--dbg': '#2b2118',
    '--dcard': '#3a2c1e',
    '--dtext': '#f7ecd9',
    '--dmuted': '#d1bd9c',
    '--dfaint': '#a68f72',
    '--dactive': '#463625',
    '--dborder': 'rgba(245,234,216,.16)',
  };

  const theme = isDark ? darkTheme : lightTheme;

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

        if (data.cv_data && data.cv_data.languages && Array.isArray(data.cv_data.languages)) {
          const parsedLanguages = data.cv_data.languages
            .map((lang: any) => {
              if (typeof lang === 'object' && lang.language && lang.level) {
                return { language: lang.language.trim() || '', level: lang.level.trim() || 'Intermediate' };
              }
              return null;
            })
            .filter((l: any) => l && l.language);
          if (parsedLanguages.length > 0) setLanguages(parsedLanguages);
        }

        if (data.cv_data && data.cv_data.nationality) {
          setNationality(data.cv_data.nationality);
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
        window.history.replaceState({}, document.title, '/profile');
        setTimeout(() => loadGmailStatus(), 500);
      } else if (params.has('gmail_error')) {
        const error = params.get('gmail_error');
        setGmailError(`Gmail connection failed: ${error}`);
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
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setGmailStatus({
        connected: data.connected || false,
        email: data.email || null,
        expires_at: data.expires_at || null,
      });
    } catch (err) {
      console.error('Failed to load Gmail status:', err);
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
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      if (data.auth_url) {
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
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await loadGmailStatus();
    } catch (err) {
      console.error('Failed to disconnect Gmail:', err);
      setGmailError('Failed to disconnect Gmail. Please try again.');
    } finally {
      setGmailLoading(false);
    }
  };

  const handleCvUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setCvUploading(true);
      setCvError(null);
      setCvSuccess(null);

      const formDataFile = new FormData();
      formDataFile.append('file', file);

      const response = await fetch('http://localhost:8001/api/cv/upload', {
        method: 'POST',
        headers: {
          'x-user-id': localStorage.getItem('user_id') || '',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        body: formDataFile,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      const extractedData = data.extracted_data;

      setFormData((prev) => ({
        ...prev,
        tech_stack: extractedData.skills || [],
        target_roles: extractedData.roles || prev.target_roles,
        cv_data: { ...prev.cv_data, nationality: extractedData.nationality || prev.cv_data?.nationality },
      }));

      if (extractedData.languages && extractedData.languages.length > 0) {
        const parsedLanguages = extractedData.languages
          .map((lang: any) => {
            if (typeof lang === 'object' && lang.language && lang.level) {
              return { language: lang.language.trim() || '', level: lang.level.trim() || 'Intermediate' };
            }
            return null;
          })
          .filter((l: any) => l && l.language);
        if (parsedLanguages.length > 0) setLanguages(parsedLanguages);
      }

      setCvSuccess(`CV processed - ${extractedData.skills?.length || 0} skills extracted`);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setTimeout(() => handleSave(), 2000);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error('[CV UPLOAD] Error:', errorMsg);
      setCvError(`CV upload failed: ${errorMsg}`);
    } finally {
      setCvUploading(false);
    }
  };

  const validateLanguages = (): boolean => {
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

      if (!validateLanguages()) {
        setSaving(false);
        return;
      }

      const profileToSave = {
        ...formData,
        cv_data: {
          ...formData.cv_data,
          languages: languages,
          nationality: nationality
        }
      };

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

  const updateTargetRole = (index: number, value: string) => {
    const roles = formData.target_roles || [];
    const newRoles = [...roles];
    newRoles[index] = value;
    setFormData({ ...formData, target_roles: newRoles });
  };

  const removeTargetRole = (index: number) => {
    const roles = formData.target_roles || [];
    setFormData({ ...formData, target_roles: roles.filter((_, i) => i !== index) });
  };

  const addTargetRole = () => {
    const roles = formData.target_roles || [];
    setFormData({ ...formData, target_roles: [...roles, ''] });
  };

  const updateTechStack = (index: number, value: string) => {
    const stack = formData.tech_stack || [];
    const newStack = [...stack];
    newStack[index] = value;
    setFormData({ ...formData, tech_stack: newStack });
  };

  const removeTechStack = (index: number) => {
    const stack = formData.tech_stack || [];
    setFormData({ ...formData, tech_stack: stack.filter((_, i) => i !== index) });
  };

  const addTechStack = () => {
    const stack = formData.tech_stack || [];
    setFormData({ ...formData, tech_stack: [...stack, ''] });
  };

  const updateLanguage = (index: number, field: 'language' | 'level', value: string) => {
    const newLanguages = [...languages];
    newLanguages[index] = { ...newLanguages[index], [field]: value };
    setLanguages(newLanguages);
  };

  const removeLanguage = (index: number) => {
    setLanguages(languages.filter((_, i) => i !== index));
  };

  const addLanguage = () => {
    setLanguages([...languages, { language: '', level: 'Intermediate' }]);
  };

  if (loading) {
    return (
      <div style={{ ...theme as any, minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg)', color: 'var(--text)', fontFamily: "'Figtree', sans-serif" }}>
        Loading profile...
      </div>
    );
  }

  const firstName = (profile as any)?.cv_data?.name?.split(' ')[0] || (profile as any)?.name?.split(' ')[0] || 'User';
  const initials = firstName.charAt(0).toUpperCase();

  return (
    <div style={{ ...theme as any, minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text)', fontFamily: "'Figtree', sans-serif" }}>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <ScoutSidebar isDark={isDark} setIsDark={setIsDark} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        {/* Main Content */}
        <main style={{ flex: 1, maxWidth: '900px', margin: '0 auto', padding: '44px 50px 70px', width: '100%' }}>
          {/* 1. Header Row */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px', marginBottom: '32px', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px', flex: 1 }}>
              {/* Avatar Blob */}
              <div style={{ width: '68px', height: '68px', borderRadius: '56% 44% 48% 52% / 50% 55% 45% 50%', background: `radial-gradient(circle at 30% 26%, var(--color-accent-200), var(--color-accent) 55%, var(--color-accent-700) 100%)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 68px', fontFamily: "'Caprasimo', serif", fontSize: '28px', fontWeight: 400, color: 'var(--bg)' }}>
                {initials}
              </div>

              {/* Name & Email */}
              <div>
                <h1 style={{ fontFamily: "'Caprasimo', serif", fontSize: '32px', fontWeight: 400, color: 'var(--text)', margin: 0 }}>
                  {(profile as any)?.cv_data?.name || (profile as any)?.name || 'User Profile'}
                </h1>
                <p style={{ fontSize: '13.5px', color: 'var(--muted)', margin: '4px 0 0' }}>
                  {(profile as any)?.email || 'email@example.com'}
                </p>
              </div>
            </div>

            {/* Save Changes Button */}
            <button onClick={handleSave} disabled={saving} style={{ padding: '10px 20px', borderRadius: '999px', border: 'none', background: 'var(--card)', color: saving ? 'var(--muted)' : 'var(--color-accent-700)', font: '600 13px var(--font-body)', cursor: saving ? 'not-allowed' : 'pointer', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', flex: '0 0 auto', whiteSpace: 'nowrap', opacity: saving ? 0.6 : 1 }}>
              {saving ? 'Saving...' : 'Save changes'}
            </button>
          </div>

          {/* 2. Résumé Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '56% 44% 48% 52% / 50% 55% 45% 50%', background: `radial-gradient(circle at 30% 26%, var(--color-accent-200), var(--color-accent) 55%, var(--color-accent-700) 100%)`, flex: '0 0 44px' }} />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>Résumé on file</div>
                <div style={{ fontSize: '12px', color: 'var(--faint)', marginTop: '2px' }}>{cvSuccess || cvError || 'resume.pdf • Updated 3 days ago'}</div>
              </div>
            </div>
            <button onClick={() => fileInputRef.current?.click()} disabled={cvUploading} style={{ padding: '10px 16px', borderRadius: '999px', border: 'none', background: 'var(--bg)', color: 'var(--muted)', font: '600 12px var(--font-body)', cursor: cvUploading ? 'not-allowed' : 'pointer', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', flex: '0 0 auto', whiteSpace: 'nowrap', opacity: cvUploading ? 0.6 : 1 }}>
              {cvUploading ? 'Uploading...' : 'Upload new CV'}
            </button>
            <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx" onChange={handleCvUpload} style={{ display: 'none' }} />
          </div>

          {/* 3. Gmail Connection Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
              <Mail size={24} style={{ color: 'var(--color-accent-2)', flex: '0 0 auto' }} />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>Gmail {gmailStatus.connected ? 'connected' : 'not connected'}</div>
                <div style={{ fontSize: '12px', color: 'var(--faint)', marginTop: '2px' }}>{gmailStatus.email || 'No email connected'}</div>
              </div>
            </div>
            <button onClick={gmailStatus.connected ? handleDisconnectGmail : handleConnectGmail} disabled={gmailLoading} style={{ padding: '10px 16px', borderRadius: '999px', border: 'none', background: 'var(--bg)', color: 'var(--muted)', font: '600 12px var(--font-body)', cursor: gmailLoading ? 'not-allowed' : 'pointer', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', flex: '0 0 auto', whiteSpace: 'nowrap', opacity: gmailLoading ? 0.6 : 1 }}>
              {gmailLoading ? 'Loading...' : gmailStatus.connected ? 'Disconnect' : 'Connect'}
            </button>
          </div>

          {/* 4. Target Roles Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Target Roles</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {(formData.target_roles || []).map((role: string, i: number) => (
                <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <input value={role} onChange={(e) => updateTargetRole(i, e.target.value)} placeholder="Role" style={{ padding: '6px 12px', borderRadius: '999px', fontSize: '13px', border: 'none', background: 'var(--bg)', color: 'var(--text)', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', width: '120px' }} />
                  <button onClick={() => removeTargetRole(i)} style={{ padding: '4px 8px', borderRadius: '999px', border: 'none', background: 'transparent', color: 'var(--faint)', cursor: 'pointer', fontSize: '12px' }}>×</button>
                </div>
              ))}
              <button onClick={addTargetRole} style={{ padding: '6px 12px', borderRadius: '999px', fontSize: '13px', color: 'var(--faint)', border: '1px dashed var(--faint)', background: 'transparent', cursor: 'pointer' }}>
                + Add role
              </button>
            </div>
          </div>

          {/* 5. Skills Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Skills</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {(formData.tech_stack || []).map((skill: string, i: number) => (
                <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <input value={skill} onChange={(e) => updateTechStack(i, e.target.value)} placeholder="Skill" style={{ padding: '8px 14px', borderRadius: '999px', fontSize: '13px', border: 'none', background: 'var(--color-accent-2-100)', color: 'var(--color-accent-2-800)', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', width: '120px' }} />
                  <button onClick={() => removeTechStack(i)} style={{ padding: '4px 8px', borderRadius: '999px', border: 'none', background: 'transparent', color: 'var(--faint)', cursor: 'pointer', fontSize: '12px' }}>×</button>
                </div>
              ))}
              <button onClick={addTechStack} style={{ padding: '8px 14px', borderRadius: '999px', fontSize: '13px', color: 'var(--faint)', border: '1px dashed var(--faint)', background: 'transparent', cursor: 'pointer' }}>
                + Add skill
              </button>
            </div>
          </div>

          {/* 6. Languages + Nationality */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            {/* Languages */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '16px', textTransform: 'uppercase' }}>Languages</div>
              {languages.map((lang: any, i: number) => (
                <div key={i} style={{ display: 'flex', gap: '8px', justifyContent: 'space-between', alignItems: 'center', marginBottom: i === languages.length - 1 ? 0 : '12px' }}>
                  <input value={lang.language} onChange={(e) => updateLanguage(i, 'language', e.target.value)} placeholder="Language" style={{ padding: '6px 12px', borderRadius: '999px', background: 'var(--bg)', color: 'var(--text)', font: '600 12px var(--font-body)', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', width: '60%' }} />
                  <select value={lang.level} onChange={(e) => updateLanguage(i, 'level', e.target.value)} style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--text)', font: '600 12px var(--font-body)', padding: '6px 12px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', width: '35%', paddingRight: '24px', cursor: 'pointer' }}>
                    <option>Native</option>
                    <option>Fluent</option>
                    <option>Intermediate</option>
                    <option>Basic</option>
                  </select>
                  <button onClick={() => removeLanguage(i)} style={{ padding: '4px 8px', borderRadius: '999px', border: 'none', background: 'transparent', color: 'var(--faint)', cursor: 'pointer', fontSize: '12px' }}>×</button>
                </div>
              ))}
              <button onClick={addLanguage} style={{ marginTop: languages.length > 0 ? '12px' : 0, padding: '6px 12px', borderRadius: '999px', fontSize: '12px', color: 'var(--faint)', border: '1px dashed var(--faint)', background: 'transparent', cursor: 'pointer', width: '100%' }}>
                + Add language
              </button>
            </div>

            {/* Nationality */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '16px', textTransform: 'uppercase' }}>Nationality</div>
              <select value={nationality} onChange={(e) => setNationality(e.target.value)} style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--text)', font: '600 12px var(--font-body)', padding: '6px 12px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', width: '100%', paddingRight: '24px', cursor: 'pointer' }}>
                <option>Mexican</option>
                <option>American</option>
                <option>Canadian</option>
                <option>Spanish</option>
                <option>Other</option>
              </select>
            </div>
          </div>

          {/* 7. Where you'll work */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '16px', textTransform: 'uppercase' }}>Where you'll work</div>

            {/* Modality */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text)', display: 'block', marginBottom: '8px' }}>Modality</label>
              <select value={formData.preferred_modality || ''} onChange={(e) => setFormData({...formData, preferred_modality: e.target.value as any})} style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--color-accent-700)', font: '700 13px var(--font-body)', padding: '10px 16px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)', width: '100%', paddingRight: '28px', cursor: 'pointer' }}>
                <option value="">Select...</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="on-site">On-site</option>
              </select>
            </div>

            {/* Priority Country */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text)', display: 'block', marginBottom: '8px' }}>Priority country</label>
              <select value={formData.preferred_countries?.[0] || ''} onChange={(e) => setFormData({...formData, preferred_countries: [e.target.value, ...(formData.preferred_countries?.slice(1) || [])]})} style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--text)', font: '600 12px var(--font-body)', padding: '6px 12px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', width: '100%', paddingRight: '24px', cursor: 'pointer' }}>
                <option value="">Select...</option>
                <option value="Mexico">Mexico</option>
                <option value="United States">United States</option>
                <option value="Canada">Canada</option>
              </select>
            </div>

            {/* Also searching in */}
            <div>
              <div style={{ fontSize: '12px', color: 'var(--faint)', marginBottom: '8px' }}>Also searching in</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {((formData.preferred_countries || []).slice(1) || []).map((country: string, i: number) => (
                  <span key={i} style={{ padding: '6px 12px', borderRadius: '999px', fontSize: '12px', color: 'var(--faint)', background: 'transparent', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)' }}>
                    {country}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 8. Minimum Salary + Links */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Salary */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Minimum salary</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontFamily: "'Caprasimo', serif", fontSize: '24px', fontWeight: 400, color: 'var(--text)' }}>$</span>
                <input type="number" value={formData.salary_min || 100000} onChange={(e) => setFormData({...formData, salary_min: parseInt(e.target.value) || 0})} style={{ fontFamily: "'Caprasimo', serif", fontSize: '24px', fontWeight: 400, color: 'var(--text)', background: 'var(--bg)', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', borderRadius: '8px', padding: '8px 12px', width: '100%' }} />
              </div>
            </div>

            {/* Links */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Links</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 700, color: 'var(--faint)', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>GitHub</label>
                  <input type="text" value={(formData as any)?.github_url || ''} onChange={(e) => setFormData({...formData, github_url: e.target.value})} placeholder="username" style={{ fontSize: '13px', color: 'var(--text)', background: 'var(--bg)', border: 'none', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', borderRadius: '8px', padding: '6px 10px', width: '100%' }} />
                </div>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 700, color: 'var(--faint)', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>LinkedIn</label>
                  <input type="text" value={(formData as any)?.linkedin_url || ''} onChange={(e) => setFormData({...formData, linkedin_url: e.target.value})} placeholder="username" style={{ fontSize: '13px', color: 'var(--text)', background: 'var(--bg)', border: 'none', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', borderRadius: '8px', padding: '6px 10px', width: '100%' }} />
                </div>
              </div>
            </div>
          </div>

          {/* Success/Error Messages */}
          {success && (
            <div style={{ background: '#d4edda', color: '#155724', padding: '12px 16px', borderRadius: '8px', marginTop: '20px', fontSize: '14px' }}>
              ✓ Profile saved successfully!
            </div>
          )}
          {error && (
            <div style={{ background: '#f8d7da', color: '#721c24', padding: '12px 16px', borderRadius: '8px', marginTop: '20px', fontSize: '14px' }}>
              ✗ {error}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
