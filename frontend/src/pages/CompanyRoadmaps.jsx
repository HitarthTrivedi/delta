import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Building2, ChevronDown, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { companyAPI } from '../lib/api';
import { careerContextKey } from '../hooks/useCareerOS';

// Roadmaps companies on Delta published for the roles they hire for. Following
// one adds up to 2 tasks a week next to your own plan, and shares your progress
// on it with that one company until you leave.

const card = 'rounded-2xl border border-rule bg-paper';
const pill = 'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold disabled:opacity-50';
const REASONS = {
  professional: 'Company roadmaps are for students. Delta for Professionals plans around your own goals.',
  minor: 'Company roadmaps open up when you turn 18.',
  college_pending: 'Your college seat is waiting for approval. Company roadmaps show once you\'re in.',
  staff: 'College staff accounts can\'t follow company roadmaps.',
};

function Roadmap({ r, onJoin, busy, full }) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState(false);
  return (
    <article className={`${card} p-5`}>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-soft">{r.company}{r.role ? ` · ${r.role}` : ''} · {r.weeks} weeks</p>
      <h2 className="mt-1 text-lg font-semibold text-ink">{r.title}</h2>
      {r.summary && <p className="mt-1 text-sm text-ink-soft">{r.summary}</p>}
      <p className="mt-2 text-sm text-ink">Skills: {r.skills.join(', ')}</p>
      <button className="mt-2 inline-flex items-center gap-1 bg-transparent p-0 text-sm text-oxblood" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? 'Hide' : 'See'} the {r.milestones.length} steps <ChevronDown size={14} style={{ transform: open ? 'rotate(180deg)' : 'none' }} />
      </button>
      {open && (
        <ol className="mt-2 grid gap-1 pl-5 text-sm">
          {r.milestones.map((m) => <li key={m.id}><span className="text-ink">{m.title}</span> <span className="text-ink-soft">· {m.skill}</span></li>)}
        </ol>
      )}
      {r.joined ? <p className="mt-3 text-sm font-semibold text-ink">You're following this.</p> : confirm ? (
        <div className="mt-3 rounded-xl border border-rule p-3 text-sm">
          <p className="text-ink">
            <span className="font-semibold">{r.company}</span> will see your name, education, progress on this roadmap, your scores on its skills, and your results in its tests (with how they were taken).
            They won't see your chats, résumé, other plans or anything else. You can stop sharing any time by leaving.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className={`${pill} bg-ink text-paper`} disabled={busy} onClick={() => onJoin(r.id)}>
              {busy && <Loader2 size={14} className="animate-spin" />} Follow and share with {r.company}
            </button>
            <button className={`${pill} border border-rule text-ink`} onClick={() => setConfirm(false)}>Not now</button>
          </div>
        </div>
      ) : (
        <button className={`${pill} mt-3 bg-ink text-paper`} disabled={full} onClick={() => setConfirm(true)}>
          {full ? 'You follow 2 already' : 'Follow this roadmap'}
        </button>
      )}
    </article>
  );
}

export default function CompanyRoadmaps() {
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
  const key = ['company-roadmaps-student', userId];
  const { data, isLoading } = useQuery({ queryKey: key, queryFn: () => companyAPI.visible(userId), enabled: !!userId });
  const [busy, setBusy] = useState('');

  const act = async (id, fn, msg) => {
    setBusy(id);
    try {
      await fn();
      queryClient.invalidateQueries({ queryKey: key });
      queryClient.invalidateQueries({ queryKey: careerContextKey(userId) });
      toast.success(msg);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not update.');
    } finally {
      setBusy('');
    }
  };

  const tracks = data?.tracks || [];
  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-20 sm:pt-24">
      <div className="mx-auto grid max-w-3xl grid-cols-1 gap-4">
        <header>
          <h1 className="flex items-center gap-2 font-display text-3xl font-semibold text-ink"><Building2 size={26} className="text-reward" /> Company roadmaps</h1>
          <p className="mt-1 text-ink-soft">Roadmaps companies on Delta made for the roles they hire for. Follow up to two next to your own plan: each adds a couple of tasks a week.</p>
        </header>

        {isLoading ? <Loader2 className="h-6 w-6 animate-spin text-ink-soft" /> : (
          <>
            {tracks.length > 0 && (
              <section className={`${card} p-5`}>
                <h2 className="text-base font-semibold text-ink">You're following</h2>
                <ul className="mt-2 grid gap-3">
                  {tracks.map((t) => (
                    <li key={t.roadmap_id} className="flex flex-wrap items-start justify-between gap-2">
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-ink">{t.title} · {t.company}</span>
                        <span className="block text-xs text-ink-soft">
                          Week {t.week} of {t.weeks} · {t.done} of {t.total} steps done{t.skipped ? ` · ${t.skipped} skipped (already proven)` : ''} · {t.on_track ? 'on track' : 'catching up'}
                          {t.status === 'archived' ? ' · the company ended this roadmap' : ''}
                        </span>
                        {t.tests.filter((x) => x.open && x.status !== 'done').map((x) => (
                          <Link key={x.id} to={`/practice/theory?assignment=${x.id}`} className="block text-xs text-oxblood underline">Take {t.company}'s test: {x.title}</Link>
                        ))}
                      </span>
                      <button className={`${pill} border border-rule text-ink`} disabled={busy === t.roadmap_id}
                        onClick={() => act(t.roadmap_id, () => companyAPI.leave(userId, t.roadmap_id), `You left it. ${t.company} no longer sees your progress.`)}>
                        Leave
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {data?.reason && REASONS[data.reason] ? <p className={`${card} p-5 text-sm text-ink-soft`}>{REASONS[data.reason]}</p>
              : (data?.roadmaps || []).filter((r) => !r.joined).length === 0
                ? <p className={`${card} p-5 text-sm text-ink-soft`}>No other company roadmaps for you right now. Companies hiring {data?.reason === 'college' ? 'at your college' : 'off-campus'} publish them here.</p>
                : (data?.roadmaps || []).filter((r) => !r.joined).map((r) => (
                  <Roadmap key={r.id} r={r} busy={busy === r.id} full={tracks.length >= (data.max_tracks || 2)}
                    onJoin={(id) => act(id, () => companyAPI.join(userId, id), 'Following. Its tasks join your weekly plan from next week.')} />
                ))}
          </>
        )}
      </div>
    </main>
  );
}
