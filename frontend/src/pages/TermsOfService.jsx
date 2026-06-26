import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const section = { marginBottom: 36 };
const h2 = { color: '#fff', fontSize: 18, fontWeight: 700, marginBottom: 10, marginTop: 0 };
const p = { color: 'rgba(255,255,255,0.6)', fontSize: 15, lineHeight: 1.8, margin: '0 0 12px' };
const ul = { color: 'rgba(255,255,255,0.6)', fontSize: 15, lineHeight: 1.8, paddingLeft: 22, margin: '0 0 12px' };

export default function TermsOfService() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', background: '#000', fontFamily: "'Inter', sans-serif", color: '#fff' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '6rem 1.5rem 4rem' }}>

        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none',
            border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer',
            fontSize: 14, marginBottom: 40, padding: 0,
          }}
        >
          <ArrowLeft size={15} /> Back
        </button>

        <h1 style={{ fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 800, marginBottom: 8 }}>Terms of Service</h1>
        <p style={{ ...p, marginBottom: 40 }}>Last updated: June 26, 2026</p>

        <div style={section}>
          <h2 style={h2}>What Delta is</h2>
          <p style={p}>Delta is an AI-powered career planning tool designed to help students build structured, personalised roadmaps toward their professional goals. Delta generates plans, suggests resources, and tracks progress based on information you provide.</p>
          <p style={p}><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Delta is not a professional career counsellor, recruiter, or placement service.</strong> Outputs from Delta's AI agents are suggestions, not guarantees. Career outcomes depend on your own effort, market conditions, and many factors outside our control.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Your account</h2>
          <ul style={ul}>
            <li>You must be at least 13 years old to use Delta.</li>
            <li>You are responsible for keeping your login credentials secure.</li>
            <li>You are responsible for all activity that occurs under your account.</li>
            <li>You may only create one account per person.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>Acceptable use</h2>
          <p style={p}>You agree not to:</p>
          <ul style={ul}>
            <li>Use Delta to generate content that is harmful, abusive, or illegal.</li>
            <li>Attempt to reverse-engineer, scrape, or abuse the platform's APIs.</li>
            <li>Share your account with others or create accounts on behalf of other people without their knowledge.</li>
            <li>Upload resumes or documents that belong to someone else without their permission.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>Your content</h2>
          <p style={p}>You retain ownership of the information you provide to Delta — your profile, goals, and conversations. By using Delta, you grant us a limited licence to process that content in order to provide the service.</p>
          <p style={p}>You are responsible for ensuring that any resume or document you upload does not infringe on any third party's intellectual property rights.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>AI-generated content</h2>
          <p style={p}>Delta uses large language models (currently Google Gemini) to generate responses and roadmaps. AI-generated content can be inaccurate, outdated, or incomplete. Always verify important information — especially deadlines, application requirements, and salary data — from authoritative sources.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Service availability</h2>
          <p style={p}>We aim to keep Delta available at all times, but we do not guarantee uninterrupted access. The service may be temporarily unavailable due to maintenance, infrastructure issues, or events outside our control.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Changes to these terms</h2>
          <p style={p}>We may update these terms from time to time. If we make significant changes, we will notify you via the email address on your account. Continued use of Delta after changes take effect constitutes your acceptance of the updated terms.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Governing law</h2>
          <p style={p}>These terms are governed by the laws of India. Any disputes shall be resolved in the courts of Ahmedabad, Gujarat.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Contact</h2>
          <p style={p}>Questions about these terms? Email us at <a href="mailto:hitartht318@gmail.com" style={{ color: '#fff' }}>hitartht318@gmail.com</a>.</p>
        </div>

      </div>
    </div>
  );
}
