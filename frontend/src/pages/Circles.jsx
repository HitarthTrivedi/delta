import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Check, Copy, Flame, Gift, Loader2, RefreshCw, Share2, Users, X } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { circlesAPI, engagementAPI } from '../lib/api';
import { inviteLink } from '../lib/referral';

// Study circles (opt-in) and invite-a-friend. Members see only first name +
// last initial, whether each studied today, and study days this week.

const card = 'rounded-2xl border border-rule bg-paper';
const MEMBERS_SEE = 'Members see your first name and last initial, whether you studied today, and your study days this week. Nothing else.';

async function copy(text, done) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(done);
  } catch {
    toast.message(text);
  }
}

function CircleCard({ userId, c, onChange }) {
  const [confirm, setConfirm] = useState(''); // 'leave' | member id
  const [busy, setBusy] = useState(false);
  const link = `${window.location.origin}/circles/join/${c.invite_code}`;
  const run = async (fn, msg) => {
    setBusy(true);
    try {
      onChange(await fn());
      if (msg) toast.success(msg);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not update the circle.');
    } finally {
      setBusy(false);
      setConfirm('');
    }
  };
  const pct = c.week.target ? Math.round((100 * c.week.done) / c.week.target) : 0;

  return (
    <section className={`${card} p-5 sm:p-6`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate font-display text-2xl font-semibold text-ink">{c.name}</h2>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-soft">
            <Flame size={15} className={c.streak > 0 ? 'text-reward' : ''} aria-hidden="true" />
            {c.streak > 0 ? `${c.streak}-day circle streak` : 'Circle streak starts when everyone studies on the same day'}
          </p>
        </div>
        {c.members.length < 6 && (
          <button onClick={() => copy(link, 'Invite link copied. Send it to a friend.')}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-ink px-3 py-1.5 text-sm font-semibold text-ink">
            <Copy size={14} /> Copy invite link
          </button>
        )}
      </div>

      <div className="mt-4">
        <div className="flex items-baseline justify-between gap-2 text-sm">
          <span className="font-semibold text-ink">This week together</span>
          <span className="text-ink-soft">{c.week.done} / {c.week.target} study days</span>
        </div>
        <div className="mt-1.5 h-2 rounded-full bg-ink/10" aria-hidden="true">
          <div className="h-2 rounded-full bg-reward" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1 text-xs text-ink-soft">
          {c.members.length < 2
            ? 'Invite someone to start a shared goal.'
            : c.week.met
              ? `Goal met! Everyone gets +${c.week.reward_xp} XP${c.week.rewarded ? ' (yours is in).' : '.'}`
              : `Reach ${c.week.target} together this week and everyone gets +${c.week.reward_xp} XP.`}
        </p>
      </div>

      <ul className="mt-4 divide-y divide-rule">
        {c.members.map((m) => (
          <li key={m.id} className="flex items-center justify-between gap-3 py-2.5">
            <span className="flex min-w-0 items-center gap-3">
              {m.studied_today
                ? <Check size={16} className="shrink-0 text-reward" aria-label="Studied today" />
                : <span className="h-4 w-4 shrink-0 rounded-full border-2 border-rule" aria-label="Not yet today" />}
              <span className="truncate text-ink">{m.name}{m.you ? ' (you)' : ''}{m.owner ? <span className="text-ink-soft"> · started it</span> : null}</span>
            </span>
            <span className="flex shrink-0 items-center gap-2 text-sm text-ink-soft">
              {m.days_this_week} {m.days_this_week === 1 ? 'day' : 'days'}
              {c.you_own && !m.you && (confirm === m.id ? (
                <button disabled={busy} onClick={() => run(() => circlesAPI.removeMember(userId, c.id, m.id), `${m.name} was removed.`)}
                  className="text-sm font-semibold text-ink underline-offset-4 hover:underline">Remove?</button>
              ) : (
                <button aria-label={`Remove ${m.name}`} onClick={() => setConfirm(m.id)} className="rounded-full p-1 hover:bg-accent-surface">
                  <X size={14} />
                </button>
              ))}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-ink-soft">
        {c.you_own && (
          <button disabled={busy} onClick={() => run(() => circlesAPI.newCode(userId, c.id), 'New invite link made. The old one no longer works.')}
            className="inline-flex items-center gap-1 underline-offset-4 hover:underline"><RefreshCw size={13} /> New invite link</button>
        )}
        {confirm === 'leave' ? (
          <button disabled={busy} onClick={() => run(() => circlesAPI.leave(userId, c.id), `You left ${c.name}.`)}
            className="font-semibold text-ink underline-offset-4 hover:underline">Leave this circle?</button>
        ) : (
          <button onClick={() => setConfirm('leave')} className="underline-offset-4 hover:underline">Leave circle</button>
        )}
      </div>
    </section>
  );
}

function InviteFriends({ userId }) {
  const { data: r } = useQuery({ queryKey: ['referrals', userId], queryFn: () => engagementAPI.referrals(userId), enabled: !!userId });
  if (!r) return null;
  const link = inviteLink(r.code);
  const share = async () => {
    const text = `I'm learning on Delta. Join with my link and we both get a streak freeze once you've studied on ${r.days_needed} days: ${link}`;
    if (navigator.share) {
      try { await navigator.share({ text }); return; } catch (err) { if (err?.name === 'AbortError') return; }
    }
    copy(text, 'Invite message copied.');
  };
  return (
    <section className={`${card} p-5 sm:p-6`}>
      <h2 className="flex items-center gap-2 font-display text-2xl font-semibold text-ink"><Gift size={20} className="text-reward" /> Invite a friend</h2>
      <p className="mt-1 text-sm text-ink-soft">
        When your friend joins with your link and studies on {r.days_needed} days, you both get a streak freeze.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <code className="min-w-0 max-w-full truncate rounded-lg bg-accent-surface px-3 py-1.5 text-sm text-ink">{link}</code>
        <button onClick={share} className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-1.5 text-sm font-semibold text-paper hover:opacity-90">
          <Share2 size={14} /> Share
        </button>
      </div>
      {r.invited.length > 0 && (
        <ul className="mt-4 divide-y divide-rule">
          {r.invited.map((f, i) => (
            <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span className="text-ink">{f.name}</span>
              <span className={f.rewarded ? 'font-semibold text-reward' : 'text-ink-soft'}>
                {f.rewarded ? 'Freeze earned for you both' : `Joined · ${r.days_needed} study days unlock the reward`}
              </span>
            </li>
          ))}
        </ul>
      )}
      {r.linked_to && (
        <p className="mt-3 text-xs text-ink-soft">
          You joined with {r.linked_to.name}'s invite{r.linked_to.rewarded ? ' and you both earned a freeze.' : '.'}
        </p>
      )}
    </section>
  );
}

export default function Circles() {
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['circles', userId], queryFn: () => circlesAPI.list(userId), enabled: !!userId,
  });
  const setData = (d) => queryClient.setQueryData(['circles', userId], d);

  const create = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      setData(await circlesAPI.create(userId, name));
      setName('');
      toast.success('Circle started. Copy the invite link and send it to friends.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not start the circle.');
    } finally {
      setCreating(false);
    }
  };

  if (isLoading) return <main className="min-h-screen bg-bone flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-ink-soft" /></main>;
  if (isError || !data) {
    return (
      <main className="min-h-screen bg-bone px-4 pt-24 text-center">
        <p className="text-ink-soft">We couldn't load your circles.</p>
        <button onClick={() => refetch()} className="mt-3 rounded-full border border-ink px-4 py-2 text-sm text-ink">Try again</button>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-20 sm:pt-24">
      <div className="mx-auto grid max-w-2xl grid-cols-1 gap-4">
        <Link to="/today" className="inline-flex items-center gap-1 text-sm text-ink-soft hover:text-ink"><ArrowLeft size={14} /> Today</Link>
        <header>
          <h1 className="flex items-center gap-2 font-display text-3xl font-semibold text-ink"><Users size={26} className="text-reward" /> Study circles</h1>
          <p className="mt-1 text-ink-soft">A few friends, one shared goal each week, and a streak you keep together.</p>
        </header>

        {data.circles.map((c) => <CircleCard key={c.id} userId={userId} c={c} onChange={setData} />)}

        {data.circles.length < data.max_circles && (
          <form onSubmit={create} className={`${card} p-5 sm:p-6`}>
            <h2 className="font-display text-xl font-semibold text-ink">{data.circles.length ? 'Start another circle' : 'Start a circle'}</h2>
            <p className="mt-1 text-sm text-ink-soft">Up to {data.max_members} people. {MEMBERS_SEE} You can leave any time.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <label htmlFor="circle-name" className="sr-only">Circle name</label>
              <input id="circle-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} required
                placeholder="e.g. Placement prep crew" className="min-w-0 flex-1 rounded-lg border border-rule bg-paper px-3 py-2 text-ink" />
              <button type="submit" disabled={creating || !name.trim()}
                className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-60">
                {creating && <Loader2 size={14} className="animate-spin" />} Start
              </button>
            </div>
          </form>
        )}

        <InviteFriends userId={userId} />
      </div>
    </main>
  );
}

export { MEMBERS_SEE };
