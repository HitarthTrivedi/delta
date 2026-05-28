import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Zap, Award, TrendingUp, Calendar as CalendarIcon, 
  CheckCircle, Lock, ShieldAlert, Cpu, 
  ExternalLink, Github, Sparkles, BookOpen, AlertCircle, RefreshCw, Network
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import GlassPanel from '../components/ui/GlassPanel';
import { usersAPI, briefsAPI, calendarAPI, dossierAPI, careerOSAPI } from '../lib/api';
import { toast } from 'sonner';

export default function Dashboard() {
  const userId = useAuthStore((state) => state.userId);
  const [stats, setStats] = useState(null);
  const [brief, setBrief] = useState(null);
  const [events, setEvents] = useState([]);
  const [sourceStatuses, setSourceStatuses] = useState([]);
  const [dossier, setDossier] = useState(null);
  const [careerContext, setCareerContext] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [consolidating, setConsolidating] = useState(false);

  // Roadmap Interaction
  const [selectedNode, setSelectedNode] = useState(null);
  const [githubUrl, setGithubUrl] = useState('');
  const [verifying, setVerifying] = useState(false);

  // Weekly Brief Interactive HUD States
  const [checkedActions, setCheckedActions] = useState({});
  const [resolverAnswers, setResolverAnswers] = useState({});
  const [submittedAnswers, setSubmittedAnswers] = useState({});

  // Web Audio Synth Chime
  const playBeep = useCallback((freq = 800, type = 'sine', duration = 0.08) => {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.type = type;
      oscillator.frequency.value = freq;
      gainNode.gain.setValueAtTime(0.04, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
      oscillator.start(audioCtx.currentTime);
      oscillator.stop(audioCtx.currentTime + duration);
    } catch (e) {
      console.warn('Web Audio API not supported or blocked:', e);
    }
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [statsRes, briefRes, calendarRes, sourceRes, dossierRes, contextRes, statusRes] = await Promise.all([
        usersAPI.getStats(userId),
        briefsAPI.getLatest(userId),
        calendarAPI.getEvents(userId),
        calendarAPI.getSources(),
        dossierAPI.getWeekly(userId),
        careerOSAPI.getContext(userId),
        careerOSAPI.getSystemStatus(),
      ]);
      setStats(statsRes);
      setBrief(briefRes);
      setEvents(calendarRes);
      setSourceStatuses(sourceRes);
      setDossier(dossierRes);
      setCareerContext(contextRes);
      setSystemStatus(statusRes);
    } catch (err) {
      console.error(err);
      toast.error('Unable to fetch live SQLite data. Reverting to sandbox state.');
    }
  }, [userId]);

  const toggleAction = useCallback(async (idx) => {
    playBeep(900, 'triangle', 0.1);
    const newChecked = !checkedActions[idx];
    setCheckedActions(prev => ({
      ...prev,
      [idx]: newChecked
    }));
    
    try {
      const actionText = brief.actions[idx];
      await careerOSAPI.logJourneyEvent(userId, {
        event_type: 'task_completed',
        summary: `${newChecked ? 'Completed' : 'Reopened'} action item: "${actionText}"`,
        evidence: { action: actionText, index: idx, completed: newChecked },
        impact: { progress_updated: true }
      });
      await loadData();
      toast.success(newChecked ? 'Action item completed!' : 'Action item reopened!');
    } catch (e) {
      console.error(e);
    }
  }, [userId, checkedActions, brief, playBeep, loadData]);

  const submitAnswer = useCallback(async (idx, qText) => {
    const answer = resolverAnswers[idx];
    if (!answer || !answer.trim()) return;
    
    playBeep(1200, 'sine', 0.2);
    setSubmittedAnswers(prev => ({
      ...prev,
      [idx]: true
    }));
    toast.success('Response ingested into Career Profile Memory!');
    
    try {
      await careerOSAPI.logJourneyEvent(userId, {
        event_type: 'user_reflection',
        summary: `Resolved uncertainty question: "${qText}" with answer: "${answer.trim()}"`,
        evidence: { question: qText, answer: answer.trim() },
        impact: { memory_uncertainty_reduced: true }
      });
      await loadData();
    } catch (e) {
      console.error(e);
    }
  }, [userId, resolverAnswers, playBeep, loadData]);


  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const refreshedContext = await careerOSAPI.runWeeklyCycle(userId);
      setCareerContext(refreshedContext);
      await loadData();
    } catch (err) {
      console.error(err);
      await loadData();
    }
    setRefreshing(false);
    toast.success('Career OS weekly cycle refreshed!');
  };

  const handleConsolidateMemory = async () => {
    setConsolidating(true);
    try {
      const context = await careerOSAPI.consolidateMemory(userId);
      setCareerContext(context);
      await loadData();
      const report = context.memory_consolidation || {};
      toast.success(`Memory consolidated. Merged ${report.merged_nodes || 0} duplicate nodes.`);
    } catch (err) {
      console.error(err);
      toast.error('Memory consolidation failed.');
    } finally {
      setConsolidating(false);
    }
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

  if (!stats || !brief || !dossier || !careerContext) {
    return (
      <div className="pt-24 px-6 min-h-screen mesh-gradient-1 bg-grid-pattern flex flex-col justify-center items-center text-slate-400 font-mono">
        <Cpu className="animate-spin text-primary-400 mb-4" size={32} />
        <h1 className="text-xl font-bold uppercase tracking-widest text-white animate-pulse">Syncing SQLite Hub...</h1>
        <p className="text-[10px] text-slate-500 uppercase mt-1">Delta Career Engine Active</p>
      </div>
    );
  }

  // Calculate circular dial path
  const roadmap = careerContext.roadmap || {};
  const memory = careerContext.memory || {};
  const semanticMemory = careerContext.semantic_memory || {};
  const semanticSummary = semanticMemory.summary || {};
  const semanticSession = semanticMemory.latest_ingestion_session || {};
  const semanticTensions = semanticMemory.active_tensions || [];
  const semanticNodes = semanticMemory.recent_nodes || [];
  const dimensionBalance = semanticMemory.dimension_balance || {};
  const market = careerContext.market || {};
  const journey = careerContext.journey_until_today || [];
  const proofProjects = careerContext.proof_projects || brief.proof_projects || [];
  const portfolio = careerContext.portfolio_assessment || brief.portfolio_assessment || {};
  const opportunitySignals = careerContext.opportunity_signals || market.raw_data?.opportunity_signals || {};
  const repeatedOpportunitySkills = opportunitySignals.repeated_skills || [];
  const phases = roadmap.phases?.length ? roadmap.phases : brief.phases || [];
  const activePhase = phases.find(phase => phase.id === roadmap.active_phase_id);
  const targetRole = memory.ambitions?.target_role || market.target_role || 'Career-ready professional';
  const hoursPerWeek = memory.constraints?.hours_per_week || stats.hours_per_week || 10;
  const alignmentPercentage = Math.round((stats.role_alignment || 0) * 100);
  const deltaScore = Math.round(brief.delta_score_end ?? brief.delta_score_start ?? 0);
  const scorePercent = Math.min(Math.max(deltaScore || 0, 0), 100);
  const modules = systemStatus?.modules || {};
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
            Target Focus: <span className="text-primary-400 font-bold">{targetRole}</span> // Career OS Synced
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl text-center min-w-[100px]">
            <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">Study Pacing</p>
            <p className="text-xs font-bold text-emerald-400">{hoursPerWeek}h / Week</p>
          </div>
          <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl text-center min-w-[100px]">
            <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">Alignment Index</p>
            <p className="text-xs font-bold text-primary-400">{alignmentPercentage}%</p>
          </div>
          <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl text-center min-w-[100px]">
            <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">Evidence Density</p>
            <p className="text-xs font-bold text-cyan-400">{stats.evidence_density}</p>
          </div>
          <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl text-center min-w-[100px]">
            <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-0.5">OS Status</p>
            <p className="text-xs font-bold text-emerald-400">{systemStatus?.status || 'syncing'}</p>
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
                <p className="text-4xl font-black text-white tracking-tight">{deltaScore}</p>
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

          <GlassPanel className="p-6 relative overflow-hidden border-cyan-500/10 space-y-4">
            <h2 className="text-[10px] font-bold uppercase text-cyan-400 tracking-widest mb-2 flex items-center gap-1.5">
              <Sparkles size={12} /> Career Memory Vault
            </h2>

            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Learning Style</p>
              <p className="text-xs font-bold text-white uppercase">{memory.preferences?.learning_style || 'unknown'}</p>
            </div>

            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Known Gaps</p>
              <p className="text-[9px] text-slate-300 uppercase leading-normal">
                {(memory.capabilities?.gaps_identified || []).slice(0, 4).join(', ') || 'No gaps indexed yet'}
              </p>
            </div>

            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-1">Confidence</p>
              <p className="text-xs font-bold text-cyan-400">{Math.round((memory.confidence_score || 0) * 100)}%</p>
            </div>
          </GlassPanel>

          <GlassPanel className="p-6 relative overflow-hidden border-indigo-500/10 space-y-4">
            <h2 className="text-[10px] font-bold uppercase text-indigo-400 tracking-widest mb-2 flex items-center gap-1.5">
              <Network size={12} /> Semantic GraphRAG Core
            </h2>
            <button
              onClick={handleConsolidateMemory}
              disabled={consolidating}
              className="absolute top-5 right-5 p-1.5 rounded bg-white/5 border border-white/5 text-slate-400 hover:text-white disabled:opacity-50 transition-all"
              title="Run memory consolidation"
            >
              <RefreshCw size={11} className={consolidating ? 'animate-spin' : ''} />
            </button>

            <div className="grid grid-cols-2 gap-2">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-white/5">
                <p className="text-[8px] text-slate-500 uppercase tracking-wider">Vertices</p>
                <p className="text-sm font-black text-white">{semanticSummary.total_nodes || 0}</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/60 border border-white/5">
                <p className="text-[8px] text-slate-500 uppercase tracking-wider">Edges</p>
                <p className="text-sm font-black text-indigo-400">{semanticSummary.total_edges || 0}</p>
              </div>
            </div>

            <div className="space-y-2">
              {['cognitive', 'emotional', 'temporal', 'social'].map((dimension) => (
                <div key={dimension}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[8px] text-slate-500 uppercase tracking-wider">{dimension}</span>
                    <span className="text-[8px] text-slate-400">{dimensionBalance[dimension] || 0}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-950 border border-white/5 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400"
                      style={{ width: `${Math.min(dimensionBalance[dimension] || 0, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-white/5">
              <p className="text-[8px] text-slate-500 uppercase tracking-wider mb-1">Latest Ingestion</p>
              <p className="text-[8px] text-slate-300 uppercase leading-normal">
                {semanticSession.status
                  ? `${semanticSession.status} // round ${semanticSession.current_round || 0} // ${Math.round((semanticSession.confidence_score || 0) * 100)}% confidence`
                  : 'No semantic ingestion session indexed yet'}
              </p>
            </div>

            {semanticNodes.length > 0 && (
              <div className="space-y-2">
                <p className="text-[8px] text-slate-500 uppercase tracking-wider">Recent Nodes</p>
                {semanticNodes.slice(0, 4).map((node) => (
                  <div key={node.id} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-950/60 border border-white/5">
                    <span className="text-[8px] text-slate-300 uppercase tracking-wider truncate">{node.label}</span>
                    <span className="text-[7px] text-indigo-400 uppercase">{node.type}</span>
                  </div>
                ))}
              </div>
            )}
          </GlassPanel>

          <GlassPanel className="p-6 relative overflow-hidden border-emerald-500/10 space-y-3">
            <h2 className="text-[10px] font-bold uppercase text-emerald-400 tracking-widest mb-2 flex items-center gap-1.5">
              <Cpu size={12} /> Core Modules
            </h2>
            {Object.entries(modules).map(([name, module]) => (
              <div key={name} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-950/60 border border-white/5">
                <span className="text-[8px] text-slate-300 uppercase tracking-wider">{name.replaceAll('_', ' ')}</span>
                <span className={`text-[7px] border px-1.5 py-0.5 rounded uppercase font-bold ${
                  module.ready
                    ? 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10'
                    : 'text-rose-400 border-rose-500/20 bg-rose-500/10'
                }`}>
                  {module.ready ? 'ready' : 'offline'}
                </span>
              </div>
            ))}
          </GlassPanel>

        </div>

        {/* Center Panel: Zoomable 3-Phase Roadmap Visualizer */}
        <div className="lg:col-span-6 space-y-6">
          
          {/* Weekly Career Brief HUD */}
          <GlassPanel className="p-6 border-white/5 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-primary-400 via-indigo-500 to-cyan-400" />
            
            {/* Header with Glowing Status Badge */}
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-primary-400 animate-ping" />
                <h2 className="text-xs font-black uppercase text-white tracking-widest">
                  Weekly Career OS Dossier
                </h2>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-[8px] text-slate-500 uppercase tracking-widest">
                  Status //
                </span>
                {(() => {
                  const status = brief.track_status || 'on_track';
                  if (status === 'ahead') {
                    return (
                      <span className="text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded uppercase tracking-wider animate-pulse flex items-center gap-1 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
                        <Zap size={10} className="animate-bounce" /> Ahead of Target
                      </span>
                    );
                  } else if (status === 'drifting') {
                    return (
                      <span className="text-[9px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded uppercase tracking-wider flex items-center gap-1 shadow-[0_0_8px_rgba(245,158,11,0.2)]">
                        <AlertCircle size={10} /> Drifting Pace
                      </span>
                    );
                  } else if (status === 'blocked') {
                    return (
                      <span className="text-[9px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 px-2 py-0.5 rounded uppercase tracking-wider flex items-center gap-1 animate-pulse shadow-[0_0_8px_rgba(244,63,94,0.2)]">
                        <ShieldAlert size={10} /> Action Blocked
                      </span>
                    );
                  } else {
                    return (
                      <span className="text-[9px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 px-2 py-0.5 rounded uppercase tracking-wider flex items-center gap-1">
                        <Zap size={10} className="fill-cyan-400/20" /> On Track
                      </span>
                    );
                  }
                })()}
              </div>
            </div>

            {/* Inner Dashboard Layout: Split Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 border-b border-white/5 pb-6">
              
              {/* Left Column: Adaptive Pulses (Market vs Personal) */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <h3 className="text-[9px] font-bold uppercase text-primary-400 tracking-wider flex items-center gap-1">
                    <TrendingUp size={11} /> What Changed in the World
                  </h3>
                  <div className="space-y-2">
                    {(brief.market_changes || []).map((change, idx) => (
                      <div key={idx} className="flex gap-2 items-start bg-slate-950/40 p-2.5 rounded-lg border border-white/5">
                        <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1 shadow-[0_0_4px_rgba(34,211,238,0.5)] flex-shrink-0" />
                        <p className="text-[8px] text-slate-300 leading-normal uppercase">{change}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-[9px] font-bold uppercase text-cyan-400 tracking-wider flex items-center gap-1">
                    <Sparkles size={11} /> What Changed in You
                  </h3>
                  <div className="space-y-2">
                    {(brief.personal_changes || []).map((change, idx) => (
                      <div key={idx} className="flex gap-2 items-start bg-slate-950/40 p-2.5 rounded-lg border border-white/5">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary-400 mt-1 shadow-[0_0_4px_rgba(236,72,153,0.5)] flex-shrink-0" />
                        <p className="text-[8px] text-slate-300 leading-normal uppercase">{change}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Column: Weekly Action Items */}
              <div className="space-y-3">
                <h3 className="text-[9px] font-bold uppercase text-slate-300 tracking-wider flex items-center gap-1">
                  <CheckCircle size={11} className="text-emerald-400" /> Weekly Pacing Checklist
                </h3>
                <p className="text-[7px] text-slate-500 uppercase leading-normal">
                  Toggle completed actions below to verify your sprint velocity.
                </p>
                
                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                  {(brief.actions || []).map((action, idx) => {
                    const isChecked = !!checkedActions[idx];
                    return (
                      <button
                        key={idx}
                        onClick={() => toggleAction(idx)}
                        className={`w-full p-2.5 rounded-lg border text-left flex items-start gap-2.5 transition-all uppercase ${
                          isChecked 
                            ? 'bg-emerald-500/5 border-emerald-500/20 text-slate-400 line-through' 
                            : 'bg-slate-950/50 border-white/5 text-slate-300 hover:border-white/10'
                        }`}
                      >
                        <div className={`w-3.5 h-3.5 rounded border flex-shrink-0 flex items-center justify-center mt-0.5 ${
                          isChecked 
                            ? 'bg-emerald-500 border-emerald-500 text-slate-950' 
                            : 'border-slate-700'
                        }`}>
                          {isChecked && <span className="text-[9px] font-black">✓</span>}
                        </div>
                        <span className="text-[8px] leading-normal">{action}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

            </div>

            {/* Bottom Row: Opportunities and Uncertainty Resolver */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 items-start">
              
              {/* Opportunities Panel */}
              <div className="space-y-2">
                <h3 className="text-[9px] font-bold uppercase text-slate-300 tracking-wider flex items-center gap-1">
                  <Award size={11} className="text-violet-400" /> Active Sprints & Deadlines
                </h3>
                <div className="space-y-2">
                  {(brief.opportunities || []).map((opp, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-slate-950/30 border border-white/5 flex justify-between items-center gap-4">
                      <p className="text-[8px] text-slate-300 uppercase leading-tight">{opp}</p>
                      <span className="text-[7px] bg-violet-500/10 text-violet-400 border border-violet-500/20 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider shrink-0">
                        Match
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Uncertainty Resolver Panel */}
              <div className="space-y-2">
                <h3 className="text-[9px] font-bold uppercase text-primary-400 tracking-wider flex items-center gap-1">
                  <Sparkles size={11} /> uncertainty_resolvers
                </h3>
                <p className="text-[7px] text-slate-500 uppercase leading-normal">
                  Answer the AI engine's questions to reduce career profile ambiguity.
                </p>

                <div className="space-y-3">
                  {(brief.questions_for_user || []).map((question, idx) => {
                    const isSubmitted = !!submittedAnswers[idx];
                    return (
                      <div key={idx} className="p-3 bg-slate-950/40 border border-white/5 rounded-lg space-y-2">
                        <p className="text-[8px] text-slate-300 leading-normal uppercase">{question}</p>
                        
                        {isSubmitted ? (
                          <div className="text-[8px] text-emerald-400 font-bold uppercase tracking-widest flex items-center gap-1">
                            ✓ Synced in Vault
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <input 
                              type="text" 
                              placeholder="Type answer to update OS memory..."
                              value={resolverAnswers[idx] || ''}
                              onChange={(e) => setResolverAnswers(prev => ({ ...prev, [idx]: e.target.value }))}
                              className="flex-1 bg-slate-900 border border-white/5 rounded px-2 py-1 text-[8px] text-white focus:outline-none focus:border-primary-500 font-mono"
                            />
                            <button
                              onClick={() => submitAnswer(idx, question)}
                              className="bg-primary-500 hover:bg-primary-600 text-white font-bold text-[8px] uppercase tracking-wider px-2 py-1 rounded transition-colors"
                            >
                              Sync
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                  {!(brief.questions_for_user || []).length && (
                    <div className="text-[8px] uppercase text-slate-500 leading-normal p-2.5 bg-slate-950/20 border border-white/5 rounded-lg">
                      All uncertainties cleared. System models running at full accuracy.
                    </div>
                  )}
                </div>
              </div>

            </div>

          </GlassPanel>

          <GlassPanel className="p-6 border-white/5 relative overflow-hidden min-h-[500px]">
            <div className="absolute top-0 right-0 w-96 h-96 bg-primary-500/5 rounded-full blur-[140px] pointer-events-none" />
            
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest flex items-center gap-1.5">
                <Cpu size={12} /> Interactive Zoomable Roadmap
              </h2>
              <span className="text-[8px] bg-primary-500/10 text-primary-400 border border-primary-500/20 px-2 py-0.5 rounded uppercase tracking-wider">
                {activePhase?.name || 'Central Roadmap'}
              </span>
            </div>

            {/* Dynamic Phase Cards */}
            <div className="space-y-6">
              {phases.map((phase, pIdx) => (
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

          <GlassPanel className="p-6 border-white/5 relative overflow-hidden">
            <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-1.5">
              <Github size={12} /> Proof Project Engine
            </h2>

            <div className="space-y-3">
              {proofProjects.slice(0, 3).map((project) => (
                <div key={project.id} className="p-3 rounded-lg bg-slate-950/60 border border-white/5">
                  <p className="text-[9px] text-primary-400 font-bold uppercase tracking-wider">{project.title}</p>
                  <p className="text-[8px] text-slate-400 uppercase leading-normal mt-1">{project.resume_headline}</p>
                  <p className="text-[7px] text-slate-500 uppercase leading-normal mt-2">{project.demo_expectations}</p>
                </div>
              ))}
            </div>
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

          <GlassPanel className="p-6 border-white/5 relative overflow-hidden">
            <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-1.5">
              <Network size={12} /> Opportunity Signals
            </h2>

            <div className="space-y-3">
              {repeatedOpportunitySkills.slice(0, 5).map((item) => (
                <div key={item.skill} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-white/5">
                  <span className="text-[8px] text-slate-300 uppercase tracking-wider">{item.skill}</span>
                  <span className="text-[8px] text-primary-400 font-bold">{item.count}x</span>
                </div>
              ))}
              {!repeatedOpportunitySkills.length && (
                <p className="text-[8px] text-slate-500 uppercase leading-normal">
                  Adapter signals will appear after the next Career OS refresh.
                </p>
              )}
            </div>
          </GlassPanel>

          <GlassPanel className="p-6 border-white/5 relative overflow-hidden">
            <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-1.5">
              <ShieldAlert size={12} /> Active Tensions
            </h2>

            <div className="space-y-3">
              {semanticTensions.slice(0, 4).map((tension) => (
                <div key={tension.id} className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/10 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[8px] text-rose-300 font-bold uppercase tracking-wider">{tension.type?.replaceAll('_', ' ')}</span>
                    <span className="text-[7px] text-rose-200 border border-rose-500/20 px-1.5 py-0.5 rounded uppercase">
                      {Math.round((tension.severity || 0) * 100)}%
                    </span>
                  </div>
                  <p className="text-[8px] text-slate-300 uppercase leading-normal">
                    {tension.challenge_question || tension.claim}
                  </p>
                  <p className="text-[7px] text-slate-500 uppercase leading-normal">
                    Market: {tension.market_reality}
                  </p>
                </div>
              ))}
              {!semanticTensions.length && (
                <p className="text-[8px] text-slate-500 uppercase leading-normal">
                  No active contradictions detected. New tensions will appear when market signals challenge the user's assumptions.
                </p>
              )}
            </div>
          </GlassPanel>

          <GlassPanel className="p-6 border-white/5 relative overflow-hidden">
            <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-1.5">
              <Cpu size={12} /> Source Modes
            </h2>

            <div className="space-y-2">
              {sourceStatuses.map((source) => (
                <div key={source.source} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-white/5">
                  <div>
                    <p className="text-[8px] text-slate-300 uppercase tracking-wider">{source.source}</p>
                    <p className="text-[7px] text-slate-500 uppercase">{source.supported_modes?.join(' / ')}</p>
                  </div>
                  <span className={`text-[7px] border px-1.5 py-0.5 rounded uppercase font-bold ${
                    source.mode === 'mock'
                      ? 'text-yellow-400 border-yellow-500/20 bg-yellow-500/10'
                      : 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10'
                  }`}>
                    {source.mode}
                  </span>
                </div>
              ))}
            </div>
          </GlassPanel>

          <GlassPanel className="p-6 border-white/5 relative overflow-hidden">
            <h2 className="text-[10px] font-bold uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-1.5">
              <TrendingUp size={12} /> Journey Until Today
            </h2>

            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-white/5">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[8px] text-cyan-400 font-bold uppercase tracking-wider">Portfolio Assessment</span>
                  <span className="text-[7px] text-slate-500 uppercase">{portfolio.readiness || 'unknown'}</span>
                </div>
                <p className="text-[8px] text-slate-300 uppercase leading-normal">
                  Missing proof: {(portfolio.missing_market_proof || []).slice(0, 3).join(', ') || 'none indexed'}
                </p>
              </div>

              {journey.slice(0, 5).map((event) => (
                <div key={event.id} className="p-3 rounded-lg bg-slate-950/60 border border-white/5">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[8px] text-primary-400 font-bold uppercase tracking-wider">{event.event_type.replaceAll('_', ' ')}</span>
                    <span className="text-[7px] text-slate-500 uppercase">{event.event_date}</span>
                  </div>
                  <p className="text-[8px] text-slate-300 uppercase leading-normal">{event.summary}</p>
                </div>
              ))}

              {!journey.length && (
                <div className="p-3 rounded-lg bg-slate-950/60 border border-white/5 text-[8px] uppercase text-slate-500 leading-normal">
                  No journey events indexed yet. Complete onboarding or verify a milestone to begin the log.
                </div>
              )}
            </div>
          </GlassPanel>
        </div>

      </div>
    </div>
  );
}
