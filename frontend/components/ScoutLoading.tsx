'use client';

import { useState, useEffect } from 'react';
import { useScout } from '@/contexts/ScoutContext';

interface ScoutLoadingProps {
  message?: string;
}

export function ScoutLoading({ message = 'Loading...' }: ScoutLoadingProps) {
  const { isLoading } = useScout();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(true);
    }, 300);
    return () => clearTimeout(timer);
  }, []);
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 'calc(100vh - 200px)',
      width: '100%',
      flex: 1,
    }}>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
      }}>
      <style>{`
        @keyframes scoutBounce {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-20px);
          }
        }

        @keyframes scoutBlink {
          0%, 92%, 100% {
            transform: scaleY(1);
          }
          95% {
            transform: scaleY(0.15);
          }
        }

        @keyframes shadowShrink {
          0%, 100% {
            transform: scaleX(1);
            opacity: 0.3;
          }
          50% {
            transform: scaleX(0.6);
            opacity: 0.1;
          }
        }

        @keyframes ainBreathe {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.08);
          }
        }

        @keyframes scoutPopIn {
          0% {
            transform: scale(0);
            opacity: 0;
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }

        .scout-blob {
          animation: scoutBounce 1.2s ease-in-out infinite, ainBreathe 3.2s ease-in-out infinite;
        }

        .scout-eye {
          animation: scoutBlink 4.5s ease-in-out infinite;
          transform-origin: center;
        }

        .scout-shadow {
          animation: shadowShrink 1.2s ease-in-out infinite;
        }
      `}
      </style>

      {/* Scout Blob with Shadow */}
      <div style={{
        position: 'relative',
        marginBottom: '24px',
        opacity: visible ? 1 : 0,
        transform: visible ? 'scale(1)' : 'scale(0)',
        transition: 'all 0.3s ease-out',
      }}>
        {/* Scout Blob */}
        <div className="scout-blob" style={{
          position: 'relative',
          width: '80px',
          height: '80px',
        }}>
          {/* Blob Body */}
          <div style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '58% 42% 45% 55% / 45% 55% 45% 55%',
            background: 'radial-gradient(circle at 30% 26%, var(--color-accent-200), var(--color-accent) 55%, var(--color-accent-700) 100%)',
          }} />

          {/* Left Eye */}
          <div className="scout-eye" style={{
            position: 'absolute',
            left: '25px',
            top: '28px',
            width: '8px',
            height: '8px',
            background: 'rgba(255,255,255,0.8)',
            borderRadius: '50%',
          }} />

          {/* Right Eye */}
          <div className="scout-eye" style={{
            position: 'absolute',
            right: '25px',
            top: '28px',
            width: '8px',
            height: '8px',
            background: 'rgba(255,255,255,0.8)',
            borderRadius: '50%',
          }} />

          {/* Mouth */}
          <div style={{
            position: 'absolute',
            left: '32%',
            top: '58%',
            width: '36%',
            height: '8px',
            borderRadius: '0 0 16px 16px',
            borderBottom: '2px solid var(--bg)',
          }} />
        </div>

        {/* Shadow */}
        <div className="scout-shadow" style={{
          position: 'absolute',
          bottom: '-12px',
          left: '10%',
          width: '80%',
          height: '8px',
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 70%)',
          borderRadius: '50%',
        }} />
      </div>

      {/* Message */}
      <p style={{
        fontFamily: 'var(--font-body)',
        fontSize: '14px',
        color: 'var(--muted)',
        margin: 0,
        textAlign: 'center',
      }}>
        {message}
      </p>
      </div>
    </div>
  );
}