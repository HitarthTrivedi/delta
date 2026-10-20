import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { sandboxInterviewAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';
import InterviewReport from '../components/interview/InterviewReport';

/** A saved mock-interview report: /practice/interview/report/:sessionId */
export default function InterviewReportPage() {
  const { sessionId } = useParams();
  const userId = useAuthStore((s) => s.userId);
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    sandboxInterviewAPI.getSession(userId, sessionId).then(setData).catch(() => setError(true));
  }, [userId, sessionId]);

  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 860, margin: '0 auto' }}>
        <Link to="/practice" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'rgba(255,255,255,0.55)', fontSize: 13, textDecoration: 'none', marginBottom: 18 }}>
          <ArrowLeft size={14} /> Test Center
        </Link>
        {error ? (
          <p style={{ color: 'rgba(255,255,255,0.6)' }}>This interview couldn't be found.</p>
        ) : !data ? (
          <Loader2 size={22} style={{ animation: 'spin 1s linear infinite' }} />
        ) : !data.feedback ? (
          <p style={{ color: 'rgba(255,255,255,0.6)' }}>
            This interview wasn't finished, so there's no report. <Link to="/practice/interview" style={{ color: '#f472b6' }}>Start a new one</Link>.
          </p>
        ) : (
          <>
            <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
              {data.title} · {data.completed_at ? new Date(`${data.completed_at}Z`).toLocaleString() : ''}
            </p>
            <h1 style={{ fontSize: 'clamp(1.8rem, 4vw, 2.6rem)', margin: '0 0 20px' }}>Interview report</h1>
            <InterviewReport feedback={data.feedback} transcript={data.transcript} settings={data.settings} />
          </>
        )}
      </div>
      <style>{'@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }'}</style>
    </main>
  );
}
