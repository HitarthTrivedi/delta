import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CalendarDays, Check, Loader2, RefreshCw, Send, MessageSquare, Clock, BookOpen, AlertCircle, Maximize2, Minimize2 } from 'lucide-react';
import { toast } from 'sonner';
import { careerOSAPI, chatAPI } from '../lib/api';
import { getTaskProgress } from '../lib/taskProgress';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: '#050505',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
};

const fallbackActions = [
  { title: 'Confirm this week\'s availability', detail: 'Tell Agent 2 your realistic hours, exam pressure, and blocked days before it assigns heavy work.' },
  { title: 'Pick one proof task', detail: 'Choose a small project, course module, paper, or revision block that can be finished this week.' },
  { title: 'Report pace at week end', detail: 'Mark what was completed so Agent 2 can decide whether to increase, repeat, or pause next week.' },
];

export default function WeeklyPlan() {
  const userId = useAuthStore((state) => state.userId);
  const location = useLocation();
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [advanceStep, setAdvanceStep] = useState(0);
  const [checked, setChecked] = useState({});
  const [skipped, setSkipped] = useState({});
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Agent 2 is ready. Tell me if exams, deadlines, low energy, travel, or inactivity should change this week\'s plan.',
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const bottomRef = useRef(null);

  const loadContext = useCallback(async (regenerate = false) => {
    setLoading(true);
    try {
      const data = await careerOSAPI.getContext(userId);
      setContext(data);
      const progress = getTaskProgress(data, fallbackActions);
      setChecked(progress.checkedByIndex);
      setSkipped(progress.skippedByIndex);

      if (regenerate) {
        toast.success('Agent 2 loaded your first weekly plan.');
      }
    } catch (err) {
      console.error(err);
      toast.error('Unable to load Agent 2 plan. Using a safe starter week.');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    loadContext(params.get('from') === 'intake');
  }, [loadContext, location.search]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const memory = context?.memory || {};
  const roadmap = context?.roadmap || {};
  const weeklyFocus = useMemo(() => roadmap.weekly_focus || {}, [roadmap.weekly_focus]);
  const studentName = memory.identity_context?.name || memory.identity?.name || 'Student';
  const educationStage = memory.identity_context?.education_stage || memory.identity?.education_stage || 'Profile building';
  const targetRole = memory.ambitions?.target_role || roadmap.destination?.target_role || 'your goal';
  const hoursPerWeek = memory.constraints?.hours_per_week || 10;
  const longHorizonPlan = roadmap.destination?.long_horizon_plan || {};
  const longHorizonLanes = longHorizonPlan.lanes || weeklyFocus.long_horizon_lanes || [];

  const actions = useMemo(() => {
    return getTaskProgress(context, fallbackActions).actions;
  }, [context]);

  const opportunities = context?.opportunities || [];
  const nextQuestions = context?.next_questions || [];
  const chatPanelStyle = chatExpanded
    ? {
        ...panelStyle,
        position: 'fixed',
        inset: '5.25rem 1.25rem 1.25rem',
        zIndex: 60,
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 24px 80px rgba(0,0,0,0.72)',
      }
    : { ...panelStyle, padding: 20 };

  const refreshWeek = async () => {
    setRefreshing(true);
    try {
      const data = await careerOSAPI.getContext(userId);
      setContext(data);
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
    const nextChecked = { ...checked, [index]: nextValue };
      setChecked(nextChecked);
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
      setChecked({ ...checked, [index]: !nextValue });
      toast.error('Task saved locally, but could not sync with database.');
    }
  };

  const ADVANCE_STEPS = [
    'Reading your profile and past activity...',
    'Checking your Agent 2 conversations...',
    'Analysing completed and skipped tasks...',
    'Scanning market signals for your role...',
    'Agent 2 is curating your next week...',
    'Finalising your personalised task list...',
  ];

  const requestNextWeek = async () => {
    setAdvancing(true);
    setAdvanceStep(0);
    const stepInterval = setInterval(() => {
      setAdvanceStep(prev => {
        if (prev < ADVANCE_STEPS.length - 2) return prev + 1;
        clearInterval(stepInterval);
        return prev;
      });
    }, 4000);
    try {
      const data = await careerOSAPI.runWeeklyCycle(userId);
      clearInterval(stepInterval);
      setAdvanceStep(ADVANCE_STEPS.length - 1);
      setContext(data);
      const progress = getTaskProgress(data, fallbackActions);
      setChecked(progress.checkedByIndex);
      setSkipped(progress.skippedByIndex);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'I have generated the next weekly plan for you. If the new week has exams, deadlines, or if you need to adjust the pace, let me know here!',
      }]);
      toast.success('Next week loaded — Agent 2 has updated your tasks.');
    } catch (err) {
      clearInterval(stepInterval);
      console.error(err);
      const detail = err?.response?.data?.detail
        || err?.message
        || 'Something went wrong — Agent 2 could not generate next week. Try again in a moment.';
      toast.error(detail);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: detail,
      }]);
    } finally {
      setAdvancing(false);
      setAdvanceStep(0);
    }
  };

  const skipTask = async (e, action, index) => {
    e.stopPropagation();
    if (advancing) return;
    setChecked(prev => ({ ...prev, [index]: false }));
    setSkipped(prev => ({ ...prev, [index]: true }));
    try {
      await careerOSAPI.logJourneyEvent(userId, {
        event_type: 'weekly_task_skipped',
        summary: `Skipped Agent 2 task: ${action.title}`,
        evidence: action,
        impact: { user_chose_to_skip: true },
      });
      toast.success('Task skipped.');
    } catch (err) {
      console.error(err);
      toast.error('Could not save skip.');
    }
  };

  const sendMessage = async (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setSending(true);

    try {
      const response = await chatAPI.send({
        user_id: userId,
        message: `Agent 2 weekly plan discussion. Current weekly actions: ${actions.map(a => a.title).join('; ')}. User update: ${text}`,
      });
      setMessages(prev => [...prev, { role: 'assistant', content: response.response }]);
      // Single source of truth: if Agent 2 returned a task list, display EXACTLY that list.
      // No separate re-derivation that could disagree with what the AI just said.
      if (Array.isArray(response.updated_actions)) {
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
        setChecked({});   // list changed — reset progress marks
        setSkipped({});
      } else {
        await loadContext();
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Agent 2 could not reply right now. Try again in a few seconds, or ask directly to explain, replace, make easier, make tougher, assign one course, or skip a task.',
      }]);
      await loadContext();
    } finally {
      setSending(false);
    }
  };

  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start', marginBottom: 28 }}>
          <div>
            <p style={{ color: 'rgba(255,255,255,0.46)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
              Part 2 · Agent 2 roadmap · Week {context?.week_number || 1}
            </p>
            <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.4rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0, maxWidth: 760 }}>
              {studentName}'s week. Adjusted to your pace.
            </h1>
          </div>
          <button
            onClick={refreshWeek}
            disabled={refreshing || advancing}
            style={{
              background: '#fff',
              color: '#000',
              border: 'none',
              borderRadius: 999,
              padding: '11px 18px',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              cursor: refreshing ? 'not-allowed' : 'pointer',
            }}
          >
            {refreshing || advancing ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={15} />}
            Refresh plan
          </button>
        </header>

        <section style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 1,
          background: 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.1)',
          marginBottom: 24,
        }}>
          {[
            { icon: BookOpen, label: 'Student', value: `${studentName} · ${educationStage}` },
            { icon: BookOpen, label: 'Goal', value: targetRole },
            { icon: Clock, label: 'Available pace', value: `${hoursPerWeek}h / week` },
            { icon: CalendarDays, label: 'Focus', value: weeklyFocus.phase_name || 'First useful week' },
          ].map(item => {
            const Icon = item.icon;
            return (
              <div key={item.label} style={{ background: '#050505', padding: 18, minHeight: 110 }}>
                <Icon size={17} style={{ color: 'rgba(255,255,255,0.72)', marginBottom: 14 }} />
                <p style={{ color: 'rgba(255,255,255,0.38)', margin: '0 0 6px', fontSize: 12 }}>{item.label}</p>
                <p style={{ color: '#fff', margin: 0, fontSize: 15, lineHeight: 1.4, fontWeight: 650 }}>{item.value}</p>
              </div>
            );
          })}
        </section>

        {longHorizonLanes.length > 0 && (
          <section style={{ ...panelStyle, padding: 20, marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h2 style={{ margin: '0 0 6px', fontSize: 20 }}>Long-scale plan</h2>
                <p style={{ margin: 0, color: 'rgba(255,255,255,0.48)', fontSize: 14, lineHeight: 1.5 }}>
                  Delta keeps these lanes alive across the selected timeline, then chooses the right weekly slice.
                </p>
              </div>
              <span style={{ color: 'rgba(255,255,255,0.62)', fontSize: 13, whiteSpace: 'nowrap' }}>
                {longHorizonPlan.horizon_months || roadmap.destination?.planning_horizon_months || 12} months
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10 }}>
              {longHorizonLanes.map((lane) => (
                <div key={lane.name} style={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: 14 }}>
                  <p style={{ margin: '0 0 6px', color: '#fff', fontSize: 14, fontWeight: 700 }}>{lane.name}</p>
                  <p style={{ margin: '0 0 8px', color: 'rgba(255,255,255,0.52)', fontSize: 12 }}>{lane.cadence}</p>
                  <p style={{ margin: 0, color: 'rgba(255,255,255,0.68)', fontSize: 13, lineHeight: 1.45 }}>{lane.rule}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.15fr) minmax(0, 0.85fr)', gap: 22 }} className="agent2-grid">
          <section style={{ ...panelStyle, padding: 22 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
              <div>
                <h2 style={{ margin: '0 0 8px', fontSize: 24, letterSpacing: 0 }}>Tasks for this week</h2>
                <p style={{ margin: 0, color: 'rgba(255,255,255,0.48)', fontSize: 14, lineHeight: 1.55 }}>
                  Agent 2 should only assign new work after these are completed or after you say the plan needs to change.
                </p>
              </div>
              {loading && <Loader2 size={18} style={{ animation: 'spin 1s linear infinite', color: 'rgba(255,255,255,0.5)' }} />}
            </div>

            {advancing && (
              <div style={{ display: 'grid', gap: 14, padding: '8px 0' }}>
                {ADVANCE_STEPS.map((step, i) => {
                  const done = i < advanceStep;
                  const active = i === advanceStep;
                  return (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14, opacity: i > advanceStep ? 0.25 : 1, transition: 'opacity 0.4s ease' }}>
                      <span style={{
                        width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: done ? 'rgba(255,255,255,0.15)' : active ? 'rgba(255,255,255,0.06)' : 'transparent',
                        border: `1px solid ${done ? 'rgba(255,255,255,0.4)' : active ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.1)'}`,
                      }}>
                        {done
                          ? <Check size={13} color="#fff" />
                          : active
                            ? <Loader2 size={13} color="rgba(255,255,255,0.8)" style={{ animation: 'spin 1s linear infinite' }} />
                            : <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'rgba(255,255,255,0.2)' }} />
                        }
                      </span>
                      <span style={{ fontSize: 14, color: done ? 'rgba(255,255,255,0.55)' : active ? '#fff' : 'rgba(255,255,255,0.25)', fontWeight: active ? 600 : 400 }}>
                        {step}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            <div style={{ display: advancing ? 'none' : 'grid', gap: 12 }}>
              {actions.map((action, index) => {
                const isDone = !!checked[index];
                const isSkipped = !!skipped[index];
                return (
                  <button
                    key={action.id}
                    onClick={() => toggleTask(action, index)}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '34px minmax(0, 1fr)',
                      gap: 14,
                      textAlign: 'left',
                      width: '100%',
                      background: isDone ? 'rgba(255,255,255,0.1)' : isSkipped ? 'rgba(255,255,255,0.04)' : '#0a0a0a',
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 8,
                      padding: 16,
                      color: '#fff',
                      cursor: advancing ? 'not-allowed' : 'pointer',
                    }}
                  >
                    <span style={{
                      width: 28,
                      height: 28,
                      borderRadius: 6,
                      border: '1px solid rgba(255,255,255,0.22)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: isDone ? '#fff' : 'transparent',
                      color: '#000',
                    }}>
                      {isDone && <Check size={16} />}
                    </span>
                    <span>
                      <span style={{ display: 'block', fontSize: 16, fontWeight: 700, marginBottom: 6, textDecoration: isDone ? 'line-through' : 'none' }}>
                        {action.title}
                        {isSkipped ? <span style={{ marginLeft: 8, color: 'rgba(255,255,255,0.42)', fontSize: 12 }}>Skipped</span> : null}
                      </span>
                      <span style={{ display: 'block', color: 'rgba(255,255,255,0.5)', fontSize: 14, lineHeight: 1.55 }}>
                        {action.detail}
                      </span>
                      {(action.source || action.url) && (
                        <span style={{ display: 'block', marginTop: 8, color: 'rgba(255,255,255,0.44)', fontSize: 13 }}>
                          Source: {action.source || 'Open resource'}
                          {action.url ? (
                            <>
                              {' · '}
                              <a
                                href={action.url}
                                target="_blank"
                                rel="noreferrer"
                                onClick={(event) => event.stopPropagation()}
                                style={{ color: '#fff', textDecoration: 'underline' }}
                              >
                                Open
                              </a>
                            </>
                          ) : null}
                        </span>
                      )}
                      {!isDone && !isSkipped && (
                        <span
                          role="button"
                          tabIndex={0}
                          onClick={(event) => skipTask(event, action, index)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') skipTask(event, action, index);
                          }}
                          style={{ display: 'inline-block', marginTop: 10, color: 'rgba(255,255,255,0.64)', fontSize: 13, textDecoration: 'underline' }}
                        >
                          Skip this task
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>

            {actions.length > 0 && actions.every((_, actionIndex) => checked[actionIndex] || skipped[actionIndex]) && (
              <div style={{ marginTop: 20, padding: '16px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <p style={{ margin: '0 0 12px', color: 'rgba(255,255,255,0.85)', fontSize: 14, lineHeight: 1.5 }}>
                  <strong>All current tasks are checked.</strong> Request the next week only after you have genuinely finished the work and proof.
                </p>
                <button
                  onClick={requestNextWeek}
                  disabled={advancing}
                  style={{
                    width: '100%',
                    background: '#fff',
                    color: '#000',
                    border: 'none',
                    borderRadius: 6,
                    padding: '14px',
                    fontWeight: 700,
                    fontSize: 15,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 10,
                    cursor: advancing ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!advancing) {
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(255,255,255,0.2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'none';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  {advancing ? (
                    <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    <Check size={18} />
                  )}
                  Request Next Week's Activities
                </button>
              </div>
            )}

            <div style={{ marginTop: 22, display: 'grid', gap: 12 }}>
              <h3 style={{ margin: 0, fontSize: 17 }}>Signals Agent 2 may use</h3>
              {(nextQuestions.length ? nextQuestions.slice(0, 2) : [
                'Are there exams or deadlines that should pause normal learning?',
                ...(context?.week_number > 1 ? ['Was last week too easy, too hard, or just right?'] : ['What do you want to focus on first this week?']),
              ]).map((question, index) => (
                <div key={index} style={{ display: 'flex', gap: 10, color: 'rgba(255,255,255,0.52)', fontSize: 14, lineHeight: 1.5 }}>
                  <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                  {question}
                </div>
              ))}
            </div>
          </section>

          <aside style={{ display: 'grid', gap: 22 }}>
            {chatExpanded && (
              <div
                onClick={() => setChatExpanded(false)}
                style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.72)', zIndex: 50 }}
              />
            )}
            <section style={chatPanelStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 4 }}>
                <h2 style={{ margin: 0, fontSize: 20 }}>Talk to Agent 2</h2>
                <button
                  type="button"
                  onClick={() => setChatExpanded(prev => !prev)}
                  title={chatExpanded ? 'Minimize chat' : 'Maximize chat'}
                  aria-label={chatExpanded ? 'Minimize Agent 2 chat' : 'Maximize Agent 2 chat'}
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.14)',
                    background: 'rgba(255,255,255,0.06)',
                    color: '#fff',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                  }}
                >
                  {chatExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>
              </div>
              <p style={{ margin: '0 0 14px', fontSize: 12, color: 'rgba(255,255,255,0.38)', lineHeight: 1.5 }}>
                Tell Agent 2 about exams, travel, or pace changes for this week.{' '}
                <Link to="/chat" style={{ color: 'rgba(255,255,255,0.55)', textDecoration: 'underline' }}>
                  Open full AI Chat
                </Link>{' '}
                for deeper career questions.
              </p>
              <div style={{ height: chatExpanded ? 'calc(100vh - 15rem)' : 330, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10, paddingRight: 4 }}>
                {messages.map((message, index) => {
                  const isUser = message.role === 'user';
                  return (
                    <div
                      key={index}
                      style={{
                        alignSelf: isUser ? 'flex-end' : 'flex-start',
                        maxWidth: '88%',
                        background: isUser ? '#fff' : 'rgba(255,255,255,0.06)',
                        color: isUser ? '#000' : 'rgba(255,255,255,0.86)',
                        border: isUser ? 'none' : '1px solid rgba(255,255,255,0.1)',
                        borderRadius: isUser ? '14px 14px 4px 14px' : '4px 14px 14px 14px',
                        padding: '10px 12px',
                        fontSize: 14,
                        lineHeight: 1.55,
                      }}
                    >
                      {isUser ? message.content : (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => <p style={{ margin: '0 0 6px 0' }}>{children}</p>,
                            ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: 18 }}>{children}</ul>,
                            ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: 18 }}>{children}</ol>,
                            li: ({ children }) => <li style={{ marginBottom: 3 }}>{children}</li>,
                            strong: ({ children }) => <strong style={{ color: '#fff', fontWeight: 700 }}>{children}</strong>,
                            code: ({ children }) => <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 5px', borderRadius: 3, fontSize: 12 }}>{children}</code>,
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      )}
                    </div>
                  );
                })}
                {sending && (
                  <div style={{ color: 'rgba(255,255,255,0.45)', display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                    <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                    Agent 2 is replying...
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
              <form onSubmit={sendMessage} style={{ display: 'flex', gap: 8, marginTop: 14, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 14 }}>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Exam in 2 weeks, slow down..."
                  style={{
                    flex: 1,
                    background: '#0a0a0a',
                    color: '#fff',
                    border: '1px solid rgba(255,255,255,0.14)',
                    borderRadius: 8,
                    padding: '11px 12px',
                    outline: 'none',
                    fontSize: 14,
                  }}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || sending}
                  style={{
                    width: 42,
                    borderRadius: 8,
                    border: 'none',
                    background: input.trim() && !sending ? '#fff' : 'rgba(255,255,255,0.12)',
                    color: '#000',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: input.trim() && !sending ? 'pointer' : 'not-allowed',
                  }}
                >
                  <Send size={16} />
                </button>
              </form>
            </section>

            <section style={{ ...panelStyle, padding: 20 }}>
              <h2 style={{ margin: '0 0 14px', fontSize: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                <MessageSquare size={18} /> Opportunities
              </h2>
              <div style={{ display: 'grid', gap: 10 }}>
                {opportunities.length ? opportunities.slice(0, 4).map((item, index) => (
                  <div key={index} style={{ borderTop: index ? '1px solid rgba(255,255,255,0.1)' : 'none', paddingTop: index ? 10 : 0 }}>
                    <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 700 }}>{item.title || item.name}</p>
                    <p style={{ margin: 0, color: 'rgba(255,255,255,0.42)', fontSize: 12 }}>
                      {item.platform}{item.match_percentage ? ` · ${item.match_percentage}% match` : ''}
                    </p>
                  </div>
                )) : (
                  <p style={{ margin: 0, color: 'rgba(255,255,255,0.38)', fontSize: 13, lineHeight: 1.5 }}>
                    Delta will surface relevant opportunities once your roadmap is further along.
                  </p>
                )}
              </div>
            </section>
          </aside>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @media (max-width: 900px) {
          .agent2-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </main>
  );
}
