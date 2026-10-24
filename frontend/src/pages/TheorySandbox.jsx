import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ListChecks, ArrowRight, ArrowLeft, Loader2, Check, X, RotateCcw, Timer, Brain, Code2,
} from 'lucide-react';
import { toast } from 'sonner';
import { sandboxTheoryAPI } from '../lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { refreshEngagement } from '../hooks/useEngagement';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: '#050505',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
};
const muted = 'rgba(255,255,255,0.5)';

const LAST_TEST_KEY = 'delta_theory_last';
const QUESTION_COUNTS = [5, 10, 15];
const DIFFICULTIES = [{ key: 'easy', label: 'Easy' }, { key: 'medium', label: 'Medium' }, { key: 'hard', label: 'Hard' }];
const APTITUDE_AREAS = [
  { key: 'quantitative', label: 'Quantitative', desc: 'Percentages, ratios, time & work, speed' },
  { key: 'logical', label: 'Logical', desc: 'Puzzles, arrangements, coding-decoding' },
  { key: 'verbal', label: 'Verbal', desc: 'Comprehension, grammar, vocabulary' },
];

function fmt(sec) {
  const s = Math.max(0, sec);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

function Choice({ active, onClick, children, style }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      style={{
        padding: '10px 14px', borderRadius: 8, color: '#fff', fontWeight: 650, fontSize: 13.5, cursor: 'pointer', textAlign: 'left',
        background: active ? 'rgba(255,255,255,0.1)' : '#0a0a0a',
        border: `1px solid ${active ? 'rgba(255,255,255,0.32)' : 'rgba(255,255,255,0.1)'}`,
        ...style,
      }}
    >
      {children}
    </button>
  );
}

