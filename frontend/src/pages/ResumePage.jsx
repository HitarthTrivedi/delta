import React from 'react';
import ResumeSection from './ResumeSection';

export default function ResumePage() {
  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <header style={{ marginBottom: 28 }}>
          <p style={{ color: 'var(--ink-soft)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
            Part 4 · ATS Resume Manager
          </p>
          <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontWeight: 500, color: 'var(--oxblood)', fontSize: 'clamp(2rem, 5vw, 3.4rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0 }}>
            Your Resume Profile
          </h1>
          <p style={{ margin: '10px 0 0', color: 'var(--ink-soft)', fontSize: 15 }}>
            Generate, optimize, and track bi-weekly resume recommendations based on your progress.
          </p>
        </header>

        <div style={{ background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 8, padding: 22 }}>
          <ResumeSection />
        </div>
      </div>
    </main>
  );
}
