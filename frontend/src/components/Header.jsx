import React, { useState, useEffect } from 'react';
import { Menu, X, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Header = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = [
    { label: 'Agents', href: '#features' },
    { label: 'Workflow', href: '#how-it-works' },
  ];

  const headerStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 50,
    height: '3.75rem',
    transition: 'all 0.3s ease',
    background: isScrolled ? 'rgba(0,0,0,0.85)' : 'transparent',
    backdropFilter: isScrolled ? 'blur(14px)' : 'none',
    borderBottom: isScrolled ? '1px solid rgba(255,255,255,0.08)' : '1px solid transparent',
  };

  return (
    <header style={headerStyle}>
      <div
        style={{
          maxWidth: 1120,
          margin: '0 auto',
          padding: '0 1.5rem',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Logo */}
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
          onClick={() => window.location.href = '/'}
        >
          <div
            style={{
              width: 28,
              height: 28,
              background: '#fff',
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ color: '#000', fontWeight: 900, fontSize: 14, fontFamily: 'monospace' }}>Δ</span>
          </div>
          <span
            style={{
              color: '#fff',
              fontWeight: 700,
              fontSize: '1rem',
              letterSpacing: 0,
              fontFamily: "'Inter', sans-serif",
            }}
          >
            Delta
          </span>
        </div>

        {/* Desktop Nav */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 32 }} className="hidden md:flex">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              style={{
                color: 'rgba(255,255,255,0.6)',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: 450,
                transition: 'color 0.2s',
                fontFamily: "'Inter', sans-serif",
              }}
              onMouseEnter={e => e.target.style.color = '#fff'}
              onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.6)'}
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }} className="hidden md:flex">
          <button
            onClick={() => window.location.href = '/progress-report'}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'rgba(255,255,255,0.6)',
              fontSize: '0.875rem',
              fontWeight: 450,
              cursor: 'pointer',
              padding: '6px 4px',
              transition: 'color 0.2s',
              fontFamily: "'Inter', sans-serif",
            }}
            onMouseEnter={e => e.target.style.color = '#fff'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.6)'}
          >
            Progress
          </button>
          <button
            onClick={() => window.location.href = '/intake'}
            id="header-get-started"
            style={{
              background: '#fff',
              color: '#000',
              border: 'none',
              borderRadius: 999,
              padding: '7px 18px',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'background 0.2s',
              fontFamily: "'Inter', sans-serif",
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#e5e5e5'}
            onMouseLeave={e => e.currentTarget.style.background = '#fff'}
          >
            Get Started <ArrowRight size={13} />
          </button>
        </div>

        {/* Mobile burger */}
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          style={{
            background: 'rgba(255,255,255,0.07)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            color: '#fff',
            padding: 8,
            cursor: 'pointer',
            display: 'none',
          }}
          className="md:hidden"
          aria-label="Toggle menu"
        >
          {isMobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              background: 'rgba(0,0,0,0.95)',
              backdropFilter: 'blur(16px)',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              padding: '1.5rem',
              position: 'absolute',
              top: '3.75rem',
              left: 0,
              right: 0,
              zIndex: 49,
            }}
          >
            <nav style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 20 }}>
              {navItems.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  style={{
                    color: 'rgba(255,255,255,0.7)',
                    textDecoration: 'none',
                    fontSize: '0.95rem',
                    fontWeight: 500,
                  }}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {item.label}
                </a>
              ))}
            </nav>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: 8,
                  color: 'rgba(255,255,255,0.7)',
                  padding: '10px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  width: '100%',
                }}
              >
                Login
              </button>
              <button
                onClick={() => { setIsMobileMenuOpen(false); window.location.href = '/intake'; }}
                style={{
                  background: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  color: '#000',
                  padding: '10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  width: '100%',
                }}
              >
                Get Started
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

export default Header;
