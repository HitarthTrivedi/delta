import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Loader2, Medal } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { engagementAPI } from '../lib/api';
import { engagementKey } from '../hooks/useEngagement';
import { daysLeftText } from '../components/engage/EngageWidgets';

// Opt-in weekly league: ranked by XP earned this week (effort, never scores).
// Copy rules: friendly, no shame for the bottom of the table.

const card = 'rounded-2xl border border-rule bg-paper';

const OUTCOME = {
  promoted: (t) => `Last week you moved up. Welcome to ${t}!`,
  stayed: (t) => `You stayed in ${t} last week. New week, fresh table.`,
  demoted: (t) => `You're in ${t} this week. A fresh start: every XP counts.`,
};

export default function League() {
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const { data: league, isLoading, isError, refetch } = useQuery({
    queryKey: ['league', userId],
    queryFn: () => engagementAPI.league(userId),
    enabled: !!userId,
    staleTime: 60 * 1000,
  });

  const setOptIn = async (enabled) => {
    setBusy(true);
    try {
      const board = await engagementAPI.setLeague(userId, enabled);
      queryClient.setQueryData(['league', userId], board);
      queryClient.invalidateQueries({ queryKey: engagementKey(userId) });
      toast.success(enabled ? `You're in the ${board.tier_name} league.` : 'You left leagues. Nobody can see you there now.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not update leagues.');
    } finally {
      setBusy(false);
    }
  };

  if (isLoading) {
    return <main className="min-h-screen bg-bone flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-ink-soft" /></main>;
  }
  if (isError || !league) {
    return (
      <main className="min-h-screen bg-bone px-4 pt-24 text-center">
        <p className="text-ink-soft">We couldn't load your league.</p>
        <button onClick={() => refetch()} className="mt-3 rounded-full border border-ink px-4 py-2 text-sm text-ink">Try again</button>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-20 sm:pt-24">
      <div className="mx-auto grid max-w-2xl grid-cols-1 gap-4">
        <Link to="/today" className="inline-flex items-center gap-1 text-sm text-ink-soft hover:text-ink"><ArrowLeft size={14} /> Today</Link>

        {!league.opted_in ? (
          <section className={`${card} p-6`}>
            <h1 className="font-display text-3xl font-semibold text-ink">Weekly leagues</h1>
            <p className="mt-2 text-ink-soft">
              Join up to 20 learners for a friendly week. The table is ranked by the XP you earn that week, so steady
              effort counts, never test scores. The top of the table moves up a league.
            </p>
            <p className="mt-2 text-sm text-ink-soft">
              Others in your league see only your first name, last initial and weekly XP. You can leave any time.
            </p>
            <button onClick={() => setOptIn(true)} disabled={busy}
              className="mt-5 inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-60">
              {busy ? <Loader2 size={15} className="animate-spin" /> : <Medal size={15} />} Join this week's league
            </button>
          </section>
        ) : (
          <>
            <section className={`${card} p-5 sm:p-6`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h1 className="flex items-center gap-2 font-display text-3xl font-semibold text-ink">
                  <Medal size={26} className="text-reward" aria-hidden="true" /> {league.tier_name} league
                </h1>
                <span className="text-sm text-ink-soft">{daysLeftText(league.days_left)}</span>
              </div>
              <ol className="mt-4 flex flex-wrap gap-1.5" aria-label="Leagues">
                {league.tiers.map((t, i) => (
                  <li key={t} aria-current={i === league.tier ? 'true' : undefined}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${i === league.tier ? 'bg-reward/15 text-reward' : i < league.tier ? 'bg-accent-surface text-ink' : 'bg-accent-surface text-ink-soft'}`}>
                    {t}
                  </li>
                ))}
              </ol>
              {league.last_week && <p className="mt-4 text-sm text-ink">{OUTCOME[league.last_week.outcome]?.(league.tier_name)}</p>}
              <p className="mt-2 text-sm text-ink-soft">
                {league.move_up > 0 ? `Top ${league.move_up} move up.` : 'This is the top league: enjoy it!'}{' '}
                {league.move_down > 0
                  ? `The last ${league.move_down} may move down, but never in your first two weeks or if you studied on 3 or more days.`
                  : 'Nobody moves down from this table.'}
              </p>
            </section>

            <section className={`${card} p-2 sm:p-3`}>
              <ol>
                {league.rows.map((r) => {
                  const upZone = r.rank <= league.move_up;
                  const downZone = league.move_down > 0 && r.rank > league.rows.length - league.move_down;
                  return (
                    <li key={r.rank}
                      className={`flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 ${r.you ? 'bg-reward/10' : ''}`}>
                      <span className="flex min-w-0 items-center gap-3">
                        <span className={`w-7 shrink-0 text-right text-sm font-semibold ${upZone ? 'text-reward' : 'text-ink-soft'}`}>{r.rank}</span>
                        <span className={`truncate ${r.you ? 'font-semibold text-ink' : 'text-ink'}`}>{r.you ? `${r.name} (you)` : r.name}</span>
                      </span>
                      <span className="shrink-0 text-sm text-ink-soft">
                        {r.xp} XP{upZone ? ' · moving up' : downZone && r.you ? ' · a little more keeps you here' : ''}
                      </span>
                    </li>
                  );
                })}
              </ol>
              {league.rows.length < 5 && (
                <p className="px-3 pb-2 pt-1 text-xs text-ink-soft">More learners join as the week goes on.</p>
              )}
            </section>

            <button onClick={() => setOptIn(false)} disabled={busy}
              className="justify-self-center text-sm text-ink-soft underline-offset-4 hover:underline">
              Leave leagues
            </button>
          </>
        )}
      </div>
    </main>
  );
}
