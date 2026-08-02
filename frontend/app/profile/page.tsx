'use client';

import { useEffect, useState } from 'react';
import { getUserProfile } from '@/lib/api';
import { UserProfile } from '@/lib/types';
import { Mail } from 'lucide-react';
import { ScoutSidebar } from '@/components/ScoutSidebar';

export default function ProfilePage() {
  const [isDark, setIsDark] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

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
        const profileData = await getUserProfile();
        setProfile(profileData);
      } catch (error) {
        console.error('Failed to load profile:', error);
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, []);

  if (loading) {
    return (
      <div style={{ ...theme as any, minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg)', color: 'var(--text)', fontFamily: "'Figtree', sans-serif" }}>
        Loading profile...
      </div>
    );
  }

  const [sidebarOpen, setSidebarOpen] = useState(true);

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
            <button style={{ padding: '10px 20px', borderRadius: '999px', border: 'none', background: 'var(--card)', color: 'var(--color-accent-700)', font: '600 13px var(--font-body)', cursor: 'pointer', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', flex: '0 0 auto', whiteSpace: 'nowrap' }}>
              Save changes
            </button>
          </div>

          {/* 2. Résumé Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '56% 44% 48% 52% / 50% 55% 45% 50%', background: `radial-gradient(circle at 30% 26%, var(--color-accent-200), var(--color-accent) 55%, var(--color-accent-700) 100%)`, flex: '0 0 44px' }} />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>Résumé on file</div>
                <div style={{ fontSize: '12px', color: 'var(--faint)', marginTop: '2px' }}>resume.pdf • Updated 3 days ago</div>
              </div>
            </div>
            <button style={{ padding: '10px 16px', borderRadius: '999px', border: 'none', background: 'var(--bg)', color: 'var(--muted)', font: '600 12px var(--font-body)', cursor: 'pointer', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', flex: '0 0 auto', whiteSpace: 'nowrap' }}>
              Upload new CV
            </button>
          </div>

          {/* 3. Gmail Connection Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
              <Mail size={24} style={{ color: 'var(--color-accent-2)', flex: '0 0 auto' }} />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text)' }}>Gmail connected</div>
                <div style={{ fontSize: '12px', color: 'var(--faint)', marginTop: '2px' }}>a01198515@tec.mx</div>
              </div>
            </div>
            <button style={{ padding: '10px 16px', borderRadius: '999px', border: 'none', background: 'var(--bg)', color: 'var(--muted)', font: '600 12px var(--font-body)', cursor: 'pointer', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)', flex: '0 0 auto', whiteSpace: 'nowrap' }}>
              Disconnect
            </button>
          </div>

          {/* 4. Target Roles Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Target Roles</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {(profile?.target_roles || ['AI Engineer']).map((role: string, i: number) => (
                <span key={i} style={{ padding: '6px 12px', borderRadius: '999px', fontSize: '13px', color: 'var(--color-accent-700)', background: 'transparent', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)' }}>
                  {role}
                </span>
              ))}
              <button style={{ padding: '6px 12px', borderRadius: '999px', fontSize: '13px', color: 'var(--faint)', border: '1px dashed var(--faint)', background: 'transparent', cursor: 'pointer' }}>
                + Add role
              </button>
            </div>
          </div>

          {/* 5. Skills Card */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Skills</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {((profile as any)?.cv_data?.skills || ['Python', 'ROS2']).map((skill: string, i: number) => (
                <span key={i} style={{ padding: '8px 14px', borderRadius: '999px', fontSize: '13px', color: 'var(--color-accent-2-800)', background: 'var(--color-accent-2-100)', cursor: 'pointer', transition: 'transform 0.2s cubic-bezier(.34,1.56,.64,1)' }} onMouseEnter={(e) => { (e.currentTarget as any).style.transform = 'scale(1.06)'; }} onMouseLeave={(e) => { (e.currentTarget as any).style.transform = 'scale(1)'; }}>
                  {skill}
                </span>
              ))}
              <button style={{ padding: '8px 14px', borderRadius: '999px', fontSize: '13px', color: 'var(--faint)', border: '1px dashed var(--faint)', background: 'transparent', cursor: 'pointer' }}>
                + Add skill
              </button>
            </div>
          </div>

          {/* 6. Languages + Nationality */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
            {/* Languages */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '16px', textTransform: 'uppercase' }}>Languages</div>
              {((profile as any)?.cv_data?.languages || [{ language: 'Spanish', level: 'Native' }]).map((lang: any, i: number) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: i === ((profile as any)?.cv_data?.languages?.length || 1) - 1 ? 0 : '12px' }}>
                  <label style={{ fontSize: '13px', color: 'var(--text)' }}>{lang.language}</label>
                  <select style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--text)', font: '600 12px var(--font-body)', padding: '6px 12px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', paddingRight: '24px', cursor: 'pointer' }}>
                    <option>{lang.level}</option>
                    <option>Native</option>
                    <option>Fluent</option>
                    <option>Intermediate</option>
                    <option>Basic</option>
                  </select>
                </div>
              ))}
            </div>

            {/* Nationality */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '16px', textTransform: 'uppercase' }}>Nationality</div>
              <select style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--text)', font: '600 12px var(--font-body)', padding: '6px 12px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', width: '100%', paddingRight: '24px', cursor: 'pointer' }}>
                <option>{(profile as any)?.cv_data?.nationality || 'Mexican'}</option>
                <option>Mexican</option>
                <option>American</option>
                <option>Canadian</option>
                <option>Spanish</option>
              </select>
            </div>
          </div>

          {/* 7. Where you'll work */}
          <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', marginBottom: '20px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '16px', textTransform: 'uppercase' }}>Where you'll work</div>

            {/* Modality */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text)', display: 'block', marginBottom: '8px' }}>Modality</label>
              <select style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--color-accent-700)', font: '700 13px var(--font-body)', padding: '10px 16px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.2)', width: '100%', paddingRight: '28px', cursor: 'pointer' }}>
                <option>{profile?.preferred_modality || 'Remote'}</option>
                <option>Remote</option>
                <option>Hybrid</option>
                <option>On-site</option>
              </select>
            </div>

            {/* Priority Country */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text)', display: 'block', marginBottom: '8px' }}>Priority country</label>
              <select style={{ appearance: 'none', borderRadius: '999px', background: 'var(--bg)', color: 'var(--text)', font: '600 12px var(--font-body)', padding: '6px 12px', border: 'none', boxShadow: 'inset 0 2px 5px rgba(32,30,29,.18)', width: '100%', paddingRight: '24px', cursor: 'pointer' }}>
                <option>{(profile?.preferred_countries?.[0]) || 'Mexico'}</option>
                <option>Mexico</option>
                <option>United States</option>
                <option>Canada</option>
              </select>
            </div>

            {/* Also searching in */}
            <div>
              <div style={{ fontSize: '12px', color: 'var(--faint)', marginBottom: '8px' }}>Also searching in</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {((profile?.preferred_countries || []).slice(1) || []).map((country: string, i: number) => (
                  <span key={i} style={{ padding: '6px 12px', borderRadius: '999px', fontSize: '12px', color: 'var(--faint)', background: 'transparent', boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)' }}>
                    {country}
                  </span>
                ))}
                <button style={{ padding: '6px 12px', borderRadius: '999px', fontSize: '12px', color: 'var(--faint)', border: '1px dashed var(--faint)', background: 'transparent', cursor: 'pointer' }}>
                  + Add country
                </button>
              </div>
            </div>
          </div>

          {/* 8. Minimum Salary + Links */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Salary */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Minimum salary</div>
              <div style={{ fontFamily: "'Caprasimo', serif", fontSize: '26px', fontWeight: 400, color: 'var(--text)' }}>
                ${(profile?.salary_min || 100000).toLocaleString()}
              </div>
            </div>

            {/* Links */}
            <div style={{ background: 'var(--card)', borderRadius: '24px', padding: '22px', boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--faint)', marginBottom: '12px', textTransform: 'uppercase' }}>Links</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <a href={`https://github.com/${(profile as any)?.github_url || ''}`} style={{ fontSize: '13px', color: 'var(--color-accent)', textDecoration: 'none' }} target="_blank" rel="noopener noreferrer">
                  GitHub
                </a>
                <a href={`https://linkedin.com/in/${(profile as any)?.linkedin_url || ''}`} style={{ fontSize: '13px', color: 'var(--color-accent)', textDecoration: 'none' }} target="_blank" rel="noopener noreferrer">
                  LinkedIn
                </a>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
