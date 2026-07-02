import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
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
    { label: 'Workflow', href: '#how-it-works' },
    { label: 'About', href: '/about' },
    { label: 'Partners', href: '/partners' },
    { label: 'Investors', href: '/investors' },
    { label: 'Contact', href: '/contact' },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-bone/92 backdrop-blur-md border-b border-rule'
          : 'bg-transparent border-b border-transparent'
      }`}
    >
      <div className="max-w-[1140px] mx-auto px-6 h-[72px] flex items-center justify-between">
        {/* Logo */}
        <div
          className="flex items-baseline gap-2.5 cursor-pointer"
          onClick={() => window.location.href = '/'}
        >
          <span className="font-display text-[1.35rem] font-semibold text-ink tracking-tight">
            Delta
          </span>
          <span className="hidden sm:inline font-mono text-[10px] uppercase tracking-[0.22em] text-ink-soft">
            by Alpha.Kore
          </span>
        </div>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-8">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-soft hover:text-oxblood transition-colors no-underline"
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTA — quiet mono links, memorandum style */}
        <div className="hidden md:flex items-center gap-7">
          <button
            onClick={() => window.location.href = '/progress-report'}
            className="bg-transparent border-none font-mono text-[10px] uppercase tracking-[0.2em] text-ink-soft hover:text-oxblood cursor-pointer p-0 transition-colors"
          >
            Progress
          </button>
          <button
            onClick={() => window.location.href = '/intake'}
            id="header-get-started"
            className="bg-transparent border-none font-mono text-[10px] uppercase tracking-[0.2em] text-oxblood hover:text-ink cursor-pointer p-0 transition-colors"
          >
            Get Started &#8599;
          </button>
        </div>

        {/* Mobile burger */}
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="md:hidden bg-transparent border border-rule text-ink p-2 cursor-pointer"
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
            className="absolute top-[72px] left-0 right-0 z-40 bg-bone border-b border-rule p-6 overflow-hidden"
          >
            <nav className="flex flex-col gap-4 mb-5">
              {navItems.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  className="font-mono text-xs uppercase tracking-[0.2em] text-ink-soft no-underline"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {item.label}
                </a>
              ))}
            </nav>
            <div className="flex flex-col gap-2.5">
              <button
                onClick={() => { setIsMobileMenuOpen(false); window.location.href = '/login'; }}
                className="bg-transparent border border-ink text-ink font-mono text-xs uppercase tracking-[0.16em] p-2.5 cursor-pointer w-full"
              >
                Login
              </button>
              <button
                onClick={() => { setIsMobileMenuOpen(false); window.location.href = '/intake'; }}
                className="bg-oxblood text-bone border border-oxblood font-mono text-xs uppercase tracking-[0.16em] p-2.5 cursor-pointer w-full"
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
