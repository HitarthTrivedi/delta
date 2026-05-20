import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Zap, Award, TrendingUp, Calendar as CalendarIcon, 
  CheckCircle, Lock, ShieldAlert, Cpu, 
  ExternalLink, Github, Sparkles, BookOpen, AlertCircle, RefreshCw 
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import GlassPanel from '../components/ui/GlassPanel';
import { usersAPI, briefsAPI, calendarAPI, dossierAPI } from '../lib/api';
import { toast } from 'sonner';

export default function Dashboard() {
  const userId = useAuthStore((state) => state.userId);
  const [stats, setStats] = useState(null);
  const [brief, setBrief] = useState(null);
  const [events, setEvents] = useState([]);
  const [dossier, setDossier] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Roadmap Interaction
  const [selectedNode, setSelectedNode] = useState(null);
  const [githubUrl, setGithubUrl] = useState('');
  const [verifying, setVerifying] = useState(false);

  const loadData = async () => {
    try {
      const statsRes = await usersAPI.getStats(userId);
      setStats(statsRes);

      const briefRes = await briefsAPI.getLatest(userId);
      setBrief(briefRes);

      // Fetch calendar and dossier endpoints
      const calendarRes = await calendarAPI.getEvents(userId);
      setEvents(calendarRes);

      const dossierRes = await dossierAPI.getWeekly(userId);
      setDossier(dossierRes);
    } catch (err) {
      console.error(err);
      toast.error('Unable to fetch live SQLite data. Reverting to sandbox state.');
    }
  };

  useEffect(() => {
    loadData();
  }, [userId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
    toast.success('SQLite Database Engine Re-indexed!');
  };

  const submitMilestone = async (recId, skillName) => {
    if (!githubUrl.trim() || !githubUrl.includes('github.com/')) {
      toast.error('Invalid repository path! Must be a valid github.com link.');
      return;
    }

    setVerifying(true);
    toast.loading(`Validating milestones on github.com... analyzing credentials...`);

    try {
      await briefsAPI.completeRecommendation(recId, {
        evidence_url: githubUrl.trim(),
        evidence_type: 'github'
      });
      
      toast.dismiss();
      toast.success(`Success! Code verified. Completed milestone for ${skillName}.`);
      setSelectedNode(null);
      setGithubUrl('');
      // Reload stats and brief
      await loadData();
    } catch (err) {
      console.error(err);
      toast.dismiss();
      toast.error('Verification failed. SQLite database commit rolled back.');
    } finally {
      setVerifying(false);
    }
  };

  if (!stats || !brief || !dossier) {
    return (
      <div className="pt-24 px-6 min-h-screen mesh-gradient-1 bg-grid-pattern flex flex-col justify-center items-center text-slate-400 font-mono">
        <Cpu className="animate-spin text-primary-400 mb-4" size={32} />
        <h1 className="text-xl font-bold uppercase tracking-widest text-white animate-pulse">Syncing SQLite Hub...</h1>
        <p className="text-[10px] text-slate-500 uppercase mt-1">Delta Career Engine Active</p>
      </div>
    );
  }

  // Calculate circular dial path
  const scorePercent = Math.min(Math.max(stats.delta_score || 0, 0), 100);
  const radius = 50;
  const strokeWidth = 8;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (scorePercent / 100) * circumference;

  return (
    <div className="pt-20 px-6 max-w-7xl mx-auto min-h-screen text-slate-300 font-mono pb-12 selection:bg-primary-500/30 selection:text-white">
      
      {/* Top Banner HUD */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 border-b border-white/5 pb-4 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-widest text-white uppercase flex items-center gap-2">
              <Zap className="text-primary-400 fill-primary-400/20" size={24} /> DELTA // CORE_HUD
            </h1>
            <button 
              onClick={handleRefresh}
              className={`p-1.5 rounded bg-white/5 border border-white/5 text-slate-400 hover:text-white transition-all ${
                refreshing ? 'animate-spin' : ''
              }`}
              title="Refresh database state"
            >
              <RefreshCw size={12} />
            </button>
          </div>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">
            Target Focus: <span className="text-primary-400 font-bold">{stats.target_role || 'CS Engineering'}</span> // Bengaluru & Pune Sprints
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl text-center min-w-[100px]">
            <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">Study Pacing</p>
            <p className="text-xs font-bold text-emerald-400">{stats.hours_per_week}h / Week</p>
          </div>
          <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl text-center min-w-[100px]">
            <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">Alignment Index</p>
            <p className="text-xs font-bold text-primary-400">{stats.alignment_percentage}%</p>
          </div>
          <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl text-center min-w-[100px]">
            <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">Evidence Density</p>
            <p className="text-xs font-bold text-cyan-400">{stats.evidence_density}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Panel: Score and Portfolio Dossier */}
        <div className="lg:col-span-3 space-y-6">
          
          {/* Glowing Radial Score HUD */}
          <GlassPanel className="p-6 relative overflow-hidden text-center border-primary-500/10">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-primary-500 to-indigo-500" />
            <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest mb-4">Delta Score HUD</h2>
            
            <div className="relative w-40 h-40 mx-auto flex items-center justify-center">
              {/* Radial SVGs */}
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  className="stroke-slate-900 fill-none"
                  strokeWidth={strokeWidth}
                />
                <circle
                  cx="80"
                  cy="80"
                  r={radius}
                  className="stroke-primary-500 fill-none"
                  strokeWidth={strokeWidth}
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dashoffset 0.8s ease-in-out' }}
                />
              </svg>
              {/* Inner score overlay */}
              <div className="absolute text-center">
                <p className="text-4xl font-black text-white tracking-tight">{stats.delta_score}</p>
                <p className="text-[8px] text-slate-500 uppercase tracking-widest">Growth Rating</p>
              </div>
            </div>
            
            <p className="text-[9px] text-slate-400 mt-4 px-2 uppercase leading-normal">
              Streak consistency: <span className="text-emerald-400 font-bold">{dossier.performance_metrics.habits_consistency_percentage}%</span>. Keep coding!
            </p>
          </GlassPanel>

          {/* Dossier Career Critiques */}
          <GlassPanel className="p-6 relative overflow-hidden border-white/5 space-y-4">
            <h2 className="text-[10px] font-bold uppercase text-primary-400 tracking-widest mb-2 flex items-center gap-1.5">
              <Award size={12} /> Dossier Critical Assessment
            </h2>

            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Expected Graduate CTC</p>
              <p className="text-xs font-bold text-white uppercase">{dossier.hiring_market_snapshot.salary_trend_range.replace('₹', 'INR')}</p>
            </div>

            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Regional Hiring Hotspot</p>
              <p className="text-[9px] text-slate-300 leading-normal uppercase">{dossier.hiring_market_snapshot.bangalore_pune_demand}</p>
            </div>

            <div className="pt-2 border-t border-white/5 space-y-3">
              <div className="space-y-1.5">
                <span className="text-[8px] font-bold text-emerald-400 uppercase tracking-wider">Keep Doing:</span>
                {dossier.critique.keep_doing.slice(0, 2).map((item, idx) => (
                  <p key={idx} className="text-[8px] text-slate-400 uppercase leading-normal">{`+ ${item}`}</p>
                ))}
              </div>
              <div className="space-y-1.5">
                <span className="text-[8px] font-bold text-red-400 uppercase tracking-wider">Avoid Errors:</span>
                {dossier.critique.mistakes_to_avoid.slice(0, 2).map((item, idx) => (
                  <p key={idx} className="text-[8px] text-slate-400 uppercase leading-normal">{`- ${item}`}</p>
                ))}
              </div>
            </div>
          </GlassPanel>

        </div>

        {/* Center Panel: Zoomable 3-Phase Roadmap Visualizer */}
        <div className="lg:col-span-6 space-y-6">
          <GlassPanel className="p-6 border-white/5 relative overflow-hidden min-h-[500px]">
            <div className="absolute top-0 right-0 w-96 h-96 bg-primary-500/5 rounded-full blur-[140px] pointer-events-none" />
            
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest flex items-center gap-1.5">
                <Cpu size={12} /> Interactive Zoomable Roadmap
              </h2>
              <span className="text-[8px] bg-primary-500/10 text-primary-400 border border-primary-500/20 px-2 py-0.5 rounded uppercase tracking-wider">
                3 Chronological Phases
              </span>
            </div>

            {/* Dynamic Phase Cards */}
            <div className="space-y-6">
              {brief.phases?.map((phase, pIdx) => (
                <div key={phase.id} className="p-4 rounded-xl bg-slate-950/40 border border-white/5 space-y-3 relative">
                  <div className="absolute top-4 right-4 text-[8px] font-mono text-slate-500 uppercase">
                    Phase {pIdx + 1}
                  </div>
                  
                  <h3 className="text-xs font-bold text-white uppercase flex items-center gap-1.5">
                    <BookOpen size={12} className="text-primary-400" /> {phase.name}
                  </h3>
                  <p className="text-[9px] text-slate-500 leading-normal uppercase">{phase.description}</p>
                  
                  {/* Skill Node Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2">
                    {phase.nodes?.map((node) => {
                      const isMastered = node.status === 'mastered';
                      const isInProgress = node.status === 'in_progress';
                      const isLocked = node.status === 'locked';
                      
                      return (
                        <button
                          key={node.id}
                          onClick={() => setSelectedNode({ ...node, pIdx })}
                          className={`p-3 rounded-lg border text-left flex flex-col justify-between transition-all duration-300 relative group overflow-hidden ${
                            isMastered 
                              ? 'bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40 text-emerald-300' 
                              : isInProgress
                                ? 'bg-primary-500/5 border-primary-500/20 hover:border-primary-500/40 text-primary-300' 
                                : 'bg-slate-900/60 border-white/5 hover:border-white/20 text-slate-400'
                          }`}
                        >
                          <div className="flex items-center justify-between w-full mb-1">
                            <span className="text-[10px] font-bold uppercase tracking-wider">{node.label}</span>
                            {isMastered && <CheckCircle size={10} className="text-emerald-400" />}
                            {isLocked && <Lock size={10} className="text-slate-600" />}
                            {isInProgress && <Zap size={10} className="text-primary-400 animate-pulse" />}
                          </div>
                          
                          <span className="text-[7px] text-slate-500 uppercase tracking-widest mt-2 block group-hover:text-slate-400 transition-colors">
                            {node.status.replace('_', ' ')} // Expand details
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Expandable Active Node detail drawer overlay */}
            <AnimatePresence>
              {selectedNode && (
                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 15 }}
                  className="absolute inset-0 bg-slate-950/95 z-20 p-6 flex flex-col justify-between overflow-y-auto"
                >
                  <div className="space-y-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[8px] text-primary-400 uppercase tracking-widest font-bold">Phase {selectedNode.pIdx + 1} Node detail</span>
                        <h3 className="text-sm font-black text-white uppercase mt-1 flex items-center gap-1.5">
                          {selectedNode.label}
                        </h3>
                      </div>
                      <button 
                        onClick={() => setSelectedNode(null)}
                        className="text-[9px] uppercase text-slate-500 hover:text-white px-2 py-1 rounded bg-white/5 transition-colors"
                      >
                        Close
                      </button>
                    </div>

                    <p className="text-[10px] text-slate-400 leading-relaxed uppercase">{selectedNode.description}</p>

                    {/* Custom tech twists & architect alerts from model seed */}
                    {selectedNode.tech_twist && (
                      <div className="p-3 bg-primary-500/5 border border-primary-500/10 rounded-lg space-y-1">
                        <span className="text-[8px] font-bold text-primary-400 uppercase tracking-wider flex items-center gap-1">
                          <Sparkles size={10} /> Tech Twist (Pragmatic Caveat):
                        </span>
                        <p className="text-[9px] text-slate-300 leading-normal uppercase">{selectedNode.tech_twist}</p>
                      </div>
                    )}

                    {selectedNode.architect_warning && (
                      <div className="p-3 bg-yellow-500/5 border border-yellow-500/10 rounded-lg space-y-1">
                        <span className="text-[8px] font-bold text-yellow-500 uppercase tracking-wider flex items-center gap-1">
                          <ShieldAlert size={10} /> Architect Warning:
                        </span>
                        <p className="text-[9px] text-slate-300 leading-normal uppercase">{selectedNode.architect_warning}</p>
                      </div>
                    )}

                    {selectedNode.certification && (
                      <div className="p-3 bg-violet-500/5 border border-violet-500/10 rounded-lg space-y-1">
                        <span className="text-[8px] font-bold text-violet-400 uppercase tracking-wider flex items-center gap-1">
                          <Award size={10} /> Resume Certification Weight:
                        </span>
                        <p className="text-[9px] text-slate-300 leading-normal uppercase">{selectedNode.certification}</p>
                      </div>
                    )}
                  </div>

                  {/* Interactive Proof-of-Work Verification Submission */}
                  <div className="mt-6 border-t border-white/5 pt-4">
                    <h4 className="text-[10px] font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-1">
                      <Github size={12} className="text-slate-400" /> Verify Proof of Work Milestone
                    </h4>
                    <p className="text-[8px] text-slate-500 uppercase leading-normal mb-3">
                      Submit your GitHub Repository URL below. The engine will inspect and index files dynamically.
                    </p>
                    
                    {/* Find active recommendation item for this skill */}
                    {(() => {
                      const rec = brief.recommendation_items?.find(r => r.skill.toLowerCase() === selectedNode.label.toLowerCase() || selectedNode.id.includes(r.skill.toLowerCase()));
                      
                      if (!rec) {
                        return (
                          <div className="p-3 bg-white/5 rounded-lg border border-white/5 flex items-center gap-2 text-slate-500">
                            <AlertCircle size={12} />
                            <span className="text-[8px] uppercase">Verify and unlock previous nodes to activate this checkpoint.</span>
                          </div>
                        );
                      }

                      if (rec.status === 'completed') {
                        return (
                          <div className="p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20 text-emerald-400 flex items-center gap-1.5">
                            <CheckCircle size={12} />
                            <span className="text-[9px] uppercase font-bold">Milestone Verified! Commited to Immutable Ledger.</span>
                          </div>
                        );
                      }

                      return (
                        <div className="flex gap-2">
                          <input 
                            type="text" 
                            placeholder="e.g. https://github.com/myusername/delta-fastapi-app"
                            value={githubUrl}
                            onChange={(e) => setGithubUrl(e.target.value)}
                            disabled={verifying}
                            className="flex-1 bg-slate-900 border border-white/5 rounded px-3 py-2 text-[10px] text-white focus:outline-none focus:border-primary-500 font-mono"
                          />
                          <button
                            onClick={() => submitMilestone(rec.id, rec.skill)}
                            disabled={verifying}
                            className="btn-primary px-4 py-2 text-[9px] uppercase tracking-wider font-bold"
                          >
                            {verifying ? 'Checking...' : 'Verify Code'}
                          </button>
                        </div>
                      );
                    })()}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </GlassPanel>
        </div>

        {/* Right Panel: Upcoming Sprints and Opportunities */}
        <div className="lg:col-span-3 space-y-6">
          <GlassPanel className="p-6 border-white/5 relative overflow-hidden min-h-[500px]">
            <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-1.5">
              <CalendarIcon size={12} /> Competitive Sprints
            </h2>

            <div className="space-y-4">
              {events.map((ev, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-white/5 space-y-2 relative group hover:border-primary-500/20 transition-all duration-300">
                  <div className="flex justify-between items-center">
                    <span className="text-[8px] text-primary-400 font-bold uppercase tracking-wider">{ev.platform}</span>
                    <span className="text-[8px] bg-slate-900 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded font-bold">
                      Match {ev.match_percentage}%
                    </span>
                  </div>
                  <h4 className="text-[9px] font-bold text-white uppercase leading-normal leading-tight group-hover:text-primary-400 transition-colors">
                    {ev.title}
                  </h4>
                  
                  <div className="space-y-1 text-[7px] text-slate-500 uppercase leading-normal">
                    <p><span className="text-slate-400">Award:</span> {ev.rewards.replace('₹', 'INR')}</p>
                    <p><span className="text-slate-400">Skills:</span> {ev.recommended_skills.join(', ')}</p>
                  </div>
                </div>
              ))}
            </div>
          </GlassPanel>
        </div>

      </div>
    </div>
  );
}
