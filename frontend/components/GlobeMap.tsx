'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import { getJobsByCountry } from '@/lib/api';

interface CountryData {
  country: string;
  country_code: string;
  count: number;
  lat: number;
  lng: number;
}

export function GlobeMap() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [countries, setCountries] = useState<CountryData[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDark, setIsDark] = useState(false);

  // Theme colors
  const lightTheme = {
    ocean: '#f6ecd9',
    land: '#847a5e',
    grid: '#e6dcc4',
  };

  const darkTheme = {
    ocean: '#3a2c1e',
    land: '#c7b59c',
    grid: '#4a3b28',
  };

  const theme = isDark ? darkTheme : lightTheme;

  useEffect(() => {
    // Check initial theme
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
    const isDarkTheme = bg.includes('2b2118') || bg.includes('43') || parseInt(bg.substring(1), 16) < 0x800000;
    setIsDark(isDarkTheme);

    // Listen for theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mediaQuery.addEventListener('change', handleChange);

    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    const loadAndRenderGlobe = async () => {
      try {
        setLoading(true);
        const countriesData = await getJobsByCountry();
        setCountries(countriesData);

        if (!svgRef.current) return;

        const size = 480;
        const radius = 229;

        const projection = d3
          .geoOrthographic()
          .scale(radius)
          .translate([size / 2, size / 2])
          .rotate([50, -22, 0])
          .clipAngle(90);

        const path = d3.geoPath(projection);
        const graticule = d3.geoGraticule();

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        // Fetch world topology
        const response = await fetch('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json');
        const topology = await response.json();
        const countries = topojson.feature(topology, topology.objects.countries) as any;

        // Draw sphere (ocean)
        svg
          .append('path')
          .attr('d', path({ type: 'Sphere' }))
          .attr('fill', theme.ocean);

        // Draw graticule (optional faint grid)
        svg
          .append('path')
          .attr('d', path(graticule()))
          .attr('fill', 'none')
          .attr('stroke', theme.grid)
          .attr('stroke-width', 0.5)
          .attr('opacity', 0.3);

        // Draw countries
        svg
          .selectAll('path.country')
          .data(countries.features)
          .enter()
          .append('path')
          .attr('class', 'country')
          .attr('d', path as any)
          .attr('fill', theme.land)
          .attr('stroke', theme.ocean)
          .attr('stroke-width', 0.6);

        // Add job source markers
        countriesData.forEach((country: CountryData, index: number) => {
          const coords = projection([country.lng, country.lat]);
          if (coords && coords[0] !== null) {
            const g = svg.append('g').attr('transform', `translate(${coords[0]},${coords[1]})`);

            // Pulsing ring animation only for newest marker
            if (index === 0) {
              g.append('circle')
                .attr('r', 5)
                .attr('fill', 'none')
                .attr('stroke', '#c67139')
                .attr('stroke-width', 1)
                .attr('opacity', 0.4)
                .style('animation', 'pulse-beat 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite');
            }

            // Main marker dot - only animate newest one
            g.append('circle')
              .attr('r', 5)
              .attr('fill', '#c67139')
              .attr('opacity', 0.8)
              .style('filter', 'drop-shadow(0 2px 6px rgba(198, 113, 57, 0.5))')
              .style('animation', index === 0 ? 'pulse-beat 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none');

            // Tooltip on hover
            g.append('title').text(`${country.country}: ${country.count} jobs`);
          }
        });

        // Add pulse animation styles
        const style = document.createElement('style');
        style.textContent = `
          @keyframes pulse-beat {
            0%, 100% {
              r: 4px;
              opacity: 1;
            }
            50% {
              r: 8px;
              opacity: 0.5;
            }
          }
        `;
        document.head.appendChild(style);
      } catch (err) {
        console.error('Failed to render globe:', err);
      } finally {
        setLoading(false);
      }
    };

    loadAndRenderGlobe();
  }, [isDark]);

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
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '32px 28px',
        background: 'var(--dcard)',
        boxShadow: 'inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)',
        gap: '24px',
      }}
    >
      <div
        style={{
          position: 'relative',
          width: '460px',
          height: '460px',
          borderRadius: '50%',
          overflow: 'hidden',
          boxShadow: 'none',
        }}
      >
        <svg
          ref={svgRef}
          width="480"
          height="480"
          viewBox="0 0 480 480"
          style={{
            display: 'block',
            width: '100%',
            height: '100%',
          }}
        />
        {/* Glossy highlight overlay - must be on top of SVG */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            pointerEvents: 'none',
            background: `radial-gradient(circle at 30% 26%, rgba(255,255,255,.55), transparent 55%), radial-gradient(circle at 72% 78%, rgba(64,35,16,.4), transparent 55%)`,
          }}
        />
      </div>

      {/* Country chips */}
      <div
        style={{
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {countries.slice(0, 5).map((country) => (
          <span
            key={country.country_code}
            className="inset-chip"
            style={{
              fontSize: '12px',
              color: 'var(--text)',
              borderRadius: '999px',
              padding: '6px 14px',
              background: 'var(--dbg)',
              boxShadow: 'inset 0 1px 3px rgba(32,30,29,.15)',
            }}
          >
            {country.country} • {country.count}
          </span>
        ))}
      </div>
    </div>
  );
}
