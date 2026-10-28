import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Crosshair, Loader2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { jobsAPI } from '../lib/api';
import { careerContextKey } from '../hooks/useCareerOS';

// Paste a job ad -> how close you are -> turn the gaps into this week's tasks.
// The ad is read by AI without your profile; the comparison happens on our server.

const card = 'rounded-2xl border border-rule bg-paper';
const STATUS = {
  gap: { label: 'Not yet', tone: 'text-ink-soft' },
  building: { label: 'Building', tone: 'text-ink' },
  strong: { label: 'Strong', tone: 'text-reward' },
};

function level(s) {
  if (s.your_level == null) return 'Not on your profile yet';
  return `You: ${s.your_level}/10${s.proven ? '' : ' (self-rated)'}`;
}

function Report({ userId, r, onChange }) {
  const queryClient = useQueryClient();
  const gaps = r.skills.filter((s) => s.status !== 'strong')
    .sort((a, b) => (a.status === b.status ? (a.importance === 'must' ? -1 : 1) : a.status === 'gap' ? -1 : 1));
  const strong = r.skills.filter((s) => s.status === 'strong');
  const [picked, setPicked] = useState(() => new Set(r.top_gaps.slice(0, 2)));
  const [busy, setBusy] = useState('');

  const toggle = (name) => setPicked((prev) => {
    const next = new Set(prev);
    if (next.has(name)) next.delete(name);
    else if (next.size < 3) next.add(name);
    else toast.message('Pick up to 3 for this week. The rest can come next week.');
    return next;
  });

  const addToWeek = async () => {
    setBusy('add');
    try {
      const res = await jobsAPI.addToWeek(userId, r.id, [...picked]);
      queryClient.removeQueries({ queryKey: careerContextKey(userId) }); // My plan reloads with the new tasks
      toast.success(res.added.length ? `Added to this week: ${res.added.join(', ')}` : 'Those tasks are already in this week.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not add the tasks.');
    } finally {
      setBusy('');
    }
  };

  const plan = async (on) => {
    setBusy('plan');
    try {
      onChange(await jobsAPI.plan(userId, r.id, on));
      toast.success(on ? 'From next week, your plan starts with this job\'s skills.' : 'Stopped planning around this job.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not update your plan.');
    } finally {
      setBusy('');
    }
  };

  return (
    <section className={`${card} p-5 sm:p-6`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-display text-2xl font-semibold text-ink">{r.title}</h2>
          <p className="text-sm text-ink-soft">{[r.company, r.seniority && `${r.seniority} level`].filter(Boolean).join(' · ') || 'Company not named'}</p>
        </div>
        <div className="text-right">
          <p className="font-display text-4xl font-semibold text-ink">{r.match_pct}%</p>
          <p className="text-xs text-ink-soft">match today</p>
        </div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-ink/10" aria-hidden="true"><div className="h-2 rounded-full bg-reward" style={{ width: `${r.match_pct}%` }} /></div>

      {gaps.length > 0 && (
        <>
          <h3 className="mt-6 text-sm font-semibold text-ink">To work on <span className="font-normal text-ink-soft">· pick up to 3 for this week</span></h3>
          <ul className="mt-2 divide-y divide-rule">
            {gaps.map((s) => (
              <li key={s.name} className="flex gap-3 py-3">
                <input type="checkbox" className="mt-1 h-4 w-4 shrink-0" checked={picked.has(s.name)} onChange={() => toggle(s.name)}
                  aria-label={`Add a task for ${s.name} to this week`} />
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-x-2 text-ink">
                    <span className="font-semibold">{s.name}</span>
                    <span className="text-xs text-ink-soft">{s.importance === 'must' ? 'Must have' : 'Nice to have'}</span>
                    <span className={`text-xs ${STATUS[s.status].tone}`}>· {STATUS[s.status].label} · {level(s)}</span>
                  </p>
                  <p className="mt-1 text-sm text-ink">{s.task.title}</p>
                  <p className="text-sm text-ink-soft">{s.task.detail}</p>
                  <Link to={`/practice/theory?topic=${encodeURIComponent(s.name)}`} className="mt-1 inline-block text-sm text-ink-soft underline-offset-4 hover:underline">
                    Take a quick test on {s.name}
                  </Link>
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button onClick={addToWeek} disabled={!picked.size || busy === 'add'}
              className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-50">
              {busy === 'add' && <Loader2 size={14} className="animate-spin" />} Add {picked.size || ''} to this week
            </button>
            {r.plan_until ? (
              <span className="text-sm text-ink-soft">
                Your weeks start with this job's skills until {new Date(`${r.plan_until}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}.{' '}
                <button onClick={() => plan(false)} disabled={busy === 'plan'} className="underline underline-offset-4">Stop</button>
              </span>
            ) : (
              <button onClick={() => plan(true)} disabled={busy === 'plan'}
                className="rounded-full border border-ink px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50">
                Plan my next 4 weeks around this job
              </button>
            )}
          </div>
        </>
      )}

      {strong.length > 0 && (
        <>
          <h3 className="mt-6 text-sm font-semibold text-ink">You already have</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {strong.map((s) => (
              <span key={s.name} className="inline-flex items-center gap-1 rounded-full bg-reward/10 px-3 py-1 text-sm text-ink">
                <Check size={13} className="text-reward" aria-hidden="true" /> {s.name}{s.proven ? '' : ' (self-rated)'}
              </span>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export default function JobMatch() {
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
  const [text, setText] = useState('');
  const [report, setReport] = useState(null);
  const [analysing, setAnalysing] = useState(false);
  const { data: saved } = useQuery({ queryKey: ['jobs', userId], queryFn: () => jobsAPI.list(userId), enabled: !!userId });
  const refreshList = () => queryClient.invalidateQueries({ queryKey: ['jobs', userId] });

  const analyse = async (e) => {
    e.preventDefault();
    setAnalysing(true);
    try {
      setReport(await jobsAPI.analyse(userId, text));
      setText('');
      refreshList();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not read that job description. Try again.');
    } finally {
      setAnalysing(false);
    }
  };

  const open = async (id) => {
    try { setReport(await jobsAPI.get(userId, id)); } catch { toast.error('Could not open that job.'); }
  };

  const remove = async (id) => {
    try {
      await jobsAPI.remove(userId, id);
      if (report?.id === id) setReport(null);
      refreshList();
    } catch {
      toast.error('Could not remove that job.');
    }
  };

  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-20 sm:pt-24">
      <div className="mx-auto grid max-w-3xl grid-cols-1 gap-4">
        <header>
          <h1 className="flex items-center gap-2 font-display text-3xl font-semibold text-ink"><Crosshair size={26} className="text-reward" /> Job match</h1>
          <p className="mt-1 text-ink-soft">Paste a job ad. See how close you are today, and turn the gaps into this week's tasks.</p>
        </header>

        <form onSubmit={analyse} className={`${card} p-5 sm:p-6`}>
          <label htmlFor="jd" className="text-sm font-semibold text-ink">Job description</label>
          <textarea id="jd" value={text} onChange={(e) => setText(e.target.value)} rows={7} maxLength={20000}
            placeholder="Paste the whole job ad here: role, responsibilities and requirements."
            className="mt-2 w-full rounded-lg border border-rule bg-paper px-3 py-2 text-sm text-ink" />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-md text-xs text-ink-soft">
              The ad is read by AI on its own; your profile is never sent. We keep the role and its skills, not the text.
            </p>
            <button type="submit" disabled={analysing || text.trim().length < 150}
              className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-50">
              {analysing && <Loader2 size={14} className="animate-spin" />} {analysing ? 'Reading the ad…' : 'Check my match'}
            </button>
          </div>
        </form>

        {report && <Report key={report.id + (report.plan_until || '')} userId={userId} r={report} onChange={(r) => { setReport(r); refreshList(); }} />}

        {saved?.jobs?.length > 0 && (
          <section className={`${card} p-5 sm:p-6`}>
            <h2 className="text-sm font-semibold text-ink">Your jobs</h2>
            <ul className="mt-2 divide-y divide-rule">
              {saved.jobs.map((j) => (
                <li key={j.id} className="flex items-center justify-between gap-3 py-2.5">
                  <button onClick={() => open(j.id)} className="min-w-0 text-left">
                    <span className="block truncate text-ink">{j.title}{j.company ? ` · ${j.company}` : ''}</span>
                    <span className="text-xs text-ink-soft">{j.match_pct}% match{j.plan_until ? ' · planning around it' : ''}</span>
                  </button>
                  <button onClick={() => remove(j.id)} aria-label={`Remove ${j.title}`} className="rounded-full p-2 text-ink-soft hover:bg-accent-surface">
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </main>
  );
}
