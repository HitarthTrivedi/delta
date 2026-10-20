import React, { useEffect, useRef } from 'react';

const REDUCED_MOTION = typeof window !== 'undefined' && window.matchMedia
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * "Aria", the AI interviewer: an SVG face that lip-syncs to `getLevel()`
 * (0..1, read every animation frame, so no React re-render per frame), blinks,
 * and shows listening / thinking states.
 *
 * state: 'idle' | 'speaking' | 'listening' | 'thinking'
 */
export default function InterviewerAvatar({ state = 'idle', getLevel, size = 280 }) {
  const mouthRef = useRef(null);
  const smileRef = useRef(null);
  const eyesRef = useRef(null);

  // Lip-sync loop
  useEffect(() => {
    let raf;
    const tick = () => {
      const raw = getLevel ? getLevel() : 0;
      const level = REDUCED_MOTION ? raw * 0.4 : raw;
      if (mouthRef.current) {
        mouthRef.current.setAttribute('ry', (0.6 + level * 9).toFixed(2));
        mouthRef.current.setAttribute('rx', (11 + level * 3).toFixed(2));
      }
      if (smileRef.current) smileRef.current.style.opacity = String(Math.max(0, 1 - level * 2.2));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [getLevel]);

  // Natural blinking at random intervals
  useEffect(() => {
    if (REDUCED_MOTION) return undefined;
    let timer;
    const blink = () => {
      if (eyesRef.current) {
        eyesRef.current.style.transform = 'scaleY(0.1)';
        setTimeout(() => { if (eyesRef.current) eyesRef.current.style.transform = 'scaleY(1)'; }, 130);
      }
      timer = setTimeout(blink, 2200 + Math.random() * 3200);
    };
    timer = setTimeout(blink, 1500);
    return () => clearTimeout(timer);
  }, []);

  const tilt = !REDUCED_MOTION && state === 'listening' ? 'rotate(-3deg)' : 'rotate(0deg)';
  const gaze = state === 'thinking' ? -3 : 0;

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      {/* listening / speaking halo */}
      <div
        aria-hidden="true"
        className={!REDUCED_MOTION && (state === 'listening' || state === 'speaking') ? 'aria-halo' : ''}
        style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          boxShadow: state === 'listening' ? '0 0 0 3px rgba(74,222,128,0.55)'
            : state === 'speaking' ? '0 0 0 3px rgba(244,114,182,0.5)' : '0 0 0 1px rgba(255,255,255,0.12)',
          transition: 'box-shadow 300ms ease',
        }}
      />
      <svg
        viewBox="0 0 300 300"
        width={size}
        height={size}
        role="img"
        aria-label={`Aria, the AI interviewer, is ${state === 'idle' ? 'waiting' : state}`}
        style={{ borderRadius: '50%', background: 'radial-gradient(circle at 50% 35%, #3a3550 0%, #1b1a24 70%)', display: 'block' }}
      >
        <g style={{ transformOrigin: '150px 230px', transform: tilt, transition: 'transform 600ms ease' }}>
          {/* shoulders + blazer */}
          <path d="M40 300 C 50 235, 95 215, 150 215 C 205 215, 250 235, 260 300 Z" fill="#2c3e66" />
          <path d="M122 216 L150 262 L178 216 Z" fill="#f4f1ea" />
          <path d="M122 216 L150 262 L136 300 L104 300 Z" fill="#24345a" />
          <path d="M178 216 L150 262 L164 300 L196 300 Z" fill="#24345a" />
          {/* neck */}
          <rect x="132" y="180" width="36" height="42" rx="12" fill="#b9805e" />
          {/* hair back */}
          <path d="M78 130 C 70 60, 125 38, 152 40 C 196 40, 232 70, 224 140 C 230 185, 214 215, 200 222 L 100 222 C 84 212, 72 182, 78 130 Z" fill="#2a1c17" />
          {/* face */}
          <ellipse cx="150" cy="128" rx="58" ry="70" fill="#c98f6b" />
          {/* ears */}
          <ellipse cx="92" cy="132" rx="8" ry="13" fill="#bd8461" />
          <ellipse cx="208" cy="132" rx="8" ry="13" fill="#bd8461" />
          <circle cx="92" cy="148" r="3" fill="#e9c46a" />
          <circle cx="208" cy="148" r="3" fill="#e9c46a" />
          {/* hair fringe */}
          <path d="M92 108 C 98 62, 140 50, 160 58 C 182 52, 212 72, 210 112 C 196 86, 172 78, 150 84 C 128 76, 104 86, 92 108 Z" fill="#2a1c17" />
          {/* eyebrows (raise slightly when listening) */}
          <g style={{ transform: `translateY(${state === 'listening' ? -3 : 0}px)`, transition: 'transform 400ms ease' }}>
            <path d="M115 106 Q 128 99, 140 105" stroke="#2a1c17" strokeWidth="4" fill="none" strokeLinecap="round" />
            <path d="M160 105 Q 172 99, 185 106" stroke="#2a1c17" strokeWidth="4" fill="none" strokeLinecap="round" />
          </g>
          {/* eyes */}
          <g ref={eyesRef} style={{ transformOrigin: '150px 122px', transition: 'transform 70ms linear' }}>
            <ellipse cx="128" cy="122" rx="9" ry="7" fill="#fff" />
            <ellipse cx="172" cy="122" rx="9" ry="7" fill="#fff" />
            <g style={{ transform: `translateY(${gaze}px)`, transition: 'transform 400ms ease' }}>
              <circle cx="128" cy="122" r="5" fill="#3b2418" />
              <circle cx="172" cy="122" r="5" fill="#3b2418" />
              <circle cx="130" cy="120" r="1.6" fill="#fff" />
              <circle cx="174" cy="120" r="1.6" fill="#fff" />
            </g>
          </g>
          {/* nose */}
          <path d="M150 128 Q 146 146, 152 150" stroke="#a46f50" strokeWidth="2.5" fill="none" strokeLinecap="round" />
          {/* mouth: smile when closed, opening ellipse when talking */}
          <path ref={smileRef} d="M136 166 Q 150 175, 164 166" stroke="#8a3b3b" strokeWidth="3.5" fill="none" strokeLinecap="round" />
          <ellipse ref={mouthRef} cx="150" cy="168" rx="11" ry="0.6" fill="#6e2a2f" />
        </g>
        {state === 'thinking' && (
          <g aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <circle key={i} cx={128 + i * 22} cy={40} r="6" fill="#f472b6" className={REDUCED_MOTION ? '' : 'aria-dot'} style={{ animationDelay: `${i * 0.18}s` }} />
            ))}
          </g>
        )}
      </svg>
      <style>{`
        .aria-halo { animation: ariaHalo 1.6s ease-in-out infinite; }
        @keyframes ariaHalo { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.04); opacity: .6; } }
        .aria-dot { animation: ariaDot 1s ease-in-out infinite; }
        @keyframes ariaDot { 0%,100% { opacity: .25; transform: translateY(0); } 50% { opacity: 1; transform: translateY(-5px); } }
      `}</style>
    </div>
  );
}
