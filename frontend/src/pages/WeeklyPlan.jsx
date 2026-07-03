import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { CalendarDays, Check, Loader2, RefreshCw, Send, MessageSquare, Clock, BookOpen, Bell, X, Pencil, Plus, Trash2, ThumbsUp, ThumbsDown } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { careerOSAPI } from '../lib/api';
import { getTaskProgress } from '../lib/taskProgress';
import { useReminder, requestNotificationPermission } from '../lib/useReminder';
import { useAuthStore } from '../store/authStore';
import { useAgent2Chat } from '../store/agent2ChatStore';
import { seedCareerContext } from '../hooks/useCareerOS';

const panelStyle = {
  background: 'var(--paper)',
  border: '1px solid var(--rule)',
  borderRadius: 0,
};

const fallbackActions = [
  { title: 'Confirm this week\'s availability', detail: 'Tell Agent 2 your realistic hours, exam pressure, and blocked days before it assigns heavy work.' },
  { title: 'Pick one proof task', detail: 'Choose a small project, course module, paper, or revision block that can be finished this week.' },
  { title: 'Report pace at week end', detail: 'Mark what was completed so Agent 2 can decide whether to increase, repeat, or pause next week.' },
];

const SUGGESTIONS = [
  'I have an exam next week, slow down',
  'These tasks are too hard for me right now',
  'I finished everything ahead of schedule',
  'What should I focus on first this week?',
];