export default function TheorySandbox() {
  const userId = useAuthStore((state) => state.userId);
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();

  const [stage, setStage] = useState('setup'); // setup | test | result
  const [category, setCategory] = useState('technical');
  const [topic, setTopic] = useState(params.get('topic') || '');
  const [area, setArea] = useState('quantitative');
  const [difficulty, setDifficulty] = useState('medium');
  const [numQuestions, setNumQuestions] = useState(10);
  const [timed, setTimed] = useState(true);
  const [starting, setStarting] = useState(false);
  const [history, setHistory] = useState([]);
  const [suggestions, setSuggestions] = useState([]);

  const [sessionId, setSessionId] = useState(null);
  const [testTopic, setTestTopic] = useState('');
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [current, setCurrent] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [timeLeft, setTimeLeft] = useState(null);
  const deadlineRef = useRef(null);

  useEffect(() => {
    if (!userId || stage !== 'setup') return;
    sandboxTheoryAPI.getSessions(userId)
      .then((data) => setHistory((data?.sessions || []).filter((s) => s.status === 'completed').slice(0, 6)))
      .catch(() => {});
    sandboxTheoryAPI.suggestions(userId).then((d) => setSuggestions(d.topics || [])).catch(() => {});
  }, [userId, stage]);

  const submitTest = useCallback(async (auto = false) => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const data = await sandboxTheoryAPI.submit(userId, sessionId, answers);
      refreshEngagement(queryClient, userId);
      deadlineRef.current = null;
      setTimeLeft(null);
      setResult(data.result);
      setStage('result');
      if (auto) toast.message("Time's up! Your test was submitted.");
    } catch (err) {
      toast.error('Could not submit your test. Try again.');
    } finally {
      setSubmitting(false);
    }
  }, [submitting, userId, sessionId, answers, queryClient]);

  // Countdown for timed tests; auto-submits at zero.
  const submitRef = useRef(submitTest);
  submitRef.current = submitTest;
  useEffect(() => {
    if (stage !== 'test' || !deadlineRef.current) return undefined;
    const t = setInterval(() => {
      const left = Math.round((deadlineRef.current - Date.now()) / 1000);
      setTimeLeft(left);
      if (left <= 0) {
        clearInterval(t);
        submitRef.current(true);
      }
    }, 500);
    return () => clearInterval(t);
  }, [stage]);

  const startTest = async (override) => {
    const opts = override || {
      topic: category === 'technical' ? topic.trim() || null : null,
      num_questions: numQuestions, difficulty, category, area: category === 'aptitude' ? area : null, timed,
    };
    setStarting(true);
    try {
      const data = await sandboxTheoryAPI.start(userId, opts);
      try { localStorage.setItem(LAST_TEST_KEY, JSON.stringify(opts)); } catch { /* ignore */ }
      setSessionId(data.session_id);
      setTestTopic(data.topic);
      setQuestions(data.questions || []);
      setAnswers(new Array((data.questions || []).length).fill(null));
      setCurrent(0);
      deadlineRef.current = data.time_limit_seconds ? Date.now() + data.time_limit_seconds * 1000 : null;
      setTimeLeft(data.time_limit_seconds || null);
      setStage('test');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not generate a test. Try again.');
    } finally {
      setStarting(false);
    }
  };

  // One-click start from the Test Center (?quick=1): last settings, or a
  // 10-question test on the user's target role.
  const startRef = useRef(startTest);
  startRef.current = startTest;
  const quickStartedRef = useRef(false);
  useEffect(() => {
    if (!userId || params.get('quick') !== '1' || quickStartedRef.current) return;
    quickStartedRef.current = true;
    setParams({}, { replace: true });
    let last = null;
    try { last = JSON.parse(localStorage.getItem(LAST_TEST_KEY)); } catch { /* ignore */ }
    startRef.current(last || { topic: null, num_questions: 10, difficulty: 'medium', category: 'technical', area: null, timed: true });
  }, [userId, params, setParams]);

  const openPast = async (id) => {
    try {
      const data = await sandboxTheoryAPI.getSession(userId, id);
      if (!data.result) return;
      setTestTopic(data.topic);
      setResult(data.result);
      setStage('result');
    } catch {
      toast.error('Could not open that test.');
    }
  };

  const startOver = () => {
    setStage('setup');
    setSessionId(null);
    setQuestions([]);
    setAnswers([]);
    setResult(null);
    if (params.get('topic')) setParams({});
  };

  const choose = (optionIndex) => setAnswers((prev) => prev.map((a, i) => (i === current ? optionIndex : a)));

  const answeredCount = answers.filter((a) => a !== null).length;
  const isLast = current === questions.length - 1;
  const q = questions[current];

  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 780, margin: '0 auto' }}>

        {stage === 'setup' && (
          <>
            <header style={{ marginBottom: 24 }}>
              <p style={{ color: muted, fontSize: 13, fontWeight: 650, margin: '0 0 10px', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <ListChecks size={15} style={{ color: '#4ade80' }} /> Knowledge & Aptitude Tests
              </p>
              <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.2rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0 }}>
                Check what you actually know.
              </h1>
              <p style={{ margin: '14px 0 0', color: muted, fontSize: 15, lineHeight: 1.55 }}>
                Timed, placement-style tests with a per-skill breakdown and an explanation for every answer.
              </p>
            </header>

            <section style={{ ...panelStyle, padding: 22, display: 'grid', gap: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }} role="tablist" aria-label="Test type">
                <Choice active={category === 'technical'} onClick={() => setCategory('technical')} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Code2 size={16} /> Subject knowledge
                </Choice>
                <Choice active={category === 'aptitude'} onClick={() => setCategory('aptitude')} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Brain size={16} /> Aptitude
                </Choice>
              </div>

              {category === 'technical' ? (
                <div>
                  <label htmlFor="theory-topic" style={{ display: 'block', margin: '0 0 8px', fontSize: 14, color: muted }}>Topic</label>
                  <input
                    id="theory-topic"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Taxation, Pharmacology, Contract Law, DBMS — empty uses your target role"
                    maxLength={120}
                    style={{ width: '100%', background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: 13, color: '#fff', fontSize: 14, outline: 'none', boxSizing: 'border-box' }}
                  />
                  {suggestions.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
                      {suggestions.map((s) => (
                        <button
                          key={s.topic}
                          onClick={() => setTopic(s.topic)}
                          title={s.reason}
                          style={{ fontSize: 12.5, padding: '5px 10px', borderRadius: 999, cursor: 'pointer', color: topic === s.topic ? '#000' : '#fff', background: topic === s.topic ? '#4ade80' : 'rgba(255,255,255,0.06)', border: `1px solid ${s.reason === 'weak spot' ? 'rgba(251,191,36,0.5)' : 'rgba(255,255,255,0.12)'}` }}
                        >
                          {s.topic}{s.reason === 'weak spot' ? ' · weak spot' : ''}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <h2 style={{ margin: '0 0 8px', fontSize: 14, color: muted }}>Area</h2>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
                    {APTITUDE_AREAS.map((a) => (
                      <Choice key={a.key} active={area === a.key} onClick={() => setArea(a.key)}>
                        <span style={{ display: 'block' }}>{a.label}</span>
                        <span style={{ display: 'block', color: muted, fontSize: 12, fontWeight: 500, marginTop: 2 }}>{a.desc}</span>
                      </Choice>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                <div>
                  <h2 style={{ margin: '0 0 8px', fontSize: 14, color: muted }}>Difficulty</h2>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {DIFFICULTIES.map((d) => <Choice key={d.key} active={difficulty === d.key} onClick={() => setDifficulty(d.key)} style={{ flex: 1, textAlign: 'center' }}>{d.label}</Choice>)}
                  </div>
                </div>
                <div>
                  <h2 style={{ margin: '0 0 8px', fontSize: 14, color: muted }}>Questions</h2>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {QUESTION_COUNTS.map((n) => <Choice key={n} active={numQuestions === n} onClick={() => setNumQuestions(n)} style={{ flex: 1, textAlign: 'center' }}>{n}</Choice>)}
                  </div>
                </div>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13.5, cursor: 'pointer' }}>
                <input type="checkbox" checked={timed} onChange={() => setTimed((v) => !v)} />
                <Timer size={14} /> Timed, like a real placement test: {numQuestions} minutes, submits automatically
              </label>

              <button
                onClick={() => startTest()}
                disabled={starting}
                style={{
                  width: '100%', background: '#fff', color: '#000', border: 'none', borderRadius: 8,
                  padding: 14, fontWeight: 800, fontSize: 15, cursor: starting ? 'wait' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >
                {starting ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <ArrowRight size={16} />}
                {starting ? 'Writing your test…' : 'Start test'}
              </button>
            </section>

            {history.length > 0 && (
              <section style={{ marginTop: 22 }}>
                <h2 style={{ margin: '0 0 10px', fontSize: 13, color: muted, fontWeight: 650 }}>Recent tests</h2>
                <div style={{ display: 'grid', gap: 8 }}>
                  {history.map((h) => (
                    <button key={h.id} onClick={() => openPast(h.id)} style={{ ...panelStyle, padding: '12px 16px', display: 'flex', justifyContent: 'space-between', gap: 12, color: '#fff', cursor: 'pointer', textAlign: 'left' }}>
                      <span style={{ color: 'rgba(255,255,255,0.78)', fontSize: 13.5 }}>{h.title}</span>
                      <span style={{ fontSize: 13.5, fontWeight: 700 }}>{h.score}/100</span>
                    </button>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {stage === 'test' && q && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12 }}>
              <span style={{ color: muted, fontSize: 13, fontWeight: 600 }}>
                {testTopic} · Question {current + 1} of {questions.length}
              </span>
              {timeLeft != null ? (
                <span aria-live="off" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontVariantNumeric: 'tabular-nums', fontWeight: 700, fontSize: 14, color: timeLeft <= 60 ? '#f87171' : '#fff' }}>
                  <Timer size={14} /> {fmt(timeLeft)}
                </span>
              ) : (
                <span style={{ color: muted, fontSize: 12.5 }}>{answeredCount} answered</span>
              )}
            </div>

            {/* question navigator */}
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 14 }} aria-label="Jump to question">
              {questions.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrent(i)}
                  aria-label={`Question ${i + 1}${answers[i] !== null ? ', answered' : ''}`}
                  style={{
                    width: 30, height: 30, borderRadius: 6, fontSize: 12, fontWeight: 700, cursor: 'pointer',
                    color: i === current ? '#000' : '#fff',
                    background: i === current ? '#fff' : answers[i] !== null ? 'rgba(74,222,128,0.2)' : '#0a0a0a',
                    border: `1px solid ${answers[i] !== null ? 'rgba(74,222,128,0.45)' : 'rgba(255,255,255,0.12)'}`,
                  }}
                >
                  {i + 1}
                </button>
              ))}
            </div>

            <section style={{ ...panelStyle, padding: 24, marginBottom: 16 }}>
              <p style={{ margin: '0 0 6px', color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>{q.skill}</p>
              <p style={{ margin: 0, fontSize: 18, lineHeight: 1.5, fontWeight: 600, whiteSpace: 'pre-wrap' }}>{q.question}</p>
            </section>

            <div role="radiogroup" aria-label="Answer options" style={{ display: 'grid', gap: 10, marginBottom: 20 }}>
              {q.options.map((opt, i) => {
                const selected = answers[current] === i;
                return (
                  <button
                    key={i}
                    role="radio"
                    aria-checked={selected}
                    onClick={() => choose(i)}
                    style={{
                      display: 'flex', alignItems: 'flex-start', gap: 12, textAlign: 'left', cursor: 'pointer',
                      background: selected ? 'rgba(255,255,255,0.1)' : '#0a0a0a',
                      border: `1px solid ${selected ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.1)'}`,
                      borderRadius: 8, padding: '14px 16px', color: '#fff', fontSize: 14.5, lineHeight: 1.5,
                    }}
                  >
                    <span style={{ color: 'rgba(255,255,255,0.45)', fontWeight: 700, minWidth: 16 }}>{String.fromCharCode(65 + i)}</span>
                    <span style={{ whiteSpace: 'pre-wrap' }}>{opt}</span>
                  </button>
                );
              })}
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={() => setCurrent((c) => c - 1)}
                disabled={current === 0}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 7, background: 'rgba(255,255,255,0.07)',
                  border: '1px solid rgba(255,255,255,0.14)', borderRadius: 8, padding: '10px 16px',
                  color: current === 0 ? 'rgba(255,255,255,0.3)' : '#fff', fontSize: 13, fontWeight: 600,
                  cursor: current === 0 ? 'not-allowed' : 'pointer',
                }}
              >
                <ArrowLeft size={14} /> Back
              </button>
              <div style={{ flex: 1 }} />
              {isLast ? (
                <button
                  onClick={() => submitTest(false)}
                  disabled={submitting}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8, background: '#fff', color: '#000',
                    border: 'none', borderRadius: 8, padding: '10px 20px', fontWeight: 700, fontSize: 14,
                    cursor: submitting ? 'not-allowed' : 'pointer',
                  }}
                >
                  {submitting ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Check size={14} />}
                  {answeredCount < questions.length ? `Submit (${questions.length - answeredCount} unanswered)` : 'Submit test'}
                </button>
              ) : (
                <button
                  onClick={() => setCurrent((c) => c + 1)}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8, background: '#fff', color: '#000',
                    border: 'none', borderRadius: 8, padding: '10px 20px', fontWeight: 700, fontSize: 14, cursor: 'pointer',
                  }}
                >
                  Next <ArrowRight size={14} />
                </button>
              )}
            </div>
          </>
        )}

        {stage === 'result' && result && (
          <>
            <header style={{ marginBottom: 24, textAlign: 'center' }}>
              <p style={{ color: muted, fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>
                {testTopic} · {result.difficulty ? `${result.difficulty[0].toUpperCase()}${result.difficulty.slice(1)}` : ''} · Test complete
              </p>
              <div style={{
                width: 104, height: 104, borderRadius: '50%', margin: '0 auto 14px',
                background: 'rgba(255,255,255,0.06)', border: `3px solid ${result.score >= 70 ? '#4ade80' : result.score >= 50 ? '#fbbf24' : '#f87171'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ fontSize: 34, fontWeight: 800 }}>{result.score}</span>
              </div>
              <p style={{ margin: 0, color: muted, fontSize: 13 }}>
                {result.correct} of {result.total} correct
                {result.time_taken_seconds != null && ` · ${fmt(result.time_taken_seconds)}${result.time_limit_seconds ? ` of ${fmt(result.time_limit_seconds)}` : ''}`}
                {result.overtime && ' · over time'}
              </p>
            </header>

            <section style={{ ...panelStyle, padding: 20, marginBottom: 14 }}>
              <h2 style={{ margin: '0 0 14px', fontSize: 14, color: 'rgba(255,255,255,0.6)' }}>By skill</h2>
              <div style={{ display: 'grid', gap: 10 }}>
                {Object.entries(result.skill_breakdown || {}).map(([skill, s]) => {
                  const pct = Math.round((100 * s.correct) / s.total);
                  return (
                    <div key={skill}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 5 }}>
                        <span style={{ color: 'rgba(255,255,255,0.8)' }}>{skill}</span>
                        <span style={{ color: muted }}>{s.correct}/{s.total}</span>
                      </div>
                      <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.08)' }}>
                        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 3, background: pct >= 70 ? '#4ade80' : '#fbbf24' }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section style={{ ...panelStyle, padding: 20, marginBottom: 20 }}>
              <h2 style={{ margin: '0 0 14px', fontSize: 14, color: 'rgba(255,255,255,0.6)' }}>Review answers</h2>
              <div style={{ display: 'grid', gap: 18 }}>
                {result.questions.map((r, i) => (
                  <div key={i}>
                    <p style={{ margin: '0 0 8px', fontSize: 13.5, fontWeight: 600, display: 'flex', gap: 8, lineHeight: 1.5 }}>
                      {r.correct
                        ? <Check size={15} style={{ color: '#4ade80', flexShrink: 0, marginTop: 3 }} aria-label="Correct" />
                        : <X size={15} style={{ color: '#f87171', flexShrink: 0, marginTop: 3 }} aria-label="Incorrect" />}
                      <span style={{ whiteSpace: 'pre-wrap' }}>{i + 1}. {r.question}</span>
                    </p>
                    {!r.correct && (
                      <p style={{ margin: '0 0 4px 23px', color: '#f87171', fontSize: 13 }}>
                        Your answer: {r.chosen_index === null ? 'not answered' : r.options[r.chosen_index]}
                      </p>
                    )}
                    <p style={{ margin: '0 0 4px 23px', color: '#4ade80', fontSize: 13 }}>
                      Correct: {r.options[r.answer_index]}
                    </p>
                    {r.explanation && (
                      <p style={{ margin: '0 0 0 23px', color: muted, fontSize: 13, lineHeight: 1.5 }}>{r.explanation}</p>
                    )}
                  </div>
                ))}
              </div>
            </section>

            <button
              onClick={startOver}
              style={{
                width: '100%', background: '#fff', color: '#000', border: 'none', borderRadius: 8,
                padding: 14, fontWeight: 700, fontSize: 15, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              <RotateCcw size={16} /> Take another test
            </button>
          </>
        )}
      </div>

      <style>{'@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }'}</style>
    </main>
  );
}
