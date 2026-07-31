'use client';

import { useEffect, useRef, useState } from 'react';
import Globe from 'react-globe.gl';
import { getJobsByCountry } from '@/lib/api';

interface CountryData {
  country: string;
  country_code: string;
  count: number;
  lat: number;
  lng: number;
}

export function GlobeComponent() {
  const globeEl = useRef<any>(null);
  const [countries, setCountries] = useState<CountryData[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);

  useEffect(() => {
    const loadCountries = async () => {
      try {
        setLoading(true);
        const data = await getJobsByCountry();
        setCountries(data);

        // Auto-rotate
        if (globeEl.current) {
          globeEl.current.controls().autoRotate = true;
          globeEl.current.controls().autoRotateSpeed = 1;
        }
      } catch (err) {
        console.error('Failed to load countries:', err);
      } finally {
        setLoading(false);
      }
    };

    loadCountries();
  }, []);

  const getMarkerSize = (count: number) => {
    const maxCount = Math.max(...countries.map(c => c.count), 1);
    return (count / maxCount) * 1.5 + 0.5;
  };

  const getComputedStyle = (varName: string) => {
    if (typeof window === 'undefined') return '#c67139';
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  };

  const accentColor = '#c67139';
  const cardBg = '#fffaf1';

  const pointsData = countries.map(country => ({
    lat: country.lat,
    lng: country.lng,
    size: getMarkerSize(country.count),
    color: accentColor,
    label: `${country.country}: ${country.count} jobs`,
    country: country.country,
    count: country.count,
  }));

  if (loading) {
    return (
      <div
        style={{
          width: '100%',
          height: '500px',
          borderRadius: '24px',
          background: 'var(--dcard)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--dmuted)',
          fontSize: '14px',
        }}
      >
        Loading globe...
      </div>
    );
  }

  return (
    <div
      style={{
        width: '100%',
        borderRadius: '24px',
        overflow: 'hidden',
        boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)',
        background: 'var(--dcard)',
      }}
    >
      <Globe
        ref={globeEl}
        height={500}
        width={typeof window !== 'undefined' ? window.innerWidth - 120 : 800}
        backgroundColor="rgba(0,0,0,0)"
        showAtmosphere={true}
        atmosphereColor="#f4d9c6"
        atmosphereAltitude={0.1}
        globeImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg"
        pointsData={pointsData}
        pointAltitude="size"
        pointColor={() => accentColor}
        pointRadius={() => 0.4}
        pointLabel={(d: any) => d.label}
        onPointHover={(point: any) => {
          setHoveredCountry(point ? point.country : null);
        }}
        pointsMerge={true}
        rendererConfig={{ antialias: true }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: '16px',
          left: '16px',
          fontSize: '12px',
          color: 'var(--muted)',
          pointerEvents: 'none',
        }}
      >
        {hoveredCountry && <div>{hoveredCountry}</div>}
        <div style={{ fontSize: '11px', color: 'var(--faint)', marginTop: '4px' }}>
          Hover over markers to see countries
        </div>
      </div>
    </div>
  );
}
