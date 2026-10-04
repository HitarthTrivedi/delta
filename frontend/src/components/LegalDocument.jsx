import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft, Loader2 } from 'lucide-react';

const serif = "'Cormorant Garamond', Georgia, serif";
const p = { color: 'var(--ink-soft)', fontSize: 15, lineHeight: 1.8, margin: '0 0 12px' };
const list = { color: 'var(--ink-soft)', fontSize: 15, lineHeight: 1.8, paddingLeft: 22, margin: '0 0 12px' };
const cell = { border: '1px solid var(--rule)', padding: '8px 10px', textAlign: 'left', verticalAlign: 'top' };

// Map markdown elements onto the editorial legal-page styles.
const components = {
  h1: ({ children }) => (
    <h1 style={{ fontFamily: serif, color: 'var(--oxblood)', fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 600, marginBottom: 8 }}>{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 style={{ color: 'var(--oxblood)', fontFamily: serif, fontSize: 22, fontWeight: 600, marginBottom: 10, marginTop: 0 }}>{children}</h2>
  ),
  h3: ({ children }) => <h3 style={{ color: 'var(--ink)', fontSize: 15, fontWeight: 600, marginBottom: 6, marginTop: 18 }}>{children}</h3>,
  p: ({ children }) => <p style={p}>{children}</p>,
  ul: ({ children }) => <ul style={list}>{children}</ul>,
  ol: ({ children }) => <ol style={list}>{children}</ol>,
  strong: ({ children }) => <strong style={{ color: 'var(--ink)' }}>{children}</strong>,
  a: ({ href, children }) => <a href={href} style={{ color: 'var(--oxblood)' }}>{children}</a>,
  hr: () => <hr style={{ border: 0, borderTop: '1px solid var(--rule)', margin: '28px 0' }} />,
  table: ({ children }) => (
    <div style={{ overflowX: 'auto', margin: '0 0 16px' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6 }}>{children}</table>
    </div>
  ),
  th: ({ children }) => <th style={{ ...cell, color: 'var(--ink)', background: 'var(--accent-surface)' }}>{children}</th>,
  td: ({ children }) => <td style={cell}>{children}</td>,
};

/**
 * Renders a legal document from /public/legal/*.md. Those markdown files are
 * the single source of truth for the published Privacy Policy and Terms.
 */
export default function LegalDocument({ src }) {
  const navigate = useNavigate();
  const [text, setText] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(src)
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(r.statusText))))
      .then(setText)
      .catch(() => setFailed(true));
  }, [src]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bone)', fontFamily: "'Manrope', sans-serif", color: 'var(--ink)' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '6rem 1.5rem 4rem' }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none',
            border: 'none', color: 'var(--ink-soft)', cursor: 'pointer',
            fontSize: 14, marginBottom: 40, padding: 0,
          }}
        >
          <ArrowLeft size={15} /> Back
        </button>

        {failed ? (
          <p style={p}>This document couldn't be loaded. Please refresh, or email hitartht318@gmail.com for a copy.</p>
        ) : text === null ? (
          <Loader2 size={22} style={{ color: 'var(--ink-soft)', animation: 'spin 1s linear infinite' }} />
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{text}</ReactMarkdown>
        )}
      </div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
