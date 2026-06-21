import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  ClipboardList, FileText, Map, BarChart3, Bell
} from 'lucide-react';

const navItems = [
  { label: 'Part 1 Input', path: '/intake', icon: ClipboardList },
  { label: 'Part 2 Roadmap', path: '/roadmap', icon: Map },
  { label: 'Part 3 Progress', path: '/progress-report', icon: BarChart3 },
  { label: 'Part 4 Resume', path: '/resume', icon: FileText },
];

export default function Navbar({ user }) {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/88 backdrop-blur-xl border-b border-white/10">
      <div className="max-w-[1180px] mx-auto px-6 flex items-center justify-between h-16 gap-5">
        <Link to="/" className="flex items-center gap-2 text-white font-bold text-base tracking-normal shrink-0">
          <span className="w-7 h-7 rounded-md bg-white text-black flex items-center justify-center">
            <FileText size={15} />
          </span>
          Delta
        </Link>

        <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
          {navItems.map(({ label, path, icon: Icon }) => {
            const isActive = location.pathname === path || (path === '/intake' && location.pathname === '/onboarding') || (path === '/roadmap' && location.pathname === '/weekly-plan');
            return (
              <Link
                key={path}
                to={path}
                className={`relative px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all duration-200 whitespace-nowrap ${
                  isActive
                    ? 'text-white bg-white/10 border border-white/20'
                    : 'text-white/45 hover:text-white/75 border border-transparent'
                }`}
              >
                <Icon size={12} />
                {label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <p className="text-xs font-semibold text-white/45">
              {user?.name || 'Guest'}
            </p>
            <p className="text-[11px] text-white/35">
              {user?.target_role || 'No Target Set'}
            </p>
          </div>
          <button className="relative p-2 rounded-lg bg-white/5 border border-white/10 text-white/45 hover:text-white transition-colors">
            <Bell size={14} />
          </button>
          <div className="w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white text-xs font-bold">
            {(user?.name || 'G')[0]}
          </div>
        </div>
      </div>
    </nav>
  );
}
