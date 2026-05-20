import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Zap, LayoutDashboard, BookOpen, FileText, TrendingUp,
  CalendarDays, FolderOpen, User, Bell
} from 'lucide-react';

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Career AI', path: '/chat', icon: Zap },
  { label: 'Ledger', path: '/ledger', icon: BookOpen },
  { label: 'Briefs', path: '/briefs', icon: FileText },
  { label: 'Pulse', path: '/pulse', icon: TrendingUp },
  { label: 'Calendar', path: '/calendar', icon: CalendarDays },
  { label: 'Dossier', path: '/portfolio', icon: FolderOpen },
  { label: 'Profile', path: '/profile', icon: User },
];

export default function Navbar({ user }) {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-2 text-white font-black italic text-xl uppercase tracking-tighter">
          <Zap className="text-primary-400 fill-primary-400/30" size={20} />
          DELTA
        </Link>

        <div className="flex items-center gap-1">
          {navItems.map(({ label, path, icon: Icon }) => {
            const isActive = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                className={`relative px-3 py-2 rounded-lg text-[10px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5 transition-all duration-300 ${
                  isActive
                    ? 'text-white bg-primary-500/10 border border-primary-500/20'
                    : 'text-slate-500 hover:text-slate-300 border border-transparent'
                }`}
              >
                <Icon size={12} />
                {label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500">
              {user?.name || 'Guest'}
            </p>
            <p className="text-[8px] font-mono text-primary-400 uppercase">
              {user?.target_role || 'No Target Set'}
            </p>
          </div>
          <button className="relative p-2 rounded-lg bg-white/5 border border-white/5 text-slate-400 hover:text-white transition-colors">
            <Bell size={14} />
          </button>
          <div className="w-8 h-8 rounded-full bg-primary-500/20 border border-primary-500/30 flex items-center justify-center text-primary-400 text-xs font-bold">
            {(user?.name || 'G')[0]}
          </div>
        </div>
      </div>
    </nav>
  );
}
