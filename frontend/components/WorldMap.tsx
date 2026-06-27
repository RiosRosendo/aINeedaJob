'use client';

import { useEffect, useState } from 'react';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';
import { X } from 'lucide-react';
import { getJobsByCountry, getJobsByCountryDetail } from '@/lib/api';

interface CountryData {
  country: string;
  country_code: string;
  count: number;
  lat: number;
  lng: number;
}

interface CountryJob {
  id: string;
  title: string;
  company: string;
  location: string;
  fit_score?: number;
  app_status?: string;
}

const geoUrl = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

export function WorldMap() {
  const [countries, setCountries] = useState<CountryData[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<CountryData | null>(null);
  const [countryJobs, setCountryJobs] = useState<CountryJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCountries = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getJobsByCountry();
        setCountries(data);
      } catch (err) {
        console.error('Failed to load countries:', err);
        setError('Failed to load map data');
      } finally {
        setLoading(false);
      }
    };

    loadCountries();
  }, []);

  const handleCountryClick = async (country: CountryData) => {
    setSelectedCountry(country);
    setJobsLoading(true);
    try {
      const jobs = await getJobsByCountryDetail(country.country_code);
      setCountryJobs(jobs);
    } catch (err) {
      console.error('Failed to load country jobs:', err);
      setCountryJobs([]);
    } finally {
      setJobsLoading(false);
    }
  };

  const countryMap = new Map(countries.map(c => [c.country_code, c]));
  const maxJobCount = Math.max(...countries.map(c => c.count), 1);

  if (loading) {
    return (
      <div
        className="col-span-2 border rounded-lg p-8 text-center"
        style={{
          borderColor: 'var(--border)',
          backgroundColor: 'var(--card)',
          color: 'var(--muted)',
        }}
      >
        Loading world map...
      </div>
    );
  }

  if (error || countries.length === 0) {
    return (
      <div
        className="col-span-2 border rounded-lg p-8 text-center"
        style={{
          borderColor: 'var(--border)',
          backgroundColor: 'var(--card)',
          color: 'var(--muted)',
        }}
      >
        {error || 'No jobs found across countries'}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-6 mb-10">
      {/* Map Container */}
      <div
        className="col-span-2 border rounded-lg overflow-hidden"
        style={{
          borderColor: 'var(--border)',
          backgroundColor: '#0d1117',
          minHeight: '400px',
        }}
      >
        <ComposableMap projection="geoMercator">
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  style={{
                    default: {
                      fill: '#1e2a3a',
                      stroke: '#0d1117',
                      strokeWidth: 0.75,
                      outline: 'none',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease',
                    },
                    hover: {
                      fill: '#2d3a4a',
                      stroke: '#444c56',
                      strokeWidth: 0.75,
                      outline: 'none',
                      cursor: 'pointer',
                    },
                    pressed: {
                      fill: '#2d3a4a',
                      stroke: '#444c56',
                      strokeWidth: 0.75,
                      outline: 'none',
                    },
                  }}
                />
              ))
            }
          </Geographies>

          {/* Job location markers */}
          {countries.map((country) => (
            <Marker
              key={country.country_code}
              coordinates={[country.lng, country.lat]}
              onMouseEnter={() => setHoveredCountry(country.country_code)}
              onMouseLeave={() => setHoveredCountry(null)}
              onClick={() => handleCountryClick(country)}
              style={{ cursor: 'pointer' }}
            >
              <g>
                {/* Pulsing rings */}
                <circle
                  cx={0}
                  cy={0}
                  r={8}
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth={1.5}
                  opacity={0.3}
                  style={{
                    animation: 'pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                  }}
                />

                {/* Main circle */}
                <circle
                  cx={0}
                  cy={0}
                  r={Math.min(25, Math.max(8, (country.count / maxJobCount) * 25))}
                  fill="#3b82f6"
                  opacity={hoveredCountry === country.country_code ? 0.9 : 0.8}
                  style={{
                    filter: 'drop-shadow(0 4px 12px rgba(59, 130, 246, 0.4))',
                    transition: 'all 0.2s ease',
                  }}
                />

                {/* Tooltip */}
                {hoveredCountry === country.country_code && (
                  <g>
                    <rect
                      x={-50}
                      y={-45}
                      width={100}
                      height={40}
                      rx={6}
                      fill="#1e2a3a"
                      stroke="#3b82f6"
                      strokeWidth={1}
                      style={{
                        filter: 'drop-shadow(0 4px 12px rgba(0, 0, 0, 0.5))',
                      }}
                    />
                    <text
                      x={0}
                      y={-25}
                      textAnchor="middle"
                      fill="#e1e8ed"
                      fontSize={12}
                      fontWeight="bold"
                    >
                      {country.country}
                    </text>
                    <text
                      x={0}
                      y={-12}
                      textAnchor="middle"
                      fill="#8b949e"
                      fontSize={11}
                    >
                      {country.count} job{country.count !== 1 ? 's' : ''}
                    </text>
                  </g>
                )}
              </g>
            </Marker>
          ))}
        </ComposableMap>

        {/* Legend */}
        <div
          className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent"
          style={{
            fontSize: '12px',
            color: '#8b949e',
          }}
        >
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: '#3b82f6' }}
              />
              <span>Jobs found in country</span>
            </div>
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full border"
                style={{ borderColor: '#3b82f6' }}
              />
              <span>Hover for details</span>
            </div>
            <div style={{ color: '#3b82f6' }} className="font-medium ml-auto">
              Click to view jobs →
            </div>
          </div>
        </div>
      </div>

      {/* Side Panel - Country Jobs */}
      {selectedCountry && (
        <div
          className="col-span-1 border rounded-lg overflow-hidden flex flex-col"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
            maxHeight: '400px',
          }}
        >
          {/* Header */}
          <div
            className="p-4 border-b flex items-center justify-between flex-shrink-0"
            style={{ borderColor: 'var(--border)' }}
          >
            <div>
              <h3
                className="text-sm font-bold"
                style={{ color: 'var(--text)' }}
              >
                {selectedCountry.country}
              </h3>
              <p
                className="text-xs mt-1"
                style={{ color: 'var(--muted)' }}
              >
                {selectedCountry.count} job{selectedCountry.count !== 1 ? 's' : ''}
              </p>
            </div>
            <button
              onClick={() => {
                setSelectedCountry(null);
                setCountryJobs([]);
              }}
              className="p-1.5 rounded hover:opacity-70 transition-opacity"
              style={{ color: 'var(--muted)' }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Jobs List */}
          <div className="flex-1 overflow-y-auto">
            {jobsLoading ? (
              <div
                className="p-6 text-center"
                style={{ color: 'var(--muted)' }}
              >
                <div className="inline-block">
                  <div
                    className="w-8 h-8 border-2 border-transparent rounded-full animate-spin"
                    style={{
                      borderTopColor: 'var(--accent)',
                      borderRightColor: 'var(--accent)',
                    }}
                  />
                </div>
              </div>
            ) : countryJobs.length > 0 ? (
              <div className="p-3 space-y-2">
                {countryJobs.map((job) => (
                  <div
                    key={job.id}
                    className="p-3 rounded border transition-all hover:border-opacity-100"
                    style={{
                      borderColor: 'var(--border)',
                      backgroundColor: 'var(--bg)',
                    }}
                    onMouseEnter={(e) => {
                      const el = e.currentTarget as HTMLDivElement;
                      el.style.backgroundColor = 'var(--sidebar-active)';
                      el.style.borderColor = 'var(--border-strong)';
                    }}
                    onMouseLeave={(e) => {
                      const el = e.currentTarget as HTMLDivElement;
                      el.style.backgroundColor = 'var(--bg)';
                      el.style.borderColor = 'var(--border)';
                    }}
                  >
                    <div
                      className="text-xs font-semibold truncate mb-0.5"
                      style={{ color: 'var(--text)' }}
                      title={job.title}
                    >
                      {job.title}
                    </div>
                    <div
                      className="text-xs truncate mb-2"
                      style={{ color: 'var(--muted)' }}
                      title={job.company}
                    >
                      {job.company}
                    </div>

                    {/* Score and Button */}
                    <div className="flex items-center justify-between gap-2">
                      {job.fit_score !== undefined && (
                        <div
                          className="text-xs font-bold px-2 py-1 rounded flex-shrink-0"
                          style={{
                            backgroundColor:
                              job.fit_score >= 85
                                ? '#10b98120'
                                : job.fit_score >= 60
                                  ? '#f59e0b20'
                                  : '#ef444420',
                            color:
                              job.fit_score >= 85
                                ? '#10b981'
                                : job.fit_score >= 60
                                  ? '#f59e0b'
                                  : '#ef4444',
                          }}
                        >
                          {Math.round(job.fit_score)}%
                        </div>
                      )}
                      <button
                        className="flex-1 text-xs px-2 py-1.5 rounded font-medium transition-all text-white"
                        style={{
                          backgroundColor: '#3b82f6',
                          border: '1px solid #3b82f6',
                        }}
                        onMouseEnter={(e) => {
                          const el = e.currentTarget as HTMLButtonElement;
                          el.style.backgroundColor = '#2563eb';
                          el.style.borderColor = '#2563eb';
                        }}
                        onMouseLeave={(e) => {
                          const el = e.currentTarget as HTMLButtonElement;
                          el.style.backgroundColor = '#3b82f6';
                          el.style.borderColor = '#3b82f6';
                        }}
                      >
                        ✓ Approve
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div
                className="p-6 text-center text-xs"
                style={{ color: 'var(--muted)' }}
              >
                No jobs found
              </div>
            )}
          </div>
        </div>
      )}

      {/* Top Countries List (when no country selected) */}
      {!selectedCountry && (
        <div
          className="col-span-1 border rounded-lg p-4 overflow-y-auto"
          style={{
            borderColor: 'var(--border)',
            backgroundColor: 'var(--card)',
            maxHeight: '400px',
          }}
        >
          <h3
            className="text-sm font-bold mb-3"
            style={{ color: 'var(--text)' }}
          >
            Top Countries
          </h3>
          <div className="space-y-2">
            {countries.slice(0, 5).map((country) => (
              <button
                key={country.country_code}
                onClick={() => handleCountryClick(country)}
                className="w-full text-left p-3 rounded border transition-all"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--bg)',
                  color: 'var(--text)',
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.backgroundColor = 'var(--sidebar-active)';
                  el.style.borderColor = 'var(--border-strong)';
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.backgroundColor = 'var(--bg)';
                  el.style.borderColor = 'var(--border)';
                }}
              >
                <div className="text-xs font-semibold">{country.country}</div>
                <div
                  className="text-xs mt-1"
                  style={{ color: 'var(--muted)' }}
                >
                  {country.count} jobs
                </div>
                <div
                  className="w-full h-1 rounded mt-2 bg-opacity-30"
                  style={{
                    backgroundColor: '#3b82f6',
                    width: `${(country.count / maxJobCount) * 100}%`,
                  }}
                />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Global pulse animation style */}
      <style>{`
        @keyframes pulse-ring {
          0% {
            r: 8px;
            opacity: 0.8;
          }
          100% {
            r: 25px;
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
