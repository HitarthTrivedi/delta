import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

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
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Pricing', href: '#pricing' },
    { label: 'FAQ', href: '#faq' }];


  return (
    <header
      className="header-nav"
      style={{
        boxShadow: isScrolled ? '0 2px 8px rgba(0, 0, 0, 0.05)' : 'none',
        transition: 'all 0.3s ease'
      }}>

      <div className="container !ml-[62px] !mr-[-40px]" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '100%' }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }} className="!mx-[40px]">
          <img
            src="https://customer-assets.emergentagent.com/job_growth-tracker-152/artifacts/9e027d2s_delta_logo.png"
            alt="Delta Logo"
            style={{
              height: '2.5rem',
              width: 'auto',
              objectFit: 'contain'
            }}
            className="!ml-[-50px] !mr-[-20px]" />

          <span style={{
            fontFamily: "'SF Mono', monospace",
            fontSize: '1.125rem',
            fontWeight: '600',
            color: 'var(--text-primary)',
            letterSpacing: '-0.01em'
          }} className="!text-2xl !ml-[-10px] !mr-[20px]">
            Delta
          </span>
        </div>

        {/* Desktop Navigation */}
        <nav style={{ display: 'none', gap: '2rem', alignItems: 'center' }} className="desktop-nav !text-left !ml-[1px]">
          {navItems.map((item) =>
            <a
              key={item.label}
              href={item.href}
              className="mono-text !ml-[-2px] !mr-[-2px]"
              style={{
                textDecoration: 'none',
                color: 'var(--text-primary)',
                fontSize: '0.875rem',
                fontWeight: '500',
                textTransform: 'uppercase',
                letterSpacing: '0.025em',
                transition: 'opacity 0.2s ease'
              }}
              onMouseEnter={(e) => e.target.style.opacity = '0.6'}
              onMouseLeave={(e) => e.target.style.opacity = '1'}>

              {item.label}
            </a>
          )}
        </nav>

        {/* Desktop CTA */}
        <div style={{ display: 'none', gap: '1rem', alignItems: 'center' }} className="desktop-nav !mr-[-60px]">
          <button className="btn-secondary !ml-[50px]">
            Sign In
          </button>
          <button className="btn-primary !ml-[-10px]" onClick={() => window.location.href = '/onboarding'}>
            Get Started
          </button>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="btn-nav mobile-menu-btn !mx-[1px]"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle menu">

          {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen &&
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              background: 'var(--bg-overlay)',
              backdropFilter: 'blur(8px)',
              borderTop: '1px solid var(--border-light)',
              padding: '1.5rem'
            }}>

            <nav style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
              {navItems.map((item) =>
                <a
                  key={item.label}
                  href={item.href}
                  className="mono-text"
                  style={{
                    textDecoration: 'none',
                    color: 'var(--text-primary)',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    textTransform: 'uppercase',
                    letterSpacing: '0.025em',
                    padding: '0.5rem 0'
                  }}
                  onClick={() => setIsMobileMenuOpen(false)}>

                  {item.label}
                </a>
              )}
            </nav>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <button className="btn-secondary" style={{ width: '100%' }}>
                Sign In
              </button>
              <button className="btn-primary" style={{ width: '100%' }} onClick={() => window.location.href = '/onboarding'}>
                Get Started
              </button>
            </div>
          </motion.div>
        }
      </AnimatePresence>

      <style>{`
        @media (min-width: 768px) {
          .desktop-nav {
            display: flex !important;
          }
          .mobile-menu-btn {
            display: none !important;
          }
        }
      `}</style>
    </header>);

};

export default Header;