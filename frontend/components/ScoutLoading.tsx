'use client';

interface ScoutLoadingProps {
  message?: string;
}

export function ScoutLoading({ message = 'Loading...' }: ScoutLoadingProps) {
  return (
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
          0%, 49%, 51%, 100% {
            scaleY: 1;
          }
          50% {
            scaleY: 0.1;
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

        .scout-blob {
          animation: scoutBounce 1.2s ease-in-out infinite;
        }

        .scout-eye {
          animation: scoutBlink 1.2s ease-in-out infinite;
          transform-origin: center;
        }

        .scout-shadow {
          animation: shadowShrink 1.2s ease-in-out infinite;
        }
      `}
      </style>

      {/* Scout Blob */}
      <div className="scout-blob" style={{
        position: 'relative',
        width: '80px',
        height: '80px',
        marginBottom: '24px',
      }}>
        {/* Shadow */}
        <div className="scout-shadow" style={{
          position: 'absolute',
          bottom: '-16px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '60px',
          height: '8px',
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 70%)',
          borderRadius: '50%',
        }} />

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
          animationDelay: '0.1s',
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
  );
}