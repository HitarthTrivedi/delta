import React from 'react';
import ResumeSection from './ResumeSection';

export default function ResumePage() {
  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <header style={{ marginBottom: 28 }}>
          <p style={{ color: 'rgba(255,255,255,0.46)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
            Part 4 · ATS Resume Manager
          </p>
          <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.4rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0 }}>
            Your Resume Profile
          </h1>
          <p style={{ margin: '10px 0 0', color: 'rgba(255,255,255,0.5)', fontSize: 15 }}>
            Generate, optimize, and track bi-weekly resume recommendations based on your progress.
          </p>
        </header>

        <div style={{ background: '#050505', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: 22 }}>
          <ResumeSection />
        </div>
      </div>
    </main>
  );
}
