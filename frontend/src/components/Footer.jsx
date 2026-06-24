import React from 'react';

const linkStyle = {
  color: 'rgba(255,255,255,0.5)',
  textDecoration: 'none',
  fontSize: 13,
  lineHeight: 2.1,
  transition: 'color 0.2s',
  display: 'block',
};

const colTitleStyle = {
  color: 'rgba(255,255,255,0.8)',
  fontSize: 13,
  fontWeight: 650,
  marginBottom: 10,
  letterSpacing: '0.02em',
};

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer style={{
      background: '#000',
      color: 'rgba(255,255,255,0.56)',
      padding: '3.5rem 1.5rem 2rem',
      borderTop: '1px solid rgba(255,255,255,0.1)',
    }}>
      <div style={{
        maxWidth: 1120,
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '2.5rem',
        marginBottom: '2.5rem',
      }}>
        {/* Brand column */}
        <div style={{ minWidth: 180 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{
              width: 26,
              height: 26,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
            }}>
              <img
                src="/delta-bg.jpeg"
                alt="Delta logo"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
            <span style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>Delta</span>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.42)', fontSize: 13, lineHeight: 1.6, margin: 0, maxWidth: 220 }}>
            AI-powered career operating system for students.
          </p>
        </div>

        {/* Product */}
        <div>
          <p style={colTitleStyle}>Product</p>
          <a href="#features" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Features</a>
          <a href="#how-it-works" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >How It Works</a>
          <a href="/intake" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Get Started</a>
          <a href="/#feedback" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Feedback</a>
        </div>

        {/* Company */}
        <div>
          <p style={colTitleStyle}>Company</p>
          <a href="/about" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >About</a>
          <a href="/careers" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Careers</a>
          <a href="/contact" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Contact</a>
          <a href="/partners" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Partners</a>
          <a href="/investors" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Investors</a>
        </div>

        {/* Legal */}
        <div>
          <p style={colTitleStyle}>Legal</p>
          <a href="#" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Privacy Policy</a>
          <a href="#" style={linkStyle}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
          >Terms of Service</a>
        </div>
      </div>

      {/* Bottom bar */}
      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.08)',
        paddingTop: 20,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
          &copy; {currentYear} Delta. All rights reserved.
        </p>
        <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.28)' }}>
          Made with purpose for students everywhere.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
