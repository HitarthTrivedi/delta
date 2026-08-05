import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Editor from '@monaco-editor/react';
import {
  Code2, Play, Send, Loader2, ChevronLeft, Check, X, ChevronDown,
} from 'lucide-react';
import { toast } from 'sonner';
import { sandboxCodingAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: '#050505',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
};

const LANGUAGE_LABELS = { python: 'Python', javascript: 'JavaScript', java: 'Java', cpp: 'C++' };

const DIFFICULTY_COLOR = {
  Easy: '#4ade80',
  Medium: '#fbbf24',
  Hard: '#f87171',
};

export default function CodingSandbox() {
  const userId = useAuthStore((state) => state.userId);
  const [topics, setTopics] = useState([]);
  const [languages, setLanguages] = useState(['python']);
  const [loading, setLoading] = useState(true);

  // Active problem/session state
  const [session, setSession] = useState(null); // {session_id, title, topic, difficulty, statement, examples, starter_code}
  const [starting, setStarting] = useState(false);
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState('');
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [runOutput, setRunOutput] = useState(null); // {stdout, stderr, error}
  const [submitResult, setSubmitResult] = useState(null); // {passed, total, all_passed, results, error}

  const loadProblems = useCallback(async () => {
    setLoading(true);
    try {
      const data = await sandboxCodingAPI.getProblems(userId);
      setTopics(data?.topics || []);
      if (data?.languages?.length) setLanguages(data.languages);
    } catch (err) {
      console.error(err);
      toast.error('Could not load the problem list.');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) loadProblems();
  }, [userId, loadProblems]);

  const solvedCount = useMemo(
    () => topics.reduce((acc, t) => acc + t.problems.filter((p) => p.completed).length, 0),
    [topics]
  );
  const totalCount = useMemo(() => topics.reduce((acc, t) => acc + t.problems.length, 0), [topics]);

  const openProblem = async (topic, problem) => {
    setStarting(true);
    setRunOutput(null);
    setSubmitResult(null);
    try {
      const data = await sandboxCodingAPI.startProblem(userId, topic, problem.id);
      setSession(data);
      const firstLang = languages[0] || 'python';
      setLanguage(firstLang);
      setCode(data.starter_code?.[firstLang] || '');
    } catch (err) {
      console.error(err);
      toast.error('Could not load this problem. Try again.');
    } finally {
      setStarting(false);
    }
  };

  const backToList = () => {
    setSession(null);
    setRunOutput(null);
    setSubmitResult(null);
    loadProblems(); // refresh solved-state
  };

  const changeLanguage = (lang) => {
    setLanguage(lang);
    setCode(session?.starter_code?.[lang] || '');
    setRunOutput(null);
    setSubmitResult(null);
  };

  const runCode = async () => {
    setRunning(true);
    setRunOutput(null);
    try {
      const result = await sandboxCodingAPI.run(userId, session.session_id, language, code, '');
      setRunOutput(result);
    } catch (err) {
      console.error(err);
      setRunOutput({ error: 'Could not reach the code runner. Try again.' });
    } finally {
      setRunning(false);
    }
  };

  const submitCode = async () => {
    setSubmitting(true);
    setSubmitResult(null);
    try {
      const result = await sandboxCodingAPI.submit(userId, session.session_id, language, code);
      setSubmitResult(result);
      if (result.all_passed) toast.success('All test cases passed!');
      else if (!result.error) toast.message(`${result.passed}/${result.total} test cases passed.`);
    } catch (err) {
      console.error(err);
      setSubmitResult({ error: 'Could not reach the code runner. Try again.' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: session ? 1200 : 900, margin: '0 auto' }}>

        {!session ? (
          <>
            {/* Header */}
            <header style={{ marginBottom: 28 }}>
              <p style={{ color: 'rgba(255,255,255,0.46)', fontSize: 13, fontWeight: 650, margin: '0 0 10px', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <Code2 size={15} style={{ color: '#60a5fa' }} /> Coding Sandbox
              </p>
              <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.2rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0, maxWidth: 720 }}>
                Practice, run, get graded.
              </h1>
              <p style={{ margin: '14px 0 0', color: 'rgba(255,255,255,0.5)', fontSize: 15, lineHeight: 1.55, maxWidth: 620 }}>
                Pick a problem, write real code in the editor, and submit for automatic pass/fail grading.
                {totalCount > 0 && <> {solvedCount}/{totalCount} solved.</>}
              </p>
            </header>

            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'rgba(255,255,255,0.5)', padding: '40px 0' }}>
                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Loading problems...
              </div>
            ) : (
              <div style={{ display: 'grid', gap: 16 }}>
                {topics.map((t) => (
                  <section key={t.topic} style={{ ...panelStyle, padding: 20 }}>
                    <div style={{ marginBottom: 14 }}>
                      <h2 style={{ margin: '0 0 4px', fontSize: 17 }}>{t.topic}</h2>
                      <p style={{ margin: 0, color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>{t.tip}</p>
                    </div>
                    <div style={{ display: 'grid', gap: 8 }}>
                      {t.problems.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => openProblem(t.topic, p)}
                          disabled={starting}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 12,
                            background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6,
                            padding: '11px 14px', color: '#fff', textAlign: 'left', cursor: starting ? 'not-allowed' : 'pointer',
                          }}
                        >
                          <span style={{
                            width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            background: p.completed ? 'rgba(74,222,128,0.15)' : 'rgba(255,255,255,0.06)',
                            border: `1px solid ${p.completed ? 'rgba(74,222,128,0.4)' : 'rgba(255,255,255,0.15)'}`,
                          }}>
                            {p.completed && <Check size={12} color="#4ade80" />}
                          </span>
                          <span style={{ flex: 1, fontSize: 14, fontWeight: 600 }}>{p.title}</span>
                          <span style={{
                            fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                            color: DIFFICULTY_COLOR[p.difficulty] || '#fff',
                            background: `${DIFFICULTY_COLOR[p.difficulty] || '#fff'}22`,
                          }}>
                            {p.difficulty}
                          </span>
                        </button>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            {/* Problem workspace */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
              <button
                onClick={backToList}
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: '8px 12px', color: '#fff', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}
              >
                <ChevronLeft size={14} /> Problems
              </button>
              <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{session.title}</h1>
              <span style={{
                fontSize: 11, fontWeight: 700, padding: '3px 9px', borderRadius: 4,
                color: DIFFICULTY_COLOR[session.difficulty] || '#fff',
                background: `${DIFFICULTY_COLOR[session.difficulty] || '#fff'}22`,
              }}>
                {session.difficulty}
              </span>
              {submitResult?.all_passed && (
                <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6, color: '#4ade80', fontSize: 13, fontWeight: 700 }}>
                  <Check size={15} /> Solved
                </span>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) minmax(360px, 1.4fr)', gap: 16 }}>
              {/* Statement panel */}
              <section style={{ ...panelStyle, padding: 20, maxHeight: '80vh', overflowY: 'auto' }}>
                <h2 style={{ margin: '0 0 12px', fontSize: 15, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Problem</h2>
                <p style={{ margin: '0 0 18px', color: 'rgba(255,255,255,0.8)', fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{session.statement}</p>
                {session.examples?.length > 0 && (
                  <>
                    <h3 style={{ margin: '0 0 10px', fontSize: 13, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Examples</h3>
                    <div style={{ display: 'grid', gap: 10 }}>
                      {session.examples.map((ex, i) => (
                        <div key={i} style={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6, padding: 12, fontSize: 12.5 }}>
                          <div style={{ marginBottom: 6 }}><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Input:</strong> <code style={{ color: '#fff' }}>{ex.input}</code></div>
                          <div style={{ marginBottom: ex.explanation ? 6 : 0 }}><strong style={{ color: 'rgba(255,255,255,0.6)' }}>Output:</strong> <code style={{ color: '#fff' }}>{ex.output}</code></div>
                          {ex.explanation && <div style={{ color: 'rgba(255,255,255,0.45)' }}>{ex.explanation}</div>}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </section>

              {/* Editor + run/submit panel */}
              <section style={{ ...panelStyle, padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  <div style={{ position: 'relative' }}>
                    <select
                      value={language}
                      onChange={(e) => changeLanguage(e.target.value)}
                      style={{
                        appearance: 'none', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.14)',
                        borderRadius: 6, padding: '6px 28px 6px 10px', color: '#fff', fontSize: 13, cursor: 'pointer', outline: 'none',
                      }}
                    >
                      {languages.map((l) => <option key={l} value={l}>{LANGUAGE_LABELS[l] || l}</option>)}
                    </select>
                    <ChevronDown size={13} style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'rgba(255,255,255,0.5)' }} />
                  </div>
                  <div style={{ flex: 1 }} />
                  <button
                    onClick={runCode}
                    disabled={running || submitting}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 6, padding: '7px 12px', color: '#fff', fontSize: 13, cursor: running ? 'not-allowed' : 'pointer', fontWeight: 600 }}
                  >
                    {running ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={13} />} Run
                  </button>
                  <button
                    onClick={submitCode}
                    disabled={running || submitting}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#fff', border: 'none', borderRadius: 6, padding: '7px 14px', color: '#000', fontSize: 13, cursor: submitting ? 'not-allowed' : 'pointer', fontWeight: 700 }}
                  >
                    {submitting ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={13} />} Submit
                  </button>
                </div>

                <Editor
                  height="380px"
                  language={language === 'cpp' ? 'cpp' : language}
                  theme="vs-dark"
                  value={code}
                  onChange={(v) => setCode(v ?? '')}
                  options={{ minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false, automaticLayout: true }}
                />

                {/* Output */}
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', padding: 14, maxHeight: 260, overflowY: 'auto', fontFamily: 'ui-monospace, monospace', fontSize: 12.5 }}>
                  {!runOutput && !submitResult && (
                    <p style={{ margin: 0, color: 'rgba(255,255,255,0.3)' }}>Run or submit to see output here.</p>
                  )}
                  {runOutput && (
                    <div style={{ marginBottom: submitResult ? 14 : 0 }}>
                      <p style={{ margin: '0 0 6px', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', fontSize: 10, letterSpacing: 0.5 }}>Run output</p>
                      {runOutput.error ? (
                        <p style={{ margin: 0, color: '#f87171' }}>{runOutput.error}</p>
                      ) : (
                        <>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', color: '#fff' }}>{runOutput.stdout || '(no output)'}</pre>
                          {runOutput.stderr && <pre style={{ margin: '6px 0 0', whiteSpace: 'pre-wrap', color: '#f87171' }}>{runOutput.stderr}</pre>}
                        </>
                      )}
                    </div>
                  )}
                  {submitResult && (
                    <div>
                      <p style={{ margin: '0 0 8px', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', fontSize: 10, letterSpacing: 0.5 }}>
                        Submission {submitResult.error ? '' : `— ${submitResult.passed}/${submitResult.total} passed`}
                      </p>
                      {submitResult.error ? (
                        <p style={{ margin: 0, color: '#f87171' }}>{submitResult.error}</p>
                      ) : (
                        <div style={{ display: 'grid', gap: 6 }}>
                          {submitResult.results.map((r) => (
                            <div key={r.index} style={{ display: 'flex', alignItems: 'center', gap: 8, color: r.passed ? '#4ade80' : '#f87171' }}>
                              {r.passed ? <Check size={13} /> : <X size={13} />}
                              <span>Test {r.index + 1}</span>
                              {!r.passed && <span style={{ color: 'rgba(255,255,255,0.4)' }}>— expected "{r.expected_output}", got "{r.actual_output || '(empty)'}"</span>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </section>
            </div>
          </>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </main>
  );
}
