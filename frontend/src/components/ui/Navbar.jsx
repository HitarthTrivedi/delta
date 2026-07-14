import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ClipboardList, FileText, Map, BarChart3, Trophy, Briefcase, LogOut, Menu, X } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import ThemeToggle from './ThemeToggle';

const navItems = [
  { label: 'Intake', path: '/intake', icon: ClipboardList },
  { label: 'Roadmap', path: '/roadmap', icon: Map },
  { label: 'Progress', path: '/progress-report', icon: BarChart3 },
  { label: 'Opportunities', path: '/opportunities', icon: Briefcase },
  { label: 'Trophies', path: '/achievements', icon: Trophy },
  { label: 'Resume', path: '/resume', icon: FileText },
];

export default function Navbar({ user }) {
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  const isActive = (path) =>
    location.pathname === path ||
    (path === '/intake' && location.pathname === '/onboarding') ||
    (path === '/roadmap' && location.pathname === '/weekly-plan');

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 bg-bone/90 backdrop-blur-xl border-b border-rule">
        <div className="max-w-[1180px] mx-auto px-4 sm:px-6 flex items-center justify-between h-14 sm:h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-ink shrink-0 no-underline">
            <span className="w-7 h-7 bg-paper border border-rule overflow-hidden flex items-center justify-center">
              <img src="/delta-bg.jpeg" alt="Delta" className="w-full h-full object-cover" />
            </span>
            <span className="hidden xs:inline font-display text-lg font-semibold">Delta</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map(({ label, path, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={`relative px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] flex items-center gap-1.5 transition-all duration-200 whitespace-nowrap border-b-2 no-underline ${
                  isActive(path)
                    ? 'text-oxblood border-oxblood'
                    : 'text-ink-soft hover:text-ink border-transparent'
                }`}
              >
                <Icon size={12} />
                {label}
              </Link>
            ))}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            {/* User info — hidden on very small screens */}
            <div className="hidden sm:block text-right">
              <p className="text-xs font-semibold text-ink truncate max-w-[120px]">
                {user?.name || 'Guest'}
              </p>
              <p className="font-mono text-[10px] text-ink-soft truncate max-w-[120px]">
                {user?.target_role || 'No target set'}
              </p>
            </div>

            {/* Avatar */}
            <div className="w-8 h-8 rounded-full bg-accent-surface border border-rule flex items-center justify-center text-ink font-display text-sm font-semibold shrink-0">
              {(user?.name || 'G')[0].toUpperCase()}
            </div>

            {/* Theme toggle */}
            <ThemeToggle className="w-11 h-11" />

            {/* Logout — desktop only */}
            <button
              onClick={handleLogout}
              title="Sign Out"
              aria-label="Sign Out"
              className="hidden sm:flex items-center justify-center w-11 h-11 bg-transparent border border-rule text-ink-soft hover:text-oxblood hover:border-oxblood transition-all"
            >
              <LogOut size={14} />
            </button>

            {/* Hamburger — mobile only */}
            <button
              onClick={() => setMobileOpen((o) => !o)}
              className="md:hidden flex items-center justify-center w-11 h-11 bg-transparent border border-rule text-ink-soft"
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        >
          <div className="absolute inset-0 bg-ink/40" />
          <div
            className="absolute top-14 left-0 right-0 bg-bone border-b border-rule"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 flex flex-col gap-1">
              {navItems.map(({ label, path, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3.5 font-mono text-xs uppercase tracking-[0.12em] transition-all no-underline ${
                    isActive(path)
                      ? 'text-oxblood bg-accent-surface'
                      : 'text-ink-soft hover:text-ink hover:bg-accent-surface'
                  }`}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              ))}
              <div className="border-t border-rule mt-2 pt-3 flex items-center justify-between px-4 pb-2">
                <div>
                  <p className="text-sm font-semibold text-ink">{user?.name || 'Guest'}</p>
                  <p className="font-mono text-xs text-ink-soft">{user?.target_role || 'No target set'}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-3 py-2 border border-oxblood text-oxblood font-mono text-xs uppercase tracking-[0.12em] bg-transparent"
                >
                  <LogOut size={14} /> Sign Out
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