export default function WeeklyPlan() {
  const userId = useAuthStore((state) => state.userId);
  const queryClient = useQueryClient();
  const location = useLocation();
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [checked, setChecked] = useState({});
  const [skipped, setSkipped] = useState({});
  const [chatOpen, setChatOpen] = useState(false);
  // Agent 2 chat state lives in a shared store so the thread and any in-flight
  // reply persist across navigating away from this page and back.
  const messages = useAgent2Chat((s) => s.messages);
  const sending = useAgent2Chat((s) => s.sending);
  const historyLoaded = useAgent2Chat((s) => s.historyLoaded);
  const loadingHistory = useAgent2Chat((s) => s.loadingHistory);
  const ensureAgent2User = useAgent2Chat((s) => s.ensureUser);
  const sendAgent2 = useAgent2Chat((s) => s.send);
  const resetAgent2Chat = useAgent2Chat((s) => s.reset);
  const loadAgent2History = useAgent2Chat((s) => s.loadHistory);
  const [input, setInput] = useState('');
  const [notifPermission, setNotifPermission] = useState(
    'Notification' in window ? Notification.permission : 'unsupported'
  );

  // Context docs (permanent rules + next-week requests)
  const [contextDocs, setContextDocs] = useState({ permanent: [], next_week: [] });
  const [docsLoading, setDocsLoading] = useState(false);
  const [newPermanent, setNewPermanent] = useState('');
  const [newNextWeek, setNewNextWeek] = useState('');
  const [newNextWeekWeeks, setNewNextWeekWeeks] = useState(1);

  // Task editing
  const [editingTasks, setEditingTasks] = useState(false);
  const [editableTasks, setEditableTasks] = useState([]);
  const [savingTasks, setSavingTasks] = useState(false);

  // Task feedback
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');

  // Skip dialog
  const [skipDialog, setSkipDialog] = useState(null); // {action, index}

  const bottomRef = useRef(null);

  const loadContext = useCallback(async (regenerate = false) => {
    setLoading(true);
    try {
      const data = await careerOSAPI.getContext(userId);
      setContext(data);
      seedCareerContext(queryClient, userId, data);
      const progress = getTaskProgress(data, fallbackActions);
      setChecked(progress.checkedByIndex);
      setSkipped(progress.skippedByIndex);
      if (regenerate) toast.success('Agent 2 loaded your first weekly plan.');
    } catch (err) {
      console.error(err);
      toast.error('Unable to load Agent 2 plan. Using a safe starter week.');
    } finally {
      setLoading(false);
    }
  }, [userId, queryClient]);

  // Bind the shared Agent 2 thread to the current user (resets only when the
  // user changes). Past conversation is loaded lazily via a button, not here —
  // so the chat opens instantly instead of blocking on a history fetch.
  useEffect(() => {
    if (userId) ensureAgent2User(userId);
  }, [userId, ensureAgent2User]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    loadContext(params.get('from') === 'intake');
  }, [loadContext, location.search]);

  useEffect(() => {
    setDocsLoading(true);
    careerOSAPI.getContextDocs(userId)
      .then(data => setContextDocs(data || { permanent: [], next_week: [] }))
      .catch(() => toast.error('Could not load your saved preferences.'))
      .finally(() => setDocsLoading(false));
  }, [userId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setChatOpen(false); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const memory = context?.memory || {};
  const roadmap = context?.roadmap || {};
  const weeklyFocus = useMemo(() => roadmap.weekly_focus || {}, [roadmap.weekly_focus]);
  const studentName = memory.identity_context?.name || memory.identity?.name || 'Student';
  const educationStage = memory.identity_context?.education_stage || memory.identity?.education_stage || 'Profile building';
  const targetRole = memory.ambitions?.target_role || roadmap.destination?.target_role || 'your goal';
  const hoursPerWeek = memory.constraints?.hours_per_week || 10;
  const longHorizonPlan = roadmap.destination?.long_horizon_plan || {};
  const longHorizonLanes = longHorizonPlan.lanes || weeklyFocus.long_horizon_lanes || [];
  const opportunities = context?.opportunities || [];
  const nextQuestions = context?.next_questions || [];

  const actions = useMemo(() => getTaskProgress(context, fallbackActions).actions, [context]);

  useReminder(actions, checked);

  const refreshWeek = async () => {
    setRefreshing(true);
    try {
      const data = await careerOSAPI.getContext(userId);
      setContext(data);
      seedCareerContext(queryClient, userId, data);
      const progress = getTaskProgress(data, fallbackActions);
      setChecked(progress.checkedByIndex);
      setSkipped(progress.skippedByIndex);
      toast.success('Refreshed this week\'s plan.');
    } catch (err) {
      console.error(err);
      toast.error('Could not refresh the week right now.');
    } finally {
      setRefreshing(false);
    }
  };

  const toggleTask = async (action, index) => {
    if (advancing) return;
    const nextValue = !checked[index];
    setChecked(prev => ({ ...prev, [index]: nextValue }));
    setSkipped(prev => ({ ...prev, [index]: false }));
    try {
      await careerOSAPI.logJourneyEvent(userId, {
        event_type: nextValue ? 'weekly_task_completed' : 'weekly_task_reopened',
        summary: `${nextValue ? 'Completed' : 'Reopened'} Agent 2 task: ${action.title}`,
        evidence: action,
        impact: { weekly_plan_adjustment_needed: true },
      });
    } catch (err) {
      console.error(err);
      setChecked(prev => ({ ...prev, [index]: !nextValue }));
      toast.error('Task saved locally, but could not sync with database.');
    }
  };

  const skipTask = (e, action, index) => {
    e.stopPropagation();
    if (advancing) return;
    setSkipDialog({ action, index });
  };

  const confirmSkip = async (choice) => {
    if (!skipDialog) return;
    const { action, index } = skipDialog;
    setSkipDialog(null);
    setChecked(prev => ({ ...prev, [index]: false }));
    setSkipped(prev => ({ ...prev, [index]: true }));
    try {
      await careerOSAPI.logJourneyEvent(userId, {
        event_type: 'weekly_task_skipped',
        summary: `Skipped Agent 2 task: ${action.title}`,
        evidence: { ...action, skip_choice: choice },
        impact: { user_chose_to_skip: true, disposition: choice },
      });
      if (choice === 'next_week') {
        await appendNextWeekRequestFromSkip(action.title);
        toast.success('Task moved to next week.');
      } else if (choice === 'remove') {
        toast.success('Task permanently removed from your plan.');
      } else {
        toast.success('Task skipped for this week.');
      }
    } catch (err) {
      console.error(err);
      toast.error('Could not save skip.');
    }
  };

  const appendNextWeekRequestFromSkip = async (title) => {
    const updated = {
      ...contextDocs,
      next_week: [...contextDocs.next_week, { text: `Include task: ${title}`, weeks_remaining: 1 }],
    };
    setContextDocs(updated);
    try {
      await careerOSAPI.updateContextDocs(userId, updated);
    } catch { /* non-fatal */ }
  };

  // Core send — accepts text directly so it can be called programmatically.
  // The store owns the message thread + sending flag (so they persist across
  // navigation); here we just build the prompt and apply any task updates.
  const sendMessageText = async (text) => {
    if (!text || sending) return;
    const prompt = `Agent 2 weekly plan discussion. Current weekly actions: ${actions.map(a => a.title).join('; ')}. User update: ${text}`;
    const response = await sendAgent2(userId, text, prompt);
    if (response && Array.isArray(response.updated_actions)) {
      setContext(prev => ({
        ...(prev || {}),
        roadmap: {
          ...((prev || {}).roadmap || {}),
          weekly_focus: {
            ...(((prev || {}).roadmap || {}).weekly_focus || {}),
            primary_actions: response.updated_actions,
            phase_name: response.week_phase || (((prev || {}).roadmap || {}).weekly_focus || {}).phase_name,
          },
        },
      }));
      setChecked({});
      setSkipped({});
    } else {
      // No task change (or the reply failed) — pull fresh context so the page
      // and the server stay in sync. On failure the store already showed an
      // error line, and task changes are persisted server-side regardless.
      await loadContext();
    }
  };

  const sendMessage = async (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput('');
    await sendMessageText(text);
  };

  // "How to do this" — opens Agent 2 and auto-asks about this specific task
  const askAgent2AboutTask = (e, action) => {
    e.stopPropagation();
    const prompt = `How do I complete this task: "${action.title}"? ${action.detail ? action.detail + ' ' : ''}Give me exact step-by-step instructions, the best resources with specific links, how long each will take, and if any course is involved tell me which modules or weeks to focus on this week specifically.`;
    setChatOpen(true);
    // Small delay so drawer is open and visible before the message fires
    setTimeout(() => sendMessageText(prompt), 150);
  };

  const openChatWithSuggestion = (text) => {
    setInput(text);
    setChatOpen(true);
  };

  const saveContextDocs = async (updated) => {
    const next = { ...contextDocs, ...updated };
    setContextDocs(next);
    try {
      await careerOSAPI.updateContextDocs(userId, next);
    } catch { toast.error('Could not save preference.'); }
  };

  const addPermanent = async () => {
    const text = newPermanent.trim();
    if (!text) return;
    setNewPermanent('');
    await saveContextDocs({ permanent: [...contextDocs.permanent, text] });
  };

  const removePermanent = async (i) => {
    await saveContextDocs({ permanent: contextDocs.permanent.filter((_, idx) => idx !== i) });
  };

  const addNextWeek = async () => {
    const text = newNextWeek.trim();
    if (!text) return;
    setNewNextWeek('');
    const weeks = Math.max(1, Math.min(12, Number(newNextWeekWeeks) || 1));
    setNewNextWeekWeeks(1);
    await saveContextDocs({ next_week: [...contextDocs.next_week, { text, weeks_remaining: weeks }] });
  };

  const removeNextWeek = async (i) => {
    await saveContextDocs({ next_week: contextDocs.next_week.filter((_, idx) => idx !== i) });
  };

  const startEditTasks = () => {
    setEditableTasks(actions.map(a => ({ ...a })));
    setEditingTasks(true);
  };

  const saveEditedTasks = async () => {
    setSavingTasks(true);
    try {
      await careerOSAPI.updateWeeklyTasks(userId, editableTasks);
      setContext(prev => ({
        ...(prev || {}),
        roadmap: {
          ...((prev || {}).roadmap || {}),
          weekly_focus: {
            ...(((prev || {}).roadmap || {}).weekly_focus || {}),
            primary_actions: editableTasks,
          },
        },
      }));
      setEditingTasks(false);
      toast.success('Tasks updated.');
    } catch { toast.error('Could not save tasks.'); }
    finally { setSavingTasks(false); }
  };

  const submitFeedback = async () => {
    const text = feedbackText.trim();
    if (!text) return;
    setFeedbackText('');
    setFeedbackOpen(false);
    setChatOpen(true);
    setTimeout(() => sendMessageText(`Feedback on this week's tasks: ${text}`), 150);
  };

  const handleEnableReminders = async (e) => {
    e.stopPropagation();
    const perm = await requestNotificationPermission();
    setNotifPermission(perm);
    if (perm === 'granted') toast.success('Reminders enabled.');
    else if (perm === 'denied') toast.error('Browser blocked notifications. Enable them in browser settings.');
  };

  const requestNextWeek = async () => {
    setAdvancing(true);
    try {
      const data = await careerOSAPI.runWeeklyCycle(userId);
      setContext(data);
      seedCareerContext(queryClient, userId, data);
      const progress = getTaskProgress(data, fallbackActions);
      setChecked(progress.checkedByIndex);
      setSkipped(progress.skippedByIndex);
      resetAgent2Chat('New week loaded. Tell me if anything has changed — exams, pace, priorities.');
      toast.success('Next week loaded — Agent 2 has updated your tasks.');
    } catch (err) {
      console.error(err);
      const detail = err?.response?.data?.detail || err?.message || 'Something went wrong. Try again in a moment.';
      toast.error(detail);
    } finally {
      setAdvancing(false);
    }
  };

  const mdComponents = {
    p: ({ children }) => <p style={{ margin: '0 0 6px 0' }}>{children}</p>,
    ul: ({ children }) => <ul style={{ margin: '4px 0 8px', paddingLeft: 20 }}>{children}</ul>,
    ol: ({ children }) => <ol style={{ margin: '4px 0 8px', paddingLeft: 20 }}>{children}</ol>,
    li: ({ children }) => <li style={{ marginBottom: 4, paddingLeft: 2 }}>{children}</li>,
    strong: ({ children }) => <strong style={{ color: 'var(--ink)', fontWeight: 700 }}>{children}</strong>,
    code: ({ children }) => <code style={{ background: 'var(--rule)', padding: '1px 5px', borderRadius: 0, fontSize: 12 }}>{children}</code>,
    a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer" style={{ color: 'var(--ink)', textDecoration: 'underline' }}>{children}</a>,
    table: ({ children }) => (
      <div style={{ margin: '6px 0', overflowX: 'auto', border: '1px solid var(--rule)', borderRadius: 0 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead style={{ background: 'var(--accent-surface)' }}>{children}</thead>,
    tbody: ({ children }) => <tbody>{children}</tbody>,
    tr: ({ children }) => <tr style={{ borderBottom: '1px solid var(--rule)' }}>{children}</tr>,
    th: ({ children }) => (
      <th style={{ padding: '6px 10px', textAlign: 'left', fontWeight: 700, color: 'var(--ink)', borderRight: '1px solid var(--rule)' }}>{children}</th>
    ),
    td: ({ children }) => (
      <td style={{ padding: '6px 10px', verticalAlign: 'top', color: 'var(--ink-soft)', borderRight: '1px solid var(--rule)' }}>{children}</td>
    ),
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>

        {/* Header */}
        <header style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start', marginBottom: 28 }}>
          <div>
            <p style={{ color: 'var(--ink-soft)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
              Part 2 · Agent 2 roadmap · Week {context?.week_number || 1}
            </p>
            <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontWeight: 500, color: 'var(--oxblood)', fontSize: 'clamp(2rem, 5vw, 3.4rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0, maxWidth: 760 }}>
              {studentName}'s week. Adjusted to your pace.
            </h1>
          </div>
          <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
            {notifPermission !== 'granted' && notifPermission !== 'unsupported' && (
              <button
                onClick={handleEnableReminders}
                style={{
                  background: 'var(--accent-surface)', color: 'var(--ink)',
                  border: '1px solid var(--rule)', borderRadius: 0,
                  padding: '11px 16px', fontWeight: 600, fontSize: 13,
                  display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer',
                }}
              >
                <Bell size={14} /> Reminders
              </button>
            )}
            <button
              onClick={refreshWeek}
              disabled={refreshing || advancing}
              style={{
                background: 'var(--ink)', color: 'var(--bone)', border: 'none', borderRadius: 0,
                padding: '11px 18px', fontWeight: 700,
                display: 'inline-flex', alignItems: 'center', gap: 8,
                cursor: refreshing ? 'not-allowed' : 'pointer',
              }}
            >
              {refreshing || advancing ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={15} />}
              Refresh plan
            </button>
          </div>
        </header>

        {/* Stats bar */}
        <section style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 1, background: 'var(--rule)', border: '1px solid var(--rule)', marginBottom: 24,
        }}>
          {[
            { icon: BookOpen, label: 'Student', value: `${studentName} · ${educationStage}` },
            { icon: BookOpen, label: 'Goal', value: targetRole },
            { icon: Clock, label: 'Available pace', value: `${hoursPerWeek}h / week` },
            { icon: CalendarDays, label: 'Focus', value: weeklyFocus.phase_name || 'First useful week' },
          ].map(item => {
            const Icon = item.icon;
            return (
              <div key={item.label} style={{ background: 'var(--paper)', padding: 18, minHeight: 110 }}>
                <Icon size={17} style={{ color: 'var(--ink)', marginBottom: 14 }} />
                <p style={{ color: 'var(--ink-soft)', margin: '0 0 6px', fontSize: 12 }}>{item.label}</p>
                <p style={{ color: 'var(--ink)', margin: 0, fontSize: 15, lineHeight: 1.4, fontWeight: 650 }}>{item.value}</p>
              </div>
            );
          })}
        </section>

        {/* Long-horizon plan */}
        {longHorizonLanes.length > 0 && (
          <section style={{ ...panelStyle, padding: 20, marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h2 style={{ margin: '0 0 6px', fontSize: 20 }}>Long-scale plan</h2>
                <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.5 }}>
                  Delta keeps these lanes alive across the selected timeline, then chooses the right weekly slice.
                </p>
              </div>
              <span style={{ color: 'var(--ink-soft)', fontSize: 13, whiteSpace: 'nowrap' }}>
                {longHorizonPlan.horizon_months || roadmap.destination?.planning_horizon_months || 12} months
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10 }}>
              {longHorizonLanes.map((lane) => (
                <div key={lane.name} style={{ background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 0, padding: 14 }}>
                  <p style={{ margin: '0 0 6px', color: 'var(--ink)', fontSize: 14, fontWeight: 700 }}>{lane.name}</p>
                  <p style={{ margin: '0 0 8px', color: 'var(--ink-soft)', fontSize: 12 }}>{lane.cadence}</p>
                  <p style={{ margin: 0, color: 'var(--ink)', fontSize: 13, lineHeight: 1.45 }}>{lane.rule}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Tasks */}
        <section style={{ ...panelStyle, padding: 22, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
            <div>
              <h2 style={{ margin: '0 0 8px', fontSize: 24, letterSpacing: 0 }}>Tasks for this week</h2>
              <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.55 }}>
                Agent 2 should only assign new work after these are completed or after you say the plan needs to change.
              </p>
            </div>
            {loading && <Loader2 size={18} style={{ animation: 'spin 1s linear infinite', color: 'var(--ink-soft)' }} />}
          </div>

          {/* Advance progress — one honest status line, not a simulated multi-step sequence */}
          {advancing && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '20px 0' }}>
              <Loader2 size={16} color="var(--ink)" style={{ animation: 'spin 1s linear infinite' }} />
              <span style={{ fontSize: 14, color: 'var(--ink)' }}>
                Agent 2 is preparing your next week — reviewing what you completed, skipped, and any preferences you saved.
              </span>
            </div>
          )}

          {/* Task list */}
          <div style={{ display: advancing ? 'none' : 'grid', gap: 12 }}>
            {actions.map((action, index) => {
              const isDone = !!checked[index];
              const isSkipped = !!skipped[index];
              return (
                <button
                  key={action.id}
                  onClick={() => toggleTask(action, index)}
                  style={{
                    display: 'grid', gridTemplateColumns: '34px minmax(0, 1fr)', gap: 14,
                    textAlign: 'left', width: '100%',
                    background: isDone ? 'var(--rule)' : isSkipped ? 'var(--accent-surface)' : 'var(--paper)',
                    border: '1px solid var(--rule)', borderRadius: 0, padding: 16,
                    color: 'var(--ink)', cursor: advancing ? 'not-allowed' : 'pointer',
                  }}
                >
                  <span style={{
                    width: 28, height: 28, borderRadius: 0,
                    border: '1px solid var(--rule)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: isDone ? 'var(--ink)' : 'transparent', color: 'var(--bone)', flexShrink: 0,
                  }}>
                    {isDone && <Check size={16} />}
                  </span>
                  <span>
                    <span style={{ display: 'block', fontSize: 16, fontWeight: 700, marginBottom: 6, textDecoration: isDone ? 'line-through' : 'none' }}>
                      {action.title}
                      {isSkipped ? <span style={{ marginLeft: 8, color: 'var(--ink-soft)', fontSize: 12 }}>Skipped</span> : null}
                    </span>
                    <span style={{ display: 'block', color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.55 }}>{action.detail}</span>
                    {action.problems?.length > 0 ? (
                      <span style={{ display: 'block', marginTop: 10 }}>
                        <span style={{ color: 'var(--ink-soft)', fontSize: 12, display: 'block', marginBottom: 6 }}>Problems this week:</span>
                        <span style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                          {action.problems.map((p) => (
                            <a
                              key={p.id}
                              href={p.url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              style={{ display: 'inline-flex', alignItems: 'center', gap: 7, textDecoration: 'none', fontSize: 13 }}
                            >
                              <span style={{
                                fontSize: 10, fontWeight: 700, padding: '1px 5px', borderRadius: 0, flexShrink: 0,
                                background: 'var(--accent-surface)', border: '1px solid var(--rule)',
                                color: 'var(--ink-soft)',
                              }}>{p.difficulty}</span>
                              <span style={{ color: 'var(--ink)', textDecoration: 'underline' }}>#{p.id} {p.title}</span>
                            </a>
                          ))}
                        </span>
                      </span>
                    ) : (action.source || action.url) ? (
                      <span style={{ display: 'block', marginTop: 8, color: 'var(--ink-soft)', fontSize: 13 }}>
                        {action.source || 'Resource'}
                        {action.url ? (
                          <> · <a href={action.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} style={{ color: 'var(--ink)', textDecoration: 'underline' }}>Open</a></>
                        ) : null}
                      </span>
                    ) : null}
                    <span style={{ display: 'flex', gap: 14, marginTop: 12, alignItems: 'center' }}>
                      {!isDone && !isSkipped && (
                        <span
                          role="button" tabIndex={0}
                          onClick={(e) => skipTask(e, action, index)}
                          onKeyDown={(e) => { if (e.key === 'Enter') skipTask(e, action, index); }}
                          style={{ color: 'var(--ink-soft)', fontSize: 13, textDecoration: 'underline', cursor: 'pointer' }}
                        >
                          Skip this task
                        </span>
                      )}
                      <span
                        role="button" tabIndex={0}
                        onClick={(e) => askAgent2AboutTask(e, action)}
                        onKeyDown={(e) => { if (e.key === 'Enter') askAgent2AboutTask(e, action); }}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: 5,
                          color: 'var(--ink-soft)', fontSize: 13, cursor: 'pointer',
                        }}
                      >
                        <MessageSquare size={12} /> How to do this
                      </span>
                    </span>
                  </span>
                </button>
              );
            })}
          </div>

          {/* Request next week */}
          {!advancing && actions.length > 0 && actions.every((_, i) => checked[i] || skipped[i]) && (
            <div style={{ marginTop: 20, padding: 16, borderRadius: 0, background: 'var(--accent-surface)', border: '1px solid var(--accent-surface)' }}>
              <p style={{ margin: '0 0 12px', color: 'var(--ink)', fontSize: 14, lineHeight: 1.5 }}>
                <strong>All current tasks are checked.</strong> Request the next week only after you have genuinely finished the work and proof.
              </p>
              <button
                onClick={requestNextWeek}
                disabled={advancing}
                style={{
                  width: '100%', background: 'var(--ink)', color: 'var(--bone)', border: 'none',
                  borderRadius: 0, padding: 14, fontWeight: 700, fontSize: 15,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                  cursor: 'pointer',
                }}
              >
                <Check size={18} /> Request Next Week's Activities
              </button>
            </div>
          )}
        </section>

        {/* Plan Preferences — permanent rules + next-week requests */}
        <section style={{ ...panelStyle, padding: 20, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>Plan Preferences</h2>
              <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 13 }}>
                Permanent rules apply every week · Next week requests carry forward once
              </p>
            </div>
            {docsLoading && <Loader2 size={15} style={{ animation: 'spin 1s linear infinite', color: 'var(--ink-soft)' }} />}
          </div>
          <div className="plan-preferences-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {/* Permanent */}
            <div style={{ background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 0, padding: 14 }}>
              <p style={{ margin: '0 0 10px', fontSize: 13, fontWeight: 700, color: 'var(--ink)' }}>Permanent Rules</p>
              {contextDocs.permanent.length === 0 && (
                <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--ink-soft)' }}>No permanent rules yet. Add one below.</p>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10 }}>
                {contextDocs.permanent.map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, background: 'var(--accent-surface)', borderRadius: 0, padding: '7px 10px' }}>
                    <span style={{ flex: 1, fontSize: 13, color: 'var(--ink)', lineHeight: 1.4 }}>{item}</span>
                    <button onClick={() => removePermanent(i)} aria-label="Remove rule" style={{ background: 'none', border: 'none', color: 'var(--ink-soft)', cursor: 'pointer', padding: 8, flexShrink: 0 }}>
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  value={newPermanent}
                  onChange={e => setNewPermanent(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addPermanent()}
                  placeholder="e.g. Never more than 2 tasks"
                  style={{ flex: 1, background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '7px 10px', color: 'var(--ink)', fontSize: 12, outline: 'none' }}
                />
                <button onClick={addPermanent} style={{ background: 'var(--rule)', border: 'none', borderRadius: 0, padding: '7px 10px', color: 'var(--ink)', cursor: 'pointer' }}>
                  <Plus size={14} />
                </button>
              </div>
            </div>
            {/* Next week requests */}
            <div style={{ background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 0, padding: 14 }}>
              <p style={{ margin: '0 0 10px', fontSize: 13, fontWeight: 700, color: 'var(--ink)' }}>Next Week Requests</p>
              {contextDocs.next_week.length === 0 && (
                <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--ink-soft)' }}>No requests yet. Add one below or tell Agent 2.</p>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10 }}>
                {contextDocs.next_week.map((item, i) => {
                  const text = typeof item === 'string' ? item : item.text;
                  const weeksLeft = typeof item === 'object' ? item.weeks_remaining : 1;
                  return (
                    <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, background: 'var(--accent-surface)', borderRadius: 0, padding: '7px 10px' }}>
                      <span style={{ flex: 1, fontSize: 13, color: 'var(--ink)', lineHeight: 1.4 }}>{text}</span>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 0, background: 'var(--accent-surface)', color: weeksLeft <= 1 ? 'var(--oxblood)' : 'var(--ink-soft)', flexShrink: 0 }}>
                        {weeksLeft}w
                      </span>
                      <button onClick={() => removeNextWeek(i)} aria-label="Remove request" style={{ background: 'none', border: 'none', color: 'var(--ink-soft)', cursor: 'pointer', padding: 8, flexShrink: 0 }}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  );
                })}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  value={newNextWeek}
                  onChange={e => setNewNextWeek(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addNextWeek()}
                  placeholder="e.g. Include a REST API project"
                  style={{ flex: 1, background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '7px 10px', color: 'var(--ink)', fontSize: 12, outline: 'none' }}
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <input
                    type="number"
                    min={1}
                    max={12}
                    value={newNextWeekWeeks}
                    onChange={e => setNewNextWeekWeeks(e.target.value)}
                    title="Number of weeks to keep this instruction active"
                    style={{ width: 44, background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '7px 6px', color: 'var(--ink)', fontSize: 12, outline: 'none', textAlign: 'center' }}
                  />
                  <span style={{ fontSize: 11, color: 'var(--ink-soft)', whiteSpace: 'nowrap' }}>wk</span>
                </div>
                <button onClick={addNextWeek} style={{ background: 'var(--rule)', border: 'none', borderRadius: 0, padding: '7px 10px', color: 'var(--ink)', cursor: 'pointer' }}>
                  <Plus size={14} />
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Task feedback + manual edit */}
        <section style={{ ...panelStyle, padding: 20, marginBottom: 20 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'space-between', alignItems: 'center', marginBottom: editingTasks ? 16 : 0 }}>
            <div>
              <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>Task Controls</h2>
              <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 13 }}>
                Edit tasks manually or give Agent 2 feedback on this week's selection
              </p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => { setFeedbackOpen(o => !o); setEditingTasks(false); }}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--accent-surface)', color: 'var(--ink)', border: '1px solid var(--rule)', borderRadius: 0, padding: '9px 14px', fontSize: 13, cursor: 'pointer', fontWeight: 600 }}
              >
                <ThumbsUp size={13} /> Feedback
              </button>
              <button
                onClick={() => { startEditTasks(); setFeedbackOpen(false); }}
                disabled={editingTasks}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: editingTasks ? 'var(--rule)' : 'var(--ink)', color: editingTasks ? 'var(--ink-soft)' : 'var(--bone)', border: 'none', borderRadius: 0, padding: '9px 14px', fontSize: 13, cursor: editingTasks ? 'not-allowed' : 'pointer', fontWeight: 700 }}
              >
                <Pencil size={13} /> Edit Tasks
              </button>
            </div>
          </div>

          {/* Feedback form */}
          {feedbackOpen && (
            <div style={{ marginTop: 14 }}>
              <p style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--ink-soft)' }}>
                What's wrong with this week's tasks? Agent 2 will adjust based on your feedback.
              </p>
              <textarea
                value={feedbackText}
                onChange={e => setFeedbackText(e.target.value)}
                placeholder="e.g. The LeetCode task is too hard, I'd prefer easier problems. The FastAPI task has no clear goal."
                rows={3}
                style={{ width: '100%', background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '10px 12px', color: 'var(--ink)', fontSize: 13, resize: 'vertical', outline: 'none', boxSizing: 'border-box' }}
              />
              <div style={{ display: 'flex', gap: 8, marginTop: 8, justifyContent: 'flex-end' }}>
                <button onClick={() => setFeedbackOpen(false)} style={{ background: 'none', border: '1px solid var(--rule)', borderRadius: 0, padding: '8px 14px', color: 'var(--ink-soft)', fontSize: 13, cursor: 'pointer' }}>Cancel</button>
                <button onClick={submitFeedback} style={{ background: 'var(--ink)', color: 'var(--bone)', border: 'none', borderRadius: 0, padding: '8px 16px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>Send to Agent 2</button>
              </div>
            </div>
          )}

          {/* Inline task editor */}
          {editingTasks && (
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {editableTasks.map((task, i) => (
                  <div key={i} style={{ background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 0, padding: 12 }}>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                      <input
                        value={task.title || ''}
                        onChange={e => setEditableTasks(prev => prev.map((t, idx) => idx === i ? { ...t, title: e.target.value } : t))}
                        placeholder="Task title"
                        style={{ flex: 1, background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '7px 10px', color: 'var(--ink)', fontSize: 14, fontWeight: 700, outline: 'none' }}
                      />
                      <button onClick={() => setEditableTasks(prev => prev.filter((_, idx) => idx !== i))} aria-label="Remove task" style={{ background: 'none', border: 'none', color: 'var(--ink-soft)', cursor: 'pointer', padding: 8 }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <textarea
                      value={task.detail || task.description || ''}
                      onChange={e => setEditableTasks(prev => prev.map((t, idx) => idx === i ? { ...t, detail: e.target.value, description: e.target.value } : t))}
                      placeholder="Task description"
                      rows={2}
                      style={{ width: '100%', background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '7px 10px', color: 'var(--ink)', fontSize: 13, resize: 'vertical', outline: 'none', boxSizing: 'border-box' }}
                    />
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center' }}>
                <button
                  onClick={() => setEditableTasks(prev => [...prev, { id: `manual-${Date.now()}`, title: '', detail: '', type: 'project' }])}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '8px 12px', color: 'var(--ink)', fontSize: 13, cursor: 'pointer' }}
                >
                  <Plus size={13} /> Add task
                </button>
                <div style={{ flex: 1 }} />
                <button onClick={() => setEditingTasks(false)} style={{ background: 'none', border: '1px solid var(--rule)', borderRadius: 0, padding: '8px 14px', color: 'var(--ink-soft)', fontSize: 13, cursor: 'pointer' }}>Cancel</button>
                <button onClick={saveEditedTasks} disabled={savingTasks} style={{ background: 'var(--ink)', color: 'var(--bone)', border: 'none', borderRadius: 0, padding: '8px 18px', fontSize: 13, fontWeight: 700, cursor: savingTasks ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  {savingTasks ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Check size={13} />}
                  Save
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Agent 2 compact box */}
        <section style={{ ...panelStyle, padding: 20, marginBottom: 20 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div>
              <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>Agent 2</h2>
              <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 13 }}>
                Chat resets each week · DB keeps last 2 weeks for context
              </p>
            </div>
            <button
              onClick={() => setChatOpen(true)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                background: 'var(--ink)', color: 'var(--bone)', border: 'none',
                borderRadius: 0, padding: '10px 16px', fontWeight: 700, fontSize: 13,
                cursor: 'pointer', flexShrink: 0,
              }}
            >
              <MessageSquare size={14} /> Talk to Agent 2
            </button>
          </div>
          <p style={{ margin: '0 0 12px', color: 'var(--ink-soft)', fontSize: 13 }}>Things you can ask:</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {(nextQuestions.length ? nextQuestions.slice(0, 4) : SUGGESTIONS).map((s, i) => (
              <button
                key={i}
                onClick={() => openChatWithSuggestion(s)}
                style={{
                  background: 'var(--accent-surface)', color: 'var(--ink)',
                  border: '1px solid var(--rule)', borderRadius: 0,
                  padding: '7px 14px', fontSize: 13, cursor: 'pointer',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--rule)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--accent-surface)'; }}
              >
                {s}
              </button>
            ))}
          </div>
        </section>

        {/* Opportunities */}
        {opportunities.length > 0 && (
          <section style={{ ...panelStyle, padding: 20 }}>
            <h2 style={{ margin: '0 0 14px', fontSize: 18 }}>Opportunities</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              {opportunities.slice(0, 4).map((item, i) => (
                <div key={i} style={{ background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 0, padding: 14 }}>
                  <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 700 }}>{item.title || item.name}</p>
                  <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 12 }}>
                    {item.platform}{item.match_percentage ? ` · ${item.match_percentage}% match` : ''}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {/* Skip task dialog */}
      {skipDialog && (
        <>
          <div onClick={() => setSkipDialog(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(26,25,24,0.45)', zIndex: 80 }} />
          <div style={{ position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 81, background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 0, padding: 28, width: 'min(90vw, 420px)' }}>
            <p style={{ color: 'var(--ink-soft)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 8px' }}>Skipping task</p>
            <p style={{ color: 'var(--ink)', fontSize: 15, fontWeight: 600, margin: '0 0 20px', lineHeight: 1.4 }}>{skipDialog.action.title}</p>
            <p style={{ color: 'var(--ink-soft)', fontSize: 13, margin: '0 0 18px' }}>What do you want to do with this task?</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button onClick={() => confirmSkip('next_week')} style={{ background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '12px 16px', color: 'var(--ink)', cursor: 'pointer', textAlign: 'left', fontSize: 13 }}>
                <span style={{ fontWeight: 600 }}>Move to next week</span>
                <span style={{ color: 'var(--ink-soft)', display: 'block', fontSize: 12, marginTop: 2 }}>Agent 2 will include it in your next weekly plan</span>
              </button>
              <button onClick={() => confirmSkip('remove')} style={{ background: 'var(--accent-surface)', border: '1px solid var(--rule)', borderRadius: 0, padding: '12px 16px', color: 'var(--ink)', cursor: 'pointer', textAlign: 'left', fontSize: 13 }}>
                <span style={{ fontWeight: 600 }}>Permanently remove</span>
                <span style={{ color: 'var(--ink-soft)', display: 'block', fontSize: 12, marginTop: 2 }}>Remove from your plan entirely — won't come back</span>
              </button>
              <button onClick={() => confirmSkip('skip_once')} style={{ background: 'none', border: '1px solid var(--accent-surface)', borderRadius: 0, padding: '10px 16px', color: 'var(--ink-soft)', cursor: 'pointer', textAlign: 'left', fontSize: 13 }}>
                Just skip this week — no action
              </button>
            </div>
            <button onClick={() => setSkipDialog(null)} style={{ marginTop: 14, background: 'none', border: 'none', color: 'var(--ink-soft)', cursor: 'pointer', fontSize: 12, padding: 0 }}>Cancel</button>
          </div>
        </>
      )}

      {/* Half-screen chat drawer */}
      {chatOpen && (
        <>
          <div onClick={() => setChatOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(26,25,24,0.45)', zIndex: 55 }} />
          <div style={{
            position: 'fixed', top: 0, right: 0, bottom: 0,
            width: 'min(max(50vw, 340px), 600px, 96vw)',
            background: 'var(--paper)', borderLeft: '1px solid var(--rule)',
            zIndex: 60, display: 'flex', flexDirection: 'column',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '16px 20px', borderBottom: '1px solid var(--accent-surface)',
            }}>
              <div>
                <p style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Agent 2</p>
                <p style={{ margin: 0, color: 'var(--ink-soft)', fontSize: 12 }}>
                  Week {context?.week_number || 1} · chat resets on new week
                </p>
              </div>
              <button
                onClick={() => setChatOpen(false)}
                style={{
                  width: 32, height: 32, borderRadius: 0,
                  border: '1px solid var(--rule)',
                  background: 'var(--accent-surface)', color: 'var(--ink)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                }}
              >
                <X size={15} />
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {!historyLoaded && (
                <button
                  onClick={async () => {
                    const ok = await loadAgent2History(userId);
                    if (!ok) toast.error('Could not load previous chat.');
                  }}
                  disabled={loadingHistory}
                  style={{
                    alignSelf: 'center', marginBottom: 4,
                    background: 'var(--accent-surface)', border: '1px solid var(--rule)',
                    borderRadius: 0, padding: '6px 14px', color: 'var(--ink-soft)',
                    fontSize: 12, cursor: loadingHistory ? 'default' : 'pointer',
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                  }}
                >
                  {loadingHistory && <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />}
                  {loadingHistory ? 'Loading previous chat...' : 'Load previous chat'}
                </button>
              )}
              {messages.map((msg, i) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={i} style={{
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '88%',
                    background: isUser ? 'var(--ink)' : 'var(--accent-surface)',
                    color: isUser ? 'var(--bone)' : 'var(--ink)',
                    border: isUser ? 'none' : '1px solid var(--rule)',
                    borderRadius: 0,
                    padding: '10px 12px', fontSize: 14, lineHeight: 1.55,
                  }}>
                    {isUser ? msg.content : (
                      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={mdComponents}>
                        {msg.content}
                      </ReactMarkdown>
                    )}
                  </div>
                );
              })}
              {sending && (
                <div style={{ color: 'var(--ink-soft)', display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                  <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Agent 2 is replying...
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <form onSubmit={sendMessage} style={{ padding: '12px 20px 20px', borderTop: '1px solid var(--accent-surface)', display: 'flex', gap: 8 }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Exam in 2 weeks, slow down..."
                autoFocus
                style={{
                  flex: 1, background: 'var(--paper)', color: 'var(--ink)',
                  border: '1px solid var(--rule)', borderRadius: 0,
                  padding: '11px 12px', outline: 'none', fontSize: 14,
                }}
              />
              <button
                type="submit"
                disabled={!input.trim() || sending}
                style={{
                  width: 42, borderRadius: 0, border: 'none',
                  background: input.trim() && !sending ? 'var(--ink)' : 'var(--rule)',
                  color: 'var(--bone)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: input.trim() && !sending ? 'pointer' : 'not-allowed',
                }}
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @media (max-width: 640px) {
          .plan-preferences-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </main>
  );
}
