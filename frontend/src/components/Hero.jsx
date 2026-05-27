import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, Terminal, Database, ShieldAlert, Cpu, Network } from 'lucide-react';
import ParticleBackground from './ParticleBackground';
import FloatingShapes from './FloatingShapes';
import GlassPanel from './ui/GlassPanel';
import { heroData } from '../mockData';

const Hero = () => {
  const [syncPercentage, setSyncPercentage] = useState(0);
  const [terminalLogs, setTerminalLogs] = useState([
    'Initializing Delta Cognitive Core...',
    'Awaiting neural vision bridge socket connection...'
  ]);

  // Simulated live metrics on the landing page for high-fidelity engagement
  useEffect(() => {
    const syncInterval = setInterval(() => {
      setSyncPercentage((prev) => (prev < 95 ? prev + 1 : 95));
    }, 150);

    const logPool = [
      '[OK] Ingested user_intent: "Founding Engineer aspirations"',
      '[QUERY] Running Tavily live market demand indexing...',
      '[WARNING] Gap detected: Cloud Architecture (AWS/GCP)',
      '[CRITIC] Live Socratic conflict scanner instantiated',
      '[SQLITE] Synced 55 career vertices and 54 capability edges',
      '[OS] Neural twin sync index optimal at 94.8% delta',
      '[OK] Auto-resume generator compilation successful'
    ];

    let logIndex = 0;
    const logInterval = setInterval(() => {
      setTerminalLogs((prev) => {
        const nextLogs = [...prev, logPool[logIndex]];
        logIndex = (logIndex + 1) % logPool.length;
        if (nextLogs.length > 5) nextLogs.shift();
        return nextLogs;
      });
    }, 2500);

    return () => {
      clearInterval(syncInterval);
      clearInterval(logInterval);
    };
  }, []);

  return (
    <section className="hero-section" style={{ position: 'relative', overflow: 'hidden', padding: '9rem 1.5rem 6rem' }}>
      <FloatingShapes />
      <ParticleBackground />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex flex-col lg:flex-row items-center gap-12 text-left">
        {/* Left Column: Core CTA and Value Prop */}
        <div className="flex-1 flex flex-col items-start">
          {/* Announcement Badge */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs font-mono font-bold uppercase tracking-widest text-indigo-400">
              <Sparkles size={12} className="animate-pulse text-indigo-400" />
              <span>{heroData.announcement}</span>
            </div>
          </motion.div>

          {/* Title */}
          <motion.h1
            className="heading-hero text-5xl sm:text-6xl lg:text-7xl font-mono font-black tracking-widest uppercase mb-6"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Your{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 select-all drop-shadow-[0_0_15px_rgba(139,92,246,0.3)]">
              Digital Twin
            </span>{' '}
            Career OS
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            className="body-large text-slate-300 mb-8 max-w-xl leading-relaxed text-sm sm:text-base font-mono uppercase tracking-wider text-justify"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Delta constructs a real-time cognitive graph representing your skills, goals, and market demands. It runs an autonomous consensus engine to build your portfolio and automate your professional presence.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <button
              className="btn-primary px-8 py-4 text-xs font-mono font-bold uppercase tracking-widest flex items-center justify-center gap-2 border border-white/10 shadow-lg shadow-white/5 transition-all duration-300 rounded-lg"
              onClick={() => window.location.href = '/onboarding'}
            >
              {heroData.ctaPrimary}
              <ArrowRight size={14} />
            </button>
            <button 
              className="btn-secondary px-8 py-4 text-xs font-mono font-bold uppercase tracking-widest flex items-center justify-center gap-2 border border-white/5 bg-slate-900/60 hover:bg-slate-900 transition-all duration-300 rounded-lg"
              onClick={() => {
                const target = document.getElementById('features');
                if (target) target.scrollIntoView({ behavior: 'smooth' });
              }}
            >
              {heroData.ctaSecondary}
            </button>
          </motion.div>
        </div>

        {/* Right Column: Live Simulated Digital Twin Cockpit */}
        <motion.div 
          className="flex-1 w-full max-w-xl"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2 }}
        >
          <GlassPanel className="p-6 border-indigo-500/20 bg-slate-950/40 relative overflow-hidden font-mono shadow-2xl shadow-indigo-500/5">
            {/* Top Bar Decorative Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-5 select-none">
              <div className="flex items-center gap-2">
                <Terminal size={14} className="text-indigo-400 animate-pulse" />
                <span className="text-[10px] uppercase font-bold tracking-widest text-slate-300">
                  COGNITIVE TWIN ENGINE // PREVIEW
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                <span className="text-[8px] uppercase tracking-widest text-emerald-400 font-bold">
                  LIVE SOCKET
                </span>
              </div>
            </div>

            {/* Core Visual Grid Dashboard */}
            <div className="grid grid-cols-2 gap-4 mb-5">
              {/* Box 1: Sync Ingestion completeness */}
              <div className="p-4 rounded-lg bg-slate-950/80 border border-white/5 flex flex-col justify-between items-center text-center h-[140px]">
                <span className="text-[8px] uppercase text-slate-500 tracking-widest font-bold">
                  Ingestion Completeness
                </span>
                
                <div className="relative w-16 h-16 flex items-center justify-center my-1 select-none">
                  {/* Glowing Radial Circle */}
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-slate-900"
                      strokeWidth="2.5"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="text-indigo-500 drop-shadow-[0_0_4px_rgba(99,102,241,0.5)]"
                      strokeDasharray={`${syncPercentage}, 100`}
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <span className="absolute text-xs font-black text-indigo-400">
                    {syncPercentage}%
                  </span>
                </div>

                <div className="flex gap-4 text-[7px] text-slate-400">
                  <div>
                    <span className="block font-bold text-white">55</span>
                    <span>NODES</span>
                  </div>
                  <div>
                    <span className="block font-bold text-white">54</span>
                    <span>EDGES</span>
                  </div>
                </div>
              </div>

              {/* Box 2: Critic Scanning & Active Tensions */}
              <div className="p-4 rounded-lg bg-slate-950/80 border border-white/5 flex flex-col justify-between h-[140px]">
                <div className="flex justify-between items-center select-none">
                  <span className="text-[8px] uppercase text-slate-500 tracking-widest font-bold">
                    Active Tension Nodes
                  </span>
                  <ShieldAlert size={10} className="text-rose-400 animate-pulse" />
                </div>

                {/* Simulated live scanner list */}
                <div className="space-y-2 mt-2 flex-1 flex flex-col justify-center">
                  <div className="p-2 rounded bg-rose-500/5 border border-rose-500/10 text-[8px] uppercase leading-normal text-rose-300/90 flex gap-1.5 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping shrink-0" />
                    <span>AWS Cloud Gap (Severe)</span>
                  </div>
                  <div className="p-2 rounded bg-amber-500/5 border border-amber-500/10 text-[8px] uppercase leading-normal text-amber-300/90 flex gap-1.5 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                    <span>System Design Gap (Moderate)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Simulated Live Memory Graph Vector Network */}
            <div className="p-4 rounded-lg bg-slate-950/80 border border-white/5 mb-5 relative overflow-hidden h-[120px] select-none">
              <span className="absolute top-2 left-3 text-[8px] uppercase text-slate-500 tracking-widest font-bold">
                Capability Mapping Vector
              </span>
              <div className="absolute top-2 right-3 text-[8px] text-indigo-400 uppercase tracking-widest flex items-center gap-1 font-bold">
                <Network size={10} /> Neural Graph
              </div>

              {/* Cyber graph mock vectors */}
              <div className="w-full h-full flex items-center justify-center relative mt-2">
                {/* Visual SVG paths connecting components */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-40">
                  <line x1="20%" y1="50%" x2="50%" y2="20%" stroke="#8b5cf6" strokeWidth="1" strokeDasharray="3 3" />
                  <line x1="20%" y1="50%" x2="50%" y2="80%" stroke="#06b6d4" strokeWidth="1" strokeDasharray="3 3" />
                  <line x1="50%" y1="20%" x2="80%" y2="50%" stroke="#10b981" strokeWidth="1" />
                  <line x1="50%" y1="80%" x2="80%" y2="50%" stroke="#fb923c" strokeWidth="1" />
                  <line x1="20%" y1="50%" x2="80%" y2="50%" stroke="#6366f1" strokeWidth="1" strokeDasharray="5 5" />
                </svg>

                {/* Nodes */}
                <div className="absolute left-[8%] top-[40%] bg-indigo-500/10 border border-indigo-500/40 text-[7px] text-indigo-300 px-2 py-1 rounded-md uppercase font-bold tracking-widest shadow-md animate-pulse">
                  FastAPI
                </div>
                <div className="absolute left-[38%] top-[10%] bg-purple-500/10 border border-purple-500/40 text-[7px] text-purple-300 px-2 py-1 rounded-md uppercase font-bold tracking-widest shadow-md">
                  System Design
                </div>
                <div className="absolute left-[38%] top-[70%] bg-cyan-500/10 border border-cyan-500/40 text-[7px] text-cyan-300 px-2 py-1 rounded-md uppercase font-bold tracking-widest shadow-md">
                  SQLite DB
                </div>
                <div className="absolute right-[8%] top-[40%] bg-emerald-500/10 border border-emerald-500/40 text-[7px] text-emerald-300 px-2 py-1 rounded-md uppercase font-bold tracking-widest shadow-md">
                  AWS Cloud
                </div>
              </div>
            </div>

            {/* Bottom Real-time Ingestion SQL/Console Logs */}
            <div className="bg-black/95 border border-white/5 rounded-lg p-3 h-28 overflow-hidden flex flex-col justify-start leading-relaxed text-left select-none relative">
              <span className="absolute top-2 right-3 text-[6px] text-slate-600 font-bold uppercase tracking-wider">
                SQLITE RECURSIVE ENGINE
              </span>
              <div className="text-[8px] font-mono text-slate-400 space-y-1 mt-1">
                {terminalLogs.map((log, idx) => (
                  <p key={idx} className={`${
                    log.includes('[WARNING]') ? 'text-amber-400/90' : 
                    log.includes('[ERROR]') ? 'text-rose-400/90' : 
                    log.includes('[OK]') ? 'text-emerald-400/90' : 
                    log.includes('[CRITIC]') ? 'text-indigo-400/90' : 
                    'text-slate-400'
                  }`}>
                    {log}
                  </p>
                ))}
              </div>
            </div>
          </GlassPanel>
        </motion.div>
      </div>
    </section>
  );
};

export default Hero;