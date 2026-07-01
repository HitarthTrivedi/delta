import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ClipboardList, FileText, Map, BarChart3, Trophy, Briefcase, LogOut, Menu, X } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

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
      <nav className="fixed top-0 left-0 right-0 z-50 bg-black/90 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-[1180px] mx-auto px-4 sm:px-6 flex items-center justify-between h-14 sm:h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-white font-bold text-sm tracking-normal shrink-0">
            <span className="w-7 h-7 rounded-md bg-white/5 border border-white/15 overflow-hidden flex items-center justify-center">
              <img src="/delta-bg.jpeg" alt="Delta" className="w-full h-full object-cover" />
            </span>
            <span className="hidden xs:inline">Delta</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map(({ label, path, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={`relative px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all duration-200 whitespace-nowrap ${
                  isActive(path)
                    ? 'text-white bg-white/10 border border-white/20'
                    : 'text-white/45 hover:text-white/75 border border-transparent'
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
              <p className="text-xs font-semibold text-white/50 truncate max-w-[120px]">
                {user?.name || 'Guest'}
              </p>
              <p className="text-[10px] text-white/30 truncate max-w-[120px]">
                {user?.target_role || 'No target set'}
              </p>
            </div>

            {/* Avatar */}
            <div className="w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {(user?.name || 'G')[0].toUpperCase()}
            </div>

            {/* Logout — desktop only */}
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="hidden sm:flex p-2 rounded-lg bg-white/5 border border-white/10 text-white/45 hover:text-red-400 hover:bg-red-500/10 hover:border-red-500/20 transition-all"
            >
              <LogOut size={14} />
            </button>

            {/* Hamburger — mobile only */}
            <button
              onClick={() => setMobileOpen((o) => !o)}
              className="md:hidden p-2 rounded-lg bg-white/5 border border-white/10 text-white/60"
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
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="absolute top-14 left-0 right-0 bg-black/95 border-b border-white/10 backdrop-blur-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 flex flex-col gap-1">
              {navItems.map(({ label, path, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all ${
                    isActive(path)
                      ? 'text-white bg-white/10 border border-white/20'
                      : 'text-white/60 hover:text-white hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              ))}
              <div className="border-t border-white/10 mt-2 pt-3 flex items-center justify-between px-4 pb-2">
                <div>
                  <p className="text-sm font-semibold text-white">{user?.name || 'Guest'}</p>
                  <p className="text-xs text-white/40">{user?.target_role || 'No target set'}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold"
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
