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
    { label: 'FAQ', href: '#faq' }
  ];

  return (
    <header
      className="header-nav"
      style={{
        boxShadow: isScrolled ? '0 4px 20px rgba(0, 0, 0, 0.3)' : 'none',
        background: isScrolled ? 'rgba(3, 7, 18, 0.85)' : 'transparent',
        backdropFilter: isScrolled ? 'blur(12px)' : 'none',
        borderBottom: isScrolled ? '1px solid rgba(255, 255, 255, 0.05)' : '1px solid transparent',
        transition: 'all 0.3s ease',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        height: '4.5rem'
      }}
    >
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 h-full flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => window.location.href = '/'}>
          <img
            src="https://customer-assets.emergentagent.com/job_growth-tracker-152/artifacts/9e027d2s_delta_logo.png"
            alt="Delta Logo"
            className="h-9 w-auto object-contain"
          />
          <span className="font-mono text-lg font-bold text-white tracking-wider uppercase">
            Delta
          </span>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="mono-text text-[11px] font-bold text-slate-300 hover:text-white uppercase tracking-widest transition-colors duration-200"
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-4">
          <button className="btn-secondary px-5 py-2 text-[10px] uppercase font-bold tracking-widest rounded-full border border-white/5 hover:border-white/10 transition-colors">
            Sign In
          </button>
          <button 
            className="btn-primary px-5 py-2 text-[10px] uppercase font-bold tracking-widest rounded-full transition-all" 
            onClick={() => window.location.href = '/onboarding'}
          >
            Get Started
          </button>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="p-2 rounded-lg bg-slate-900/80 border border-white/5 text-slate-400 hover:text-slate-200 md:hidden transition-all"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
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
              background: 'var(--bg-overlay)',
              backdropFilter: 'blur(16px)',
              borderBottom: '1px solid var(--border-light)',
              padding: '2rem 1.5rem',
              position: 'absolute',
              top: '4.5rem',
              left: 0,
              right: 0,
              zIndex: 49
            }}
          >
            <nav className="flex flex-col gap-5 mb-8">
              {navItems.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  className="mono-text text-xs font-bold text-slate-300 hover:text-white uppercase tracking-widest py-1"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {item.label}
                </a>
              ))}
            </nav>
            <div className="flex flex-col gap-3">
              <button className="btn-secondary w-full py-3 text-[10px] uppercase font-bold tracking-widest rounded-full">
                Sign In
              </button>
              <button 
                className="btn-primary w-full py-3 text-[10px] uppercase font-bold tracking-widest rounded-full" 
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  window.location.href = '/onboarding';
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