import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BadgeCheck, Loader2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { verifyAPI } from '../lib/api';
import { waitForJob } from '../lib/backgroundJobs';
import useSessionSignals from '../hooks/useSessionSignals';
import { useAuthStore } from '../store/authStore';

// A strict, timed re-check of the readiness score: fresh questions from a shared
// bank and, for tech fields, one coding problem. Recruiters see it only if the
// student holds their practice level. It is not camera proctoring.

const card = 'rounded-2xl border border-rule bg-paper';
const pill = 'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold disabled:opacity-50';
const LANGUAGES = { python: 'Python', javascript: 'JavaScript', java: 'Java', cpp: 'C++' };
const day = (iso) => (iso ? new Date(/(Z|[+-]\d\d:\d\d)$/.test(iso) ? iso : `${iso}Z`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : ''); // server times are UTC
const errText = (err, fallback) => err?.response?.data?.detail || err?.message || fallback;

function useCountdown(deadline) {
  const [left, setLeft] = useState(null);
  useEffect(() => {
    if (!deadline) return undefined;
    const end = new Date(`${deadline}Z`).getTime();
    const tick = () => setLeft(Math.max(0, Math.round((end - Date.now()) / 1000)));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [deadline]);
  return left;
}

const clock = (s) => (s == null ? '' : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`);

function Questions({ userId, check, onDone }) {
  const part = check.parts.theory;
  const [answers, setAnswers] = useState(() => part.questions.map(() => null));
  const [busy, setBusy] = useState(false);
  const signals = useSessionSignals(`${check.id}-theory`);
  const left = useCountdown(part.deadline);

  const submit = async () => {
    setBusy(true);
    try {
      onDone(await verifyAPI.submitTheory(userId, check.id, answers, signals.snapshot()));
    } catch (err) {
      toast.error(errText(err, 'Could not submit.'));
      setBusy(false);
    }
  };
  useEffect(() => {
    if (left === 0 && !busy) submit();
  }, [left]);

  return (
    <section className={`${card} p-5`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-ink">Part 1 · {part.questions.length} questions</h2>
        <span className={`tabular-nums text-sm font-semibold ${left != null && left < 60 ? 'text-oxblood' : 'text-ink'}`}>{clock(left)} left</span>
      </div>
      <ol className="mt-4 grid gap-5 pl-5">
        {part.questions.map((q, i) => (
          <li key={i} className="text-sm text-ink">
            <p className="whitespace-pre-wrap font-medium">{q.question}</p>
            <div className="mt-2 grid gap-1.5">
              {q.options.map((opt, j) => (
                <label key={j} className={`flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2 ${answers[i] === j ? 'border-ink' : 'border-rule'}`}>
                  <input type="radio" name={`q${i}`} checked={answers[i] === j} className="mt-1"
                    onChange={() => setAnswers((a) => a.map((v, k) => (k === i ? j : v)))} />
                  <span>{opt}</span>
                </label>
              ))}
            </div>
          </li>
        ))}
      </ol>
      <button className={`${pill} mt-5 bg-ink text-paper`} disabled={busy} onClick={submit}>
        {busy && <Loader2 size={14} className="animate-spin" />} Submit answers
      </button>
    </section>
  );
}

function Coding({ userId, check, onDone }) {
  const part = check.parts.coding;
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState(part.starter_code?.python || '');
  const [output, setOutput] = useState('');
  const [busy, setBusy] = useState('');
  const [submitsLeft, setSubmitsLeft] = useState(part.submits_left);
  const signals = useSessionSignals(`${check.id}-coding`);
  const left = useCountdown(part.deadline);

  const run = async () => {
    setBusy('run');
    try {
      const r = await verifyAPI.run(userId, check.id, language, code, part.examples?.[0]?.input || '');
      setOutput(r.error || r.stderr || r.stdout || '(no output)');
    } catch (err) {
      toast.error(errText(err, 'Could not run.'));
    } finally {
      setBusy('');
    }
  };
  const submit = async () => {
    setBusy('submit');
    try {
      const r = await verifyAPI.submitCoding(userId, check.id, language, code, signals.snapshot());
      setSubmitsLeft(r.submits_left);
      setOutput(`${r.passed} of ${r.total} hidden tests passed.`);
      if (r.check.status !== 'in_progress' || r.check.parts.coding.done) onDone(r.check);
    } catch (err) {
      toast.error(errText(err, 'Could not submit.'));
    } finally {
      setBusy('');
    }
  };

  return (
    <section className={`${card} p-5`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-ink">Part 2 · {part.title}</h2>
        <span className={`tabular-nums text-sm font-semibold ${left != null && left < 120 ? 'text-oxblood' : 'text-ink'}`}>{clock(left)} left · {submitsLeft} submits left</span>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm text-ink">{part.statement}</p>
      {(part.examples || []).map((ex, i) => (
        <pre key={i} className="mt-2 overflow-x-auto rounded-lg bg-bone p-3 text-xs text-ink">Input:{'\n'}{ex.input}{'\n'}Output:{'\n'}{ex.output}</pre>
      ))}
      <div className="mt-3 flex items-center gap-2">
        <select aria-label="Language" value={language} className="rounded-lg border border-rule bg-paper px-2 py-1.5 text-sm"
          onChange={(e) => { setLanguage(e.target.value); setCode(part.starter_code?.[e.target.value] || ''); }}>
          {Object.entries(LANGUAGES).filter(([k]) => part.starter_code?.[k] !== undefined).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <div className="mt-2 overflow-hidden rounded-lg">
        <Editor height="320px" language={language} theme="vs-dark" value={code} onChange={(v) => setCode(v ?? '')}
          onMount={(editor) => {
            editor.onDidPaste((e) => signals.notePaste(editor.getModel()?.getValueInRange(e.range) || ''));
          }}
          options={{ minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false, automaticLayout: true }} />
      </div>
      {output && <pre className="mt-2 overflow-x-auto rounded-lg bg-bone p-3 text-xs text-ink">{output}</pre>}
      <div className="mt-3 flex flex-wrap gap-2">
        <button className={`${pill} border border-rule text-ink`} disabled={!!busy || left === 0} onClick={run}>
          {busy === 'run' && <Loader2 size={14} className="animate-spin" />} Run on the example
        </button>
        <button className={`${pill} bg-ink text-paper`} disabled={!!busy || left === 0 || submitsLeft <= 0} onClick={submit}>
          {busy === 'submit' && <Loader2 size={14} className="animate-spin" />} Submit
        </button>
      </div>
    </section>
  );
}

export default function VerifyReadiness() {
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
  const key = ['verify-status', userId];
  const { data, isLoading } = useQuery({ queryKey: key, queryFn: () => verifyAPI.status(userId), enabled: !!userId });
  const [check, setCheck] = useState(null);
  const [starting, setStarting] = useState(false);
  const [agreed, setAgreed] = useState(false);

  useEffect(() => {
    if (data?.current) setCheck(data.current);
  }, [data?.current?.id]);

  const refresh = () => queryClient.invalidateQueries({ queryKey: key });
  const start = async () => {
    setStarting(true);
    try {
      let r = await verifyAPI.start(userId);
      if (r.preparing) {
        await waitForJob(r.preparing.id);
        r = await verifyAPI.start(userId);
      }
      setCheck(r.check);
    } catch (err) {
      toast.error(errText(err, 'Could not start the re-check.'));
    } finally {
      setStarting(false);
    }
  };
  const update = (next) => {
    setCheck(next);
    if (next.status !== 'in_progress') {
      refresh();
      setCheck(null);
    }
  };

  if (isLoading || !data) return <main className="min-h-screen bg-bone px-4 pt-24"><Loader2 className="mx-auto h-6 w-6 animate-spin text-ink-soft" /></main>;
  const rules = data.rules;
  const inProgress = check && check.status === 'in_progress';
  const showCoding = inProgress && check.parts.coding && (check.parts.theory.done || !check.parts.theory.questions);

  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-20 sm:pt-24">
      <div className="mx-auto grid max-w-3xl grid-cols-1 gap-4">
        <header>
          <h1 className="flex items-center gap-2 font-display text-3xl font-semibold text-ink"><ShieldCheck size={26} className="text-reward" /> Verify your readiness</h1>
          <p className="mt-1 text-ink-soft">A short, strictly timed re-check with fresh questions. If you hold your practice level, recruiters see your readiness as verified.</p>
        </header>

        {inProgress ? (
          showCoding ? <Coding userId={userId} check={check} onDone={update} />
            : <Questions userId={userId} check={check} onDone={update} />
        ) : (
          <>
            {data.verified && (
              <section className={`${card} flex items-start gap-3 p-5`}>
                <BadgeCheck className="mt-0.5 shrink-0 text-reward" />
                <p className="text-sm text-ink">Verified readiness <strong>{data.verified.score}</strong> on {day(data.verified.on)}. Recruiters see it until {day(data.verified.valid_until)}.</p>
              </section>
            )}
            {data.last && data.last.status === 'not_verified' && (
              <section className={`${card} p-5 text-sm text-ink`}>
                <p>Your last re-check scored <strong>{data.last.score}</strong> against your practice level of {data.last.baseline}{data.last.flags.length ? ` (${data.last.flags.join('; ')})` : ''}, so it isn't verified. Only you see this.</p>
                {data.retry_on && <p className="mt-1 text-ink-soft">You can try again on {day(data.retry_on)}.</p>}
              </section>
            )}
            {data.requests.length > 0 && (
              <section className={`${card} p-5 text-sm text-ink`}>
                {data.requests.map((r) => (
                  <p key={r.id} className="flex flex-wrap items-center justify-between gap-2">
                    <span><strong>{r.company}</strong> asked you to verify your readiness.</span>
                    <button className="text-ink-soft underline" onClick={async () => { await verifyAPI.decline(userId, r.id); refresh(); }}>Not now</button>
                  </p>
                ))}
              </section>
            )}
            <section className={`${card} p-5`}>
              <h2 className="text-lg font-semibold text-ink">How it works</h2>
              <ul className="mt-2 grid gap-1.5 pl-5 text-sm text-ink" style={{ listStyle: 'disc' }}>
                <li>{rules.questions} questions, {rules.seconds_per_question} seconds each on one clock. Answers after time is up don't count.</li>
                <li>For tech fields, then one coding problem: {rules.coding_minutes} minutes, {rules.max_submits} submits; you see how many hidden tests passed.</li>
                <li>Verified if you score within {rules.tolerance} points of your practice level, without leaving the tab more than {rules.max_tab_switches} times or pasting answers.</li>
                <li>Recruiters see only a pass, for {rules.valid_days} days. A miss stays private; you can retry after {rules.retry_days} days.</li>
                <li>This is a strict timed check with fresh questions, not camera proctoring.</li>
                {data.verified && <li>Taking it again replaces your current result, pass or miss.</li>}
              </ul>
              {data.can_start ? (
                <>
                  <label className="mt-4 flex items-start gap-2 text-sm text-ink">
                    <input type="checkbox" checked={agreed} onChange={() => setAgreed(!agreed)} className="mt-1" />
                    <span>I'll do this on my own, in one sitting, without help.</span>
                  </label>
                  <button className={`${pill} mt-3 bg-ink text-paper`} disabled={!agreed || starting} onClick={start}>
                    {starting && <Loader2 size={14} className="animate-spin" />} {starting ? 'Preparing your questions…' : 'Start the re-check'}
                  </button>
                </>
              ) : (
                <p className="mt-4 text-sm text-ink-soft">
                  {data.reason === 'no_tests' && <>Take a practice test first, so there's a score to verify. <Link to="/practice/theory" className="text-oxblood underline">Practice tests</Link></>}
                  {data.reason === 'cooldown' && `You can start a new re-check on ${day(data.retry_on)}.`}
                  {data.reason === 'minor' && 'Verified re-checks open when you turn 18.'}
                </p>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
