import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Code2, Briefcase, ArrowRight, Loader2 } from 'lucide-react';
import { sandboxCodingAPI, sandboxInterviewAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: '#050505',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
};

export default function PracticeHub() {
  const userId = useAuthStore((state) => state.userId);
  const navigate = useNavigate();
  const [stats, setStats] = useState({ coding: null, interview: null });

  useEffect(() => {
    if (!userId) return;
    sandboxCodingAPI.getSessions(userId)
      .then((data) => {
        const sessions = data?.sessions || [];
        setStats((s) => ({ ...s, coding: sessions.filter((x) => x.status === 'completed').length }));
      })
      .catch(() => {});
    sandboxInterviewAPI.getSessions(userId)
      .then((data) => {
        const sessions = data?.sessions || [];
        setStats((s) => ({ ...s, interview: sessions.filter((x) => x.status === 'completed').length }));
      })
      .catch(() => {});
  }, [userId]);

  const cards = [
    {
      key: 'coding',
      icon: Code2,
      color: '#60a5fa',
      title: 'Coding Sandbox',
      description: 'Pick a problem, write real code, run it, and submit for automatic pass/fail grading.',
      stat: stats.coding === null ? null : `${stats.coding} problem${stats.coding === 1 ? '' : 's'} solved`,
      path: '/practice/coding',
    },
    {
      key: 'interview',
      icon: Briefcase,
      color: '#f472b6',
      title: 'Mock Interview',
      description: 'An AI interviewer asks questions tailored to your profile — answer by voice or text, get feedback.',
      stat: stats.interview === null ? null : `${stats.interview} interview${stats.interview === 1 ? '' : 's'} completed`,
      path: '/practice/interview',
    },
  ];

  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <header style={{ marginBottom: 32 }}>
          <p style={{ color: 'rgba(255,255,255,0.46)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
            Practice
          </p>
          <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.2rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0, maxWidth: 640 }}>
            Rehearse before it counts.
          </h1>
          <p style={{ margin: '14px 0 0', color: 'rgba(255,255,255,0.5)', fontSize: 15, lineHeight: 1.55, maxWidth: 600 }}>
            Two ways to get sharper: solve real coding problems with automatic grading, or run a mock interview with an AI interviewer.
          </p>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <button
                key={card.key}
                onClick={() => navigate(card.path)}
                style={{
                  ...panelStyle, padding: 26, textAlign: 'left', cursor: 'pointer', color: '#fff',
                  display: 'flex', flexDirection: 'column', gap: 14,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
              >
                <div style={{
                  width: 44, height: 44, borderRadius: 10,
                  background: `${card.color}1a`, border: `1px solid ${card.color}44`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon size={20} style={{ color: card.color }} />
                </div>
                <div>
                  <h2 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 700 }}>{card.title}</h2>
                  <p style={{ margin: 0, color: 'rgba(255,255,255,0.5)', fontSize: 13.5, lineHeight: 1.55 }}>{card.description}</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'auto', paddingTop: 4 }}>
                  <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12.5, minHeight: 16 }}>
                    {card.stat === null ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : card.stat}
                  </span>
                  <ArrowRight size={16} style={{ color: 'rgba(255,255,255,0.5)' }} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </main>
  );
}
