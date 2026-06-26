import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Award,
  BookOpen,
  Calendar as CalendarIcon,
  CheckCircle,
  Cpu,
  ExternalLink,
  FileText,
  Github,
  Network,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import GlassPanel from '../components/ui/GlassPanel';
import { usersAPI, briefsAPI, calendarAPI, dossierAPI, careerOSAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';
import ResumeSection from './ResumeSection';

const views = [
  { id: 'focus', label: 'Focus' },
  { id: 'roadmap', label: 'Roadmap' },
  { id: 'memory', label: 'Memory' },
  { id: 'resume', label: 'Resume' },
];

const emptyDossier = {
  performance_metrics: { habits_consistency_percentage: 0 },
  hiring_market_snapshot: {
    salary_trend_range: 'Unknown',
    bangalore_pune_demand: 'Market pulse pending',
  },
  critique: { keep_doing: [], mistakes_to_avoid: [] },
};

function cx(...parts) {
  return parts.filter(Boolean).join(' ');
}

function formatLabel(value) {
  return String(value || 'unknown').replaceAll('_', ' ');
}

function formatINR(value) {
  return String(value || '').replace('â‚¹', 'INR').replace('₹', 'INR');
}

function Panel({ children, className = '' }) {
  return (
    <GlassPanel hover={false} className={cx('p-5 rounded-lg border-white/5', className)}>
      {children}
    </GlassPanel>
  );
}

function SectionTitle({ icon: Icon, title, meta }) {
  return (
    <div className="flex items-center justify-between gap-3 mb-4">
      <h2 className="text-[11px] font-bold uppercase tracking-widest text-slate-300 flex items-center gap-2">
        <Icon size={13} className="text-cyan-400" />
        {title}
      </h2>
      {meta && <span className="text-[10px] text-slate-500 uppercase tracking-wider">{meta}</span>}
    </div>
  );
}

function Metric({ label, value, detail, tone = 'text-white' }) {
  return (
    <Panel className="min-h-[104px]">
      <p className="text-[10px] uppercase tracking-widest text-slate-500">{label}</p>
      <p className={cx('mt-2 text-2xl font-black tracking-tight', tone)}>{value}</p>
      {detail && <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{detail}</p>}
    </Panel>
  );
}

function EmptyLine({ children }) {
  return (
    <div className="py-4 text-[11px] leading-relaxed text-slate-500">
      {children}
    </div>
  );
}

function StatusPill({ children, tone = 'cyan' }) {
  const tones = {
    cyan: 'border-cyan-500/20 bg-cyan-500/10 text-cyan-300',
    emerald: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    amber: 'border-amber-500/20 bg-amber-500/10 text-amber-300',
    rose: 'border-rose-500/20 bg-rose-500/10 text-rose-300',
    slate: 'border-white/10 bg-white/5 text-slate-300',
  };

  return (
    <span className={cx('inline-flex items-center rounded border px-2 py-1 text-[10px] font-bold uppercase tracking-wider', tones[tone])}>
      {children}
    </span>
  );
}

function Row({ children, className = '' }) {
  return (
    <div className={cx('border-t border-white/5 py-3 first:border-t-0 first:pt-0 last:pb-0', className)}>
      {children}
    </div>
  );
}

export default function Dashboard() {
  const userId = useAuthStore((state) => state.userId);
  const [stats, setStats] = useState(null);
  const [brief, setBrief] = useState(null);
  const [events, setEvents] = useState([]);
  const [sourceStatuses, setSourceStatuses] = useState([]);
  const [dossier, setDossier] = useState(emptyDossier);
  const [careerContext, setCareerContext] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [activeView, setActiveView] = useState('focus');
  const [refreshing, setRefreshing] = useState(false);
  const [consolidating, setConsolidating] = useState(false);
  const [checkedActions, setCheckedActions] = useState({});
  const [resolverAnswers, setResolverAnswers] = useState({});
  const [submittedAnswers, setSubmittedAnswers] = useState({});
  const [selectedNode, setSelectedNode] = useState(null);
  const [githubUrl, setGithubUrl] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [resumeSuggestionsDue, setResumeSuggestionsDue] = useState(false);

  const fetchBrief = useCallback(async () => {
    try {
      return await briefsAPI.getLatest(userId);
    } catch (err) {
      return briefsAPI.generate(userId);
    }
  }, [userId]);

  const loadData = useCallback(async () => {
    try {
      const [
        statsRes,
        briefRes,
        calendarRes,
        sourceRes,
        dossierRes,
        contextRes,
        statusRes,
      ] = await Promise.all([
        usersAPI.getStats(userId),
        fetchBrief(),
        calendarAPI.getEvents(userId).catch(() => []),
        calendarAPI.getSources().catch(() => []),
        dossierAPI.getWeekly(userId).catch(() => emptyDossier),
        careerOSAPI.getContext(userId),
        careerOSAPI.getSystemStatus().catch(() => null),
      ]);

      setStats(statsRes);
      setBrief(briefRes);
      setEvents(Array.isArray(calendarRes) ? calendarRes : []);
      setSourceStatuses(Array.isArray(sourceRes) ? sourceRes : []);
      setDossier(dossierRes || emptyDossier);
      setCareerContext(contextRes);
      setSystemStatus(statusRes);
    } catch (err) {
      console.error(err);
      toast.error('Dashboard sync failed.');
    }
  }, [fetchBrief, userId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // After a single task toggle / answer, only stats and context can change —
  // refresh just those two instead of re-firing all 7 dashboard calls.
  const refreshDerived = useCallback(async () => {
    const [statsRes, contextRes] = await Promise.all([
      usersAPI.getStats(userId).catch(() => null),
      careerOSAPI.getContext(userId).catch(() => null),
    ]);
    if (statsRes) setStats(statsRes);
    if (contextRes) setCareerContext(contextRes);
  }, [userId]);

  const playBeep = useCallback((freq = 800, type = 'sine', duration = 0.08) => {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContext();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.type = type;
      oscillator.frequency.value = freq;
      gainNode.gain.setValueAtTime(0.03, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
      oscillator.start(audioCtx.currentTime);
      oscillator.stop(audioCtx.currentTime + duration);
    } catch (err) {
      console.warn('Audio feedback unavailable:', err);
    }
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const refreshedContext = await careerOSAPI.getContext(userId);
      setCareerContext(refreshedContext);
      await loadData();
      toast.success('Career OS refreshed.');
    } catch (err) {
      console.error(err);
      await loadData();
      toast.error('Refresh completed with partial sync.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleConsolidateMemory = async () => {
    setConsolidating(true);
    try {
      const context = await careerOSAPI.consolidateMemory(userId);
      setCareerContext(context);
      await loadData();
      const report = context.memory_consolidation || {};
      toast.success(`Memory consolidated. ${report.merged_nodes || 0} duplicates merged.`);
    } catch (err) {
      console.error(err);
      toast.error('Memory consolidation failed.');
    } finally {
      setConsolidating(false);
    }
  };

  const toggleAction = useCallback(async (idx) => {
    const actionText = brief?.actions?.[idx];
    if (!actionText) return;

    playBeep(900, 'triangle', 0.1);
    const completed = !checkedActions[idx];
    setCheckedActions((prev) => ({ ...prev, [idx]: completed }));

    try {
      await careerOSAPI.logJourneyEvent(userId, {
        event_type: completed ? 'task_completed' : 'task_reopened',
        summary: `${completed ? 'Completed' : 'Reopened'} action item: "${actionText}"`,
        evidence: { action: actionText, index: idx, completed },
        impact: { progress_updated: true },
      });
      await refreshDerived();
    } catch (err) {
      console.error(err);
    }
  }, [brief, checkedActions, refreshDerived, playBeep, userId]);

  const submitAnswer = useCallback(async (idx, question) => {
    const answer = resolverAnswers[idx]?.trim();
    if (!answer) return;

    playBeep(1200, 'sine', 0.16);
    setSubmittedAnswers((prev) => ({ ...prev, [idx]: true }));

    try {
      await careerOSAPI.logJourneyEvent(userId, {
        event_type: 'user_reflection',
        summary: `Answered profile question: "${question}"`,
        evidence: { question, answer },
        impact: { memory_uncertainty_reduced: true },
      });
      await refreshDerived();
      toast.success('Answer added to journey memory.');
    } catch (err) {
      console.error(err);
    }
  }, [refreshDerived, playBeep, resolverAnswers, userId]);

  const submitMilestone = async (recId, skillName) => {
    if (!githubUrl.trim() || !githubUrl.includes('github.com/')) {
      toast.error('Use a valid github.com repository link.');
      return;
    }

    setVerifying(true);
    toast.loading('Checking proof link...');
    try {
      await briefsAPI.completeRecommendation(recId, {
        evidence_url: githubUrl.trim(),
        evidence_type: 'github',
      });
      toast.dismiss();
      toast.success(`Proof verified for ${skillName}.`);
      setSelectedNode(null);
      setGithubUrl('');
      await loadData();
    } catch (err) {
      console.error(err);
      toast.dismiss();
      toast.error('Proof verification failed.');
    } finally {
      setVerifying(false);
    }
  };

  const derived = useMemo(() => {
    if (!brief || !careerContext || !stats) return null;

    const roadmap = careerContext.roadmap || {};
    const memory = careerContext.memory || {};
    const semanticMemory = careerContext.semantic_memory || {};
    const market = careerContext.market || {};
    const phases = roadmap.phases?.length ? roadmap.phases : brief.phases || [];
    const nodes = phases.flatMap((phase, phaseIndex) =>
      (phase.nodes || []).map((node) => ({ ...node, phaseIndex, phaseName: phase.name }))
    );
    const nextNode =
      nodes.find((node) => node.status === 'in_progress') ||
      nodes.find((node) => node.status === 'locked') ||
      nodes[0];
    const proofProjects = careerContext.proof_projects || brief.proof_projects || [];
    const portfolio = careerContext.portfolio_assessment || brief.portfolio_assessment || {};
    const opportunitySignals = careerContext.opportunity_signals || market.raw_data?.opportunity_signals || {};
    const repeatedOpportunitySkills = opportunitySignals.repeated_skills || [];
    const deltaScore = Math.round(brief.delta_score_end ?? brief.delta_score_start ?? 0);

    return {
      roadmap,
      memory,
      semanticMemory,
      market,
      phases,
      nextNode,
      proofProjects,
      portfolio,
      repeatedOpportunitySkills,
      deltaScore,
      targetRole: memory.ambitions?.target_role || market.target_role || 'Career-ready professional',
      hoursPerWeek: memory.constraints?.hours_per_week || stats.hours_per_week || 10,
      alignment: Math.round((stats.role_alignment || 0) * 100),
      weeklyActions: brief.actions || [],
      questions: brief.questions_for_user || [],
      activePhase: phases.find((phase) => phase.id === roadmap.active_phase_id),
      semanticSummary: semanticMemory.summary || {},
      semanticTensions: semanticMemory.active_tensions || [],
      semanticSession: semanticMemory.latest_ingestion_session || {},
      semanticNodes: semanticMemory.recent_nodes || [],
      dimensionBalance: semanticMemory.dimension_balance || {},
      modules: systemStatus?.modules || {},
    };
  }, [brief, careerContext, stats, systemStatus]);

  if (!stats || !brief || !careerContext || !derived) {
    return (
      <div className="min-h-screen pt-24 px-6 flex flex-col items-center justify-center bg-grid-pattern text-slate-400 font-mono">
        <Cpu className="animate-spin text-cyan-400 mb-4" size={32} />
        <h1 className="text-lg font-black uppercase tracking-widest text-white">Loading Career OS</h1>
        <p className="text-[11px] text-slate-500 mt-2">Dashboard sync in progress</p>
      </div>
    );
  }

  const {
    phases,
    nextNode,
    proofProjects,
    portfolio,
    repeatedOpportunitySkills,
    deltaScore,
    targetRole,
    hoursPerWeek,
    alignment,
    weeklyActions,
    questions,
    activePhase,
    semanticSummary,
    semanticTensions,
    semanticSession,
    semanticNodes,
    dimensionBalance,
    modules,
  } = derived;

  const primaryProject = proofProjects[0];
  const primaryTension = semanticTensions[0];
  const topEvents = events.slice(0, 4);
  const topJourney = (careerContext.journey_until_today || []).slice(0, 5);
  const consistency = dossier?.performance_metrics?.habits_consistency_percentage ?? 0;
  const readiness = portfolio.readiness || 'unknown';

  return (
    <div className="min-h-screen pt-20 px-4 sm:px-6 max-w-7xl mx-auto pb-12 text-slate-200 font-mono selection:bg-cyan-500/20">
      <header className="mb-6 flex flex-col gap-5 border-b border-white/5 pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-400">Delta Career OS</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-white">Dashboard</h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            {targetRole}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {views.map((view) => (
            <button
              key={view.id}
              onClick={() => setActiveView(view.id)}
              className={cx(
                'relative rounded-md border px-3 py-2 text-[11px] font-bold uppercase tracking-wider transition-colors',
                activeView === view.id
                  ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200'
                  : 'border-white/10 bg-white/[0.03] text-slate-400 hover:text-white'
              )}
            >
              {view.label}
              {view.id === 'resume' && resumeSuggestionsDue && (
                <span className="absolute -right-1.5 -top-1.5 flex h-2.5 w-2.5 rounded-full bg-cyan-400" />
              )}
            </button>
          ))}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-300 transition-colors hover:text-white disabled:opacity-50"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </header>

      <section className="mb-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Delta Score" value={deltaScore} detail={`${alignment}% aligned with target role`} tone="text-cyan-300" />
        <Metric label="Weekly Capacity" value={`${hoursPerWeek}h`} detail={`${consistency}% consistency indexed`} tone="text-emerald-300" />
        <Metric label="Portfolio" value={readiness} detail={(portfolio.missing_market_proof || []).slice(0, 2).join(', ') || 'proof stack stable'} tone="text-white" />
        <Metric label="OS Status" value={systemStatus?.status || 'syncing'} detail={`${semanticSummary.total_nodes || 0} memory nodes`} tone="text-emerald-300" />
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_1.55fr_.95fr]">
        <aside className="space-y-6">
          <Panel>
            <SectionTitle icon={Target} title="Current Sprint" meta={activePhase?.name || 'active'} />
            {nextNode ? (
              <div className="space-y-4">
                <div>
                  <p className="text-[11px] uppercase tracking-widest text-slate-500">Next checkpoint</p>
                  <h3 className="mt-1 text-lg font-black text-white">{nextNode.label}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{nextNode.description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusPill tone={nextNode.status === 'mastered' ? 'emerald' : 'cyan'}>
                    {formatLabel(nextNode.status)}
                  </StatusPill>
                  {nextNode.certification && <StatusPill tone="slate">certification mapped</StatusPill>}
                </div>
                <button
                  onClick={() => {
                    setSelectedNode(nextNode);
                    setActiveView('roadmap');
                  }}
                  className="inline-flex items-center gap-2 rounded-md border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-cyan-200 transition-colors hover:border-cyan-400/50"
                >
                  <BookOpen size={13} />
                  Open checkpoint
                </button>
              </div>
            ) : (
              <EmptyLine>No roadmap checkpoint is active yet.</EmptyLine>
            )}
          </Panel>

          <Panel>
            <SectionTitle icon={Github} title="Proof To Ship" meta={readiness} />
            {primaryProject ? (
              <div className="space-y-3">
                <h3 className="text-base font-black text-white">{primaryProject.title}</h3>
                <p className="text-sm leading-relaxed text-slate-400">{primaryProject.resume_headline}</p>
                <Row>
                  <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Demo bar</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-300">{primaryProject.demo_expectations}</p>
                </Row>
                {primaryProject.market_signal && (
                  <Row>
                    <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Market signal</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-300">{primaryProject.market_signal}</p>
                  </Row>
                )}
              </div>
            ) : (
              <EmptyLine>No proof project is assigned yet.</EmptyLine>
            )}
          </Panel>
        </aside>

        <main className="space-y-6">
          <Panel className="min-h-[520px]">
            <AnimatePresence mode="wait">
              {activeView === 'focus' && (
                <motion.div key="focus" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                  <SectionTitle icon={CheckCircle} title="This Week" meta={`${weeklyActions.length} actions`} />
                  <div className="space-y-0">
                    {weeklyActions.slice(0, 6).map((action, idx) => {
                      const complete = !!checkedActions[idx];
                      return (
                        <Row key={`${action}-${idx}`}>
                          <button
                            onClick={() => toggleAction(idx)}
                            className="group flex w-full items-start gap-3 text-left"
                          >
                            <span className={cx(
                              'mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded border transition-colors',
                              complete
                                ? 'border-emerald-400 bg-emerald-400 text-slate-950'
                                : 'border-slate-700 text-transparent group-hover:border-cyan-400'
                            )}>
                              <CheckCircle size={13} />
                            </span>
                            <span className={cx('text-sm leading-relaxed', complete ? 'text-slate-500 line-through' : 'text-slate-200')}>
                              {action}
                            </span>
                          </button>
                        </Row>
                      );
                    })}
                    {!weeklyActions.length && <EmptyLine>No weekly actions generated yet.</EmptyLine>}
                  </div>

                  <div className="mt-8 grid gap-6 lg:grid-cols-2">
                    <div>
                      <SectionTitle icon={Sparkles} title="Open Questions" meta={`${questions.length} pending`} />
                      {questions.slice(0, 3).map((question, idx) => {
                        const submitted = !!submittedAnswers[idx];
                        return (
                          <Row key={`${question}-${idx}`}>
                            <p className="text-sm leading-relaxed text-slate-300">{question}</p>
                            {submitted ? (
                              <p className="mt-2 text-[11px] font-bold uppercase tracking-wider text-emerald-300">Synced</p>
                            ) : (
                              <div className="mt-3 flex gap-2">
                                <input
                                  value={resolverAnswers[idx] || ''}
                                  onChange={(event) => setResolverAnswers((prev) => ({ ...prev, [idx]: event.target.value }))}
                                  className="min-w-0 flex-1 rounded-md border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-white outline-none transition-colors focus:border-cyan-400"
                                  placeholder="Short answer"
                                />
                                <button
                                  onClick={() => submitAnswer(idx, question)}
                                  className="rounded-md bg-cyan-500 px-3 py-2 text-[11px] font-black uppercase tracking-wider text-slate-950"
                                >
                                  Save
                                </button>
                              </div>
                            )}
                          </Row>
                        );
                      })}
                      {!questions.length && <EmptyLine>No open questions.</EmptyLine>}
                    </div>

                    <div>
                      <SectionTitle icon={ShieldAlert} title="Reality Check" meta={primaryTension ? 'active' : 'clear'} />
                      {primaryTension ? (
                        <div className="space-y-3">
                          <StatusPill tone="rose">{formatLabel(primaryTension.type)}</StatusPill>
                          <p className="text-sm leading-relaxed text-slate-300">
                            {primaryTension.challenge_question || primaryTension.claim}
                          </p>
                          <p className="text-xs leading-relaxed text-slate-500">
                            {primaryTension.market_reality}
                          </p>
                        </div>
                      ) : (
                        <EmptyLine>No active market contradiction.</EmptyLine>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}

              {activeView === 'roadmap' && (
                <motion.div key="roadmap" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                  <SectionTitle icon={BookOpen} title="Roadmap" meta={activePhase?.name || 'phase map'} />
                  <div className="space-y-5">
                    {phases.map((phase, phaseIndex) => (
                      <section key={phase.id || phase.name} className="border-t border-white/5 pt-5 first:border-t-0 first:pt-0">
                        <div className="mb-3 flex items-start justify-between gap-4">
                          <div>
                            <p className="text-[10px] uppercase tracking-widest text-slate-500">Phase {phaseIndex + 1}</p>
                            <h3 className="mt-1 text-base font-black text-white">{phase.name}</h3>
                            <p className="mt-1 text-xs leading-relaxed text-slate-500">{phase.description}</p>
                          </div>
                          {phase.id === derived.roadmap.active_phase_id && <StatusPill tone="cyan">active</StatusPill>}
                        </div>

                        <div className="grid gap-2 md:grid-cols-2">
                          {(phase.nodes || []).map((node) => (
                            <button
                              key={node.id}
                              onClick={() => setSelectedNode({ ...node, phaseIndex, phaseName: phase.name })}
                              className="rounded-md border border-white/10 bg-white/[0.02] p-3 text-left transition-colors hover:border-cyan-400/40"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <span className="text-sm font-bold text-white">{node.label}</span>
                                <StatusPill tone={node.status === 'mastered' ? 'emerald' : node.status === 'locked' ? 'slate' : 'cyan'}>
                                  {formatLabel(node.status)}
                                </StatusPill>
                              </div>
                              <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-500">{node.description}</p>
                            </button>
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                </motion.div>
              )}

              {activeView === 'resume' && (
                <motion.div key="resume" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                  <div className="mb-4 flex items-center gap-2">
                    <FileText size={13} className="text-cyan-400" />
                    <h2 className="text-[11px] font-bold uppercase tracking-widest text-slate-300">Resume</h2>
                  </div>
                  <ResumeSection />
                </motion.div>
              )}

              {activeView === 'memory' && (
                <motion.div key="memory" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <SectionTitle icon={Network} title="Memory Core" meta={`${semanticSummary.total_nodes || 0} nodes`} />
                    <button
                      onClick={handleConsolidateMemory}
                      disabled={consolidating}
                      className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-300 transition-colors hover:text-white disabled:opacity-50"
                    >
                      <RefreshCw size={13} className={consolidating ? 'animate-spin' : ''} />
                      Consolidate
                    </button>
                  </div>

                  <div className="grid gap-6 lg:grid-cols-2">
                    <div>
                      {['cognitive', 'emotional', 'temporal', 'social'].map((dimension) => (
                        <Row key={dimension}>
                          <div className="mb-2 flex items-center justify-between">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{dimension}</span>
                            <span className="text-xs text-slate-500">{dimensionBalance[dimension] || 0}%</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded bg-slate-950">
                            <div
                              className="h-full rounded bg-cyan-400"
                              style={{ width: `${Math.min(dimensionBalance[dimension] || 0, 100)}%` }}
                            />
                          </div>
                        </Row>
                      ))}
                    </div>

                    <div>
                      <Row>
                        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Latest ingestion</p>
                        <p className="mt-1 text-sm text-slate-300">
                          {semanticSession.status
                            ? `${semanticSession.status} / round ${semanticSession.current_round || 0} / ${Math.round((semanticSession.confidence_score || 0) * 100)}%`
                            : 'No ingestion session indexed'}
                        </p>
                      </Row>
                      <Row>
                        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Recent nodes</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {semanticNodes.slice(0, 8).map((node) => (
                            <StatusPill key={node.id} tone="slate">{node.label}</StatusPill>
                          ))}
                          {!semanticNodes.length && <span className="text-xs text-slate-500">No nodes indexed.</span>}
                        </div>
                      </Row>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </Panel>
        </main>

        <aside className="space-y-6">
          <Panel>
            <SectionTitle icon={TrendingUp} title="Market Pulse" meta={topEvents.length ? `${topEvents.length} live` : 'queued'} />
            {topEvents.map((event, idx) => (
              <Row key={event.external_id || event.title || idx}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-widest text-cyan-400">{event.platform}</p>
                    <p className="mt-1 text-sm font-bold leading-relaxed text-white">{event.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">
                      {(event.recommended_skills || []).slice(0, 3).join(', ') || 'skills pending'}
                    </p>
                  </div>
                  <StatusPill tone={event.recommended ? 'emerald' : 'slate'}>{event.match_percentage || 0}%</StatusPill>
                </div>
                {event.url && (
                  <a href={event.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-cyan-300">
                    Open <ExternalLink size={11} />
                  </a>
                )}
              </Row>
            ))}
            {!topEvents.length && <EmptyLine>No calendar signals loaded.</EmptyLine>}
          </Panel>

          <Panel>
            <SectionTitle icon={Award} title="Opportunity Skills" meta={`${repeatedOpportunitySkills.length} signals`} />
            <div className="flex flex-wrap gap-2">
              {repeatedOpportunitySkills.slice(0, 8).map((item) => (
                <StatusPill key={item.skill} tone="slate">{item.skill} {item.count}x</StatusPill>
              ))}
            </div>
            {!repeatedOpportunitySkills.length && <EmptyLine>No repeated signals yet.</EmptyLine>}
          </Panel>

          <Panel>
            <SectionTitle icon={CalendarIcon} title="Journey" meta={topJourney.length ? 'latest' : 'empty'} />
            <Row>
              <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Hiring range</p>
              <p className="mt-1 text-sm text-slate-300">{formatINR(dossier?.hiring_market_snapshot?.salary_trend_range)}</p>
            </Row>
            {topJourney.map((event) => (
              <Row key={event.id}>
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm leading-relaxed text-slate-300">{event.summary}</p>
                  <span className="text-[10px] uppercase tracking-wider text-slate-600">{event.event_date}</span>
                </div>
              </Row>
            ))}
            {!topJourney.length && <EmptyLine>No journey events yet.</EmptyLine>}
          </Panel>

          <Panel>
            <SectionTitle icon={Cpu} title="System" meta={systemStatus?.status || 'syncing'} />
            {Object.entries(modules).map(([name, module]) => (
              <Row key={name}>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{formatLabel(name)}</span>
                  <StatusPill tone={module.ready ? 'emerald' : 'rose'}>{module.ready ? 'ready' : 'offline'}</StatusPill>
                </div>
              </Row>
            ))}
            {sourceStatuses.length > 0 && (
              <Row>
                <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Sources</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">
                  {sourceStatuses.map((source) => `${source.source}:${source.mode}`).join(' / ')}
                </p>
              </Row>
            )}
          </Panel>
        </aside>
      </div>

      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 py-8 backdrop-blur"
          >
            <motion.div
              initial={{ scale: 0.96, y: 16 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.96, y: 16 }}
              className="max-h-full w-full max-w-2xl overflow-y-auto rounded-lg border border-white/10 bg-slate-950 p-6 shadow-2xl"
            >
              <div className="mb-5 flex items-start justify-between gap-4">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-widest text-cyan-400">
                    {selectedNode.phaseName || `Phase ${(selectedNode.phaseIndex || 0) + 1}`}
                  </p>
                  <h2 className="mt-1 text-2xl font-black text-white">{selectedNode.label}</h2>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="rounded-md border border-white/10 bg-white/[0.03] p-2 text-slate-400 hover:text-white"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-5">
                <p className="text-sm leading-relaxed text-slate-300">{selectedNode.description}</p>
                {selectedNode.tech_twist && (
                  <Row>
                    <p className="text-[11px] font-bold uppercase tracking-widest text-cyan-400">Tech twist</p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-300">{selectedNode.tech_twist}</p>
                  </Row>
                )}
                {selectedNode.architect_warning && (
                  <Row>
                    <p className="text-[11px] font-bold uppercase tracking-widest text-amber-300">Warning</p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-300">{selectedNode.architect_warning}</p>
                  </Row>
                )}
                {selectedNode.certification && (
                  <Row>
                    <p className="text-[11px] font-bold uppercase tracking-widest text-emerald-300">Credential</p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-300">{selectedNode.certification}</p>
                  </Row>
                )}

                <Row>
                  <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Proof link</p>
                  {(() => {
                    const rec = brief.recommendation_items?.find((item) => {
                      const skill = item.skill?.toLowerCase();
                      const label = selectedNode.label?.toLowerCase();
                      return skill && label && (skill === label || selectedNode.id?.toLowerCase().includes(skill));
                    });

                    if (!rec) {
                      return <p className="mt-2 text-sm text-slate-500">No active proof checkpoint for this node.</p>;
                    }

                    if (rec.status === 'completed') {
                      return (
                        <p className="mt-2 inline-flex items-center gap-2 text-sm font-bold text-emerald-300">
                          <CheckCircle size={14} />
                          Verified
                        </p>
                      );
                    }

                    return (
                      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                        <input
                          value={githubUrl}
                          onChange={(event) => setGithubUrl(event.target.value)}
                          disabled={verifying}
                          className="min-w-0 flex-1 rounded-md border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-cyan-400"
                          placeholder="https://github.com/user/project"
                        />
                        <button
                          onClick={() => submitMilestone(rec.id, rec.skill)}
                          disabled={verifying}
                          className="rounded-md bg-cyan-500 px-4 py-2 text-xs font-black uppercase tracking-wider text-slate-950 disabled:opacity-50"
                        >
                          {verifying ? 'Checking' : 'Verify'}
                        </button>
                      </div>
                    );
                  })()}
                </Row>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
