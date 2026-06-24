import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Play } from 'lucide-react';

const BAR_HEIGHTS = [20, 40, 65, 82, 95, 82, 65, 40, 20, 40, 65, 82, 95, 82, 65, 40, 20];

const Hero = () => {
  return (
    <section
      style={{
        background: '#000',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        padding: '0 1.5rem',
      }}
    >
      {/* Vertical bars background — centered, fading */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
          gap: '14px',
          padding: '0 10%',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      >
        {BAR_HEIGHTS.map((h, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              maxWidth: 36,
              height: `${h}%`,
              background: `linear-gradient(to top, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0.06) 100%)`,
              borderRadius: '6px 6px 0 0',
              opacity: 0.55,
              maskImage: 'linear-gradient(to top, transparent 0%, black 40%, black 80%, transparent 100%)',
              WebkitMaskImage: 'linear-gradient(to top, transparent 0%, black 40%, black 80%, transparent 100%)',
            }}
          />
        ))}
        {/* Bottom fade */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: '35%',
            background: 'linear-gradient(to top, #000 0%, transparent 100%)',
          }}
        />
      </div>

      {/* Main Content */}
      <div
        style={{
          position: 'relative',
          zIndex: 10,
          textAlign: 'center',
          maxWidth: 680,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '0',
        }}
      >
        {/* Hero Title */}
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.08 }}
          style={{
            fontSize: 'clamp(2.6rem, 7vw, 4.25rem)',
            fontWeight: 700,
            color: '#fff',
            lineHeight: 1.1,
            letterSpacing: 0,
            fontFamily: "'Inter', sans-serif",
            marginBottom: 20,
          }}
        >
          F#CK COLLEGE!<br />Delta is here
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.16 }}
          style={{
            color: 'rgba(255,255,255,0.45)',
            fontSize: '1.05rem',
            lineHeight: 1.65,
            maxWidth: 480,
            marginBottom: 36,
          }}
        >
          One intake conversation, one adaptive weekly planner, and one progress
          report page that keeps your roadmap honest for years.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.24 }}
          style={{ display: 'flex', alignItems: 'center', gap: 12 }}
        >
          <button
            onClick={() => window.location.href = '/intake'}
            style={{
              background: '#fff',
              color: '#000',
              border: 'none',
              borderRadius: 999,
              padding: '11px 26px',
              fontSize: '0.92rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'background 0.2s, transform 0.15s',
              letterSpacing: '0.01em',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#e5e5e5'; e.currentTarget.style.transform = 'scale(1.03)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.transform = 'scale(1)'; }}
            id="hero-get-started"
          >
            Get Started
            <ArrowRight size={14} />
          </button>

          <button
            onClick={() => window.location.href = '/roadmap'}
            style={{
              background: 'transparent',
              color: 'rgba(255,255,255,0.65)',
              border: '1px solid rgba(255,255,255,0.18)',
              borderRadius: 999,
              padding: '10px 22px',
              fontSize: '0.92rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.4)'; e.currentTarget.style.color = '#fff'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.18)'; e.currentTarget.style.color = 'rgba(255,255,255,0.65)'; }}
            id="hero-watch-demo"
          >
            <Play size={12} style={{ fill: 'currentColor' }} />
            View Roadmap
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default Hero;
