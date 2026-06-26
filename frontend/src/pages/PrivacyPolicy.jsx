import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const section = { marginBottom: 36 };
const h2 = { color: '#fff', fontSize: 18, fontWeight: 700, marginBottom: 10, marginTop: 0 };
const p = { color: 'rgba(255,255,255,0.6)', fontSize: 15, lineHeight: 1.8, margin: '0 0 12px' };
const ul = { color: 'rgba(255,255,255,0.6)', fontSize: 15, lineHeight: 1.8, paddingLeft: 22, margin: '0 0 12px' };

export default function PrivacyPolicy() {
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

        <h1 style={{ fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 800, marginBottom: 8 }}>Privacy Policy</h1>
        <p style={{ ...p, marginBottom: 40 }}>Last updated: June 26, 2026</p>

        <div style={section}>
          <h2 style={h2}>What we collect</h2>
          <p style={p}>When you use Delta, we collect the following information:</p>
          <ul style={ul}>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Account information</strong> — your name, email address, and authentication credentials managed by Supabase.</li>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Career profile</strong> — your background, skills, goals, constraints, and preferences that you share during onboarding and throughout your use of the app.</li>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Resume content</strong> — text extracted from resumes you upload. We do not store the original file after processing.</li>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Conversation history</strong> — messages exchanged with Agent 1 (onboarding) and Agent 2 (weekly planning), stored to provide continuity across sessions.</li>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Usage data</strong> — task completions, weekly progress, and interaction patterns used to improve your roadmap.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>How we use your data</h2>
          <ul style={ul}>
            <li>To generate and refine your personalised career roadmap.</li>
            <li>To power the AI agents that answer your questions and adapt your weekly plan.</li>
            <li>To track your progress and surface relevant opportunities over time.</li>
            <li>To improve Delta's models and features (only in aggregate and anonymised form).</li>
          </ul>
          <p style={p}>We do not sell your personal data. We do not use your data to train third-party AI models.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Third-party services</h2>
          <p style={p}>Delta relies on the following third-party services to operate:</p>
          <ul style={ul}>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Supabase</strong> — authentication and database hosting. Your data is stored in Supabase's PostgreSQL infrastructure.</li>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Google Gemini</strong> — AI model provider. Conversation content is sent to Gemini to generate responses. Google's API data usage policy applies.</li>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Vercel</strong> — frontend hosting.</li>
            <li><strong style={{ color: 'rgba(255,255,255,0.85)' }}>Render</strong> — backend API hosting.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>Data retention</h2>
          <p style={p}>Your profile and conversation data is retained for as long as your account is active. You can request deletion of your account and all associated data at any time by contacting us.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Your rights</h2>
          <ul style={ul}>
            <li>Access the data we hold about you.</li>
            <li>Correct inaccurate data in your profile at any time via the Intake page.</li>
            <li>Delete your account and data by contacting us at the address below.</li>
            <li>Export your profile data on request.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>Cookies</h2>
          <p style={p}>Delta uses only functional cookies and local storage to maintain your login session. We do not use advertising or tracking cookies.</p>
        </div>

        <div style={section}>
          <h2 style={h2}>Contact</h2>
          <p style={p}>For any privacy-related questions or deletion requests, email us at <a href="mailto:hitartht318@gmail.com" style={{ color: '#fff' }}>hitartht318@gmail.com</a>.</p>
        </div>

      </div>
    </div>
  );
}
