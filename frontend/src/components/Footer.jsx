import React from 'react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer style={{
      background: '#000',
      color: 'rgba(255,255,255,0.56)',
      padding: '2.5rem 1.5rem',
      borderTop: '1px solid rgba(255,255,255,0.1)',
    }}>
      <div style={{
        maxWidth: 1120,
        margin: '0 auto',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 26,
            height: 26,
            background: '#fff',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <span style={{ color: '#000', fontWeight: 900, fontSize: 13, fontFamily: 'monospace' }}>Δ</span>
          </div>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>Delta</span>
        </div>

        <p style={{ margin: 0, fontSize: 13 }}>
          © {currentYear} Delta. Week-by-week career planning for students.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
