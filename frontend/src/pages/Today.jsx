import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Bell, CalendarClock, CheckCircle2, Clock, Coffee, Flame, Gift, Loader2, Medal, PauseCircle, Snowflake, Sparkles, Users } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { useUserWithSkills } from '../hooks/useUser';
import { engagementKey, useEngagement } from '../hooks/useEngagement';
import { useCareerContext } from '../hooks/useCareerOS';
import { getTaskProgress } from '../lib/taskProgress';
import { circlesAPI, collegeAPI, engagementAPI } from '../lib/api';
import { clearReferral, pendingReferral } from '../lib/referral';
import { enablePush, pushSupported } from '../lib/push';
import InterviewerAvatar from '../components/interview/InterviewerAvatar';
import { DailyGoalRing, LevelBar, StreakFlame, WeekStrip, daysLeftText } from '../components/engage/EngageWidgets';

// Home after sign-in: one clear next step, the daily habit at a glance, and
// Aria as a friendly guide. Copy rules: warm, no guilt, no false urgency.

const card = 'rounded-2xl border border-rule bg-paper';
const LEAGUE_OFFER_KEY = 'delta_league_offer_dismissed';
const TIME_HINT_KEY = 'delta_time_hint_dismissed';
const QUEST_ACTION = {
  quick5: { to: '/today/quick', label: 'Start' },
  plan_task: { to: '/roadmap', label: 'Open plan' },
  practice: { to: '/practice', label: 'Practise' },
  two_kinds: { to: '/practice', label: 'Practise' },
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

function ariaLine(e) {
  if (!e) return '';
  if (e.on_break) return "You're on a break. Your streak is safe. Rest well!";
  if (e.repair) return `Let's win back your ${e.repair.streak}-day streak: meet your goal today and tomorrow.`;
  if (e.goal_met_today) return "Today's goal is done. Anything more is a bonus!";
  if (e.done_today) return 'Nice start today! A little more and your goal is done.';
  if (e.streak > 0) return `Five minutes today keeps your ${e.streak}-day streak going.`;
  return "Let's start small: five questions, about five minutes.";
}

function HabitSetup({ userId, e, onDone }) {
  const [minutes, setMinutes] = useState(e.goal_minutes || 10);
  const [time, setTime] = useState(e.study_time || '20:00');
  const [remind, setRemind] = useState(true);
  const [push, setPush] = useState(false);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await engagementAPI.update(userId, { goal_minutes: minutes, study_time: time });
      if (remind) {
        let channel = 'email';
        if (push) {
          try {
            await enablePush(userId);
            channel = 'both';
          } catch (err) {
            toast.message(err.message);
          }
        }
        await engagementAPI.setReminders(userId, true, channel);
      }
      onDone();
      toast.success("You're all set. See you at " + time + '!');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not save. Try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={`${card} p-5 sm:p-6`}>
      <h2 className="font-display text-2xl font-semibold text-ink">Make it a habit</h2>
      <p className="mt-1 text-sm text-ink-soft">People who pick a time stick with it. You can change this any time.</p>
      <div className="mt-4">
        <p className="text-sm font-semibold text-ink">How much time a day?</p>
        <div className="mt-2 flex flex-wrap gap-2" role="radiogroup" aria-label="Daily goal">
          {[{ m: 5, l: '5 min · Easy' }, { m: 10, l: '10 min · Regular' }, { m: 20, l: '20 min · Serious' }].map(({ m, l }) => (
            <button key={m} role="radio" aria-checked={minutes === m} onClick={() => setMinutes(m)}
              className={`rounded-full border px-4 py-2 text-sm font-semibold ${minutes === m ? 'border-ink bg-ink text-paper' : 'border-rule bg-paper text-ink hover:border-ink-soft'}`}>
              {l}
            </button>
          ))}
        </div>
      </div>
      <label className="mt-4 block text-sm font-semibold text-ink" htmlFor="study-time">When will you study?</label>
      <input id="study-time" type="time" value={time} onChange={(ev) => setTime(ev.target.value)}
        className="mt-2 rounded-lg border border-rule bg-paper px-3 py-2 text-ink" />
      <label className="mt-4 flex items-start gap-3 text-sm text-ink">
        <input type="checkbox" className="mt-1" checked={remind} onChange={() => setRemind((v) => !v)} />
        <span>Send me one friendly reminder at this time on days I haven't studied yet. I can turn it off any time.</span>
      </label>
      {remind && pushSupported() && (
        <label className="mt-2 ml-7 flex items-start gap-3 text-sm text-ink-soft">
          <input type="checkbox" className="mt-1" checked={push} onChange={() => setPush((v) => !v)} />
          <span>Also as a browser notification on this device</span>
        </label>
      )}
      <button onClick={save} disabled={saving}
        className="mt-5 inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-60">
        {saving ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />} Save my plan
      </button>
    </section>
  );
}

function BreakControl({ userId, e, onChange }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const run = async (fn) => {
    setBusy(true);
    try {
      onChange(await fn());
      setOpen(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not update your break.');
    } finally {
      setBusy(false);
    }
  };
  if (e.on_break) {
    return (
      <button onClick={() => run(() => engagementAPI.endBreak(userId))} disabled={busy}
        className="inline-flex items-center gap-1.5 text-sm text-ink-soft underline-offset-4 hover:underline">
        <Coffee size={14} /> On a break until {new Date(`${e.break_until}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}. End it early
      </button>
    );
  }
  return (
    <div>
      <button onClick={() => setOpen((v) => !v)} className="inline-flex items-center gap-1.5 text-sm text-ink-soft underline-offset-4 hover:underline">
        <PauseCircle size={14} /> Exams or travel? Pause your streak
      </button>
      {open && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-sm text-ink-soft">Pause for</span>
          {[1, 2, 3, 7].filter((d) => d <= e.break_days_left).map((d) => (
            <button key={d} disabled={busy} onClick={() => run(() => engagementAPI.startBreak(userId, d))}
              className="rounded-full border border-rule px-3 py-1 text-sm text-ink hover:border-ink-soft">
              {d} day{d > 1 ? 's' : ''}
            </button>
          ))}
          {e.break_days_left === 0 && <span className="text-sm text-ink-soft">No break days left this month.</span>}
        </div>
      )}
    </div>
  );
}

function WeeklyChallenge({ c }) {
  if (!c) return null;
  return (
    <div className="mt-3 rounded-xl bg-accent-surface px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Snowflake size={15} className="text-reward" aria-hidden="true" /> Weekly challenge
        </span>
        <span className="flex gap-1" role="img" aria-label={`${Math.min(c.days_done, c.needed)} of ${c.needed} days`}>
          {Array.from({ length: c.needed }, (_, i) => (
            <span key={i} className={`h-2.5 w-2.5 rounded-full ${i < c.days_done ? 'bg-reward' : 'bg-ink/20'}`} />
          ))}
        </span>
      </div>
      <p className="mt-1 text-xs text-ink-soft">
        {c.won
          ? (c.reward === 'freeze' ? 'Won! A streak freeze is yours.' : `Won! +${c.reward_xp} XP (your freezes were already full).`)
          : `Finish your quests on ${c.needed} days this week to earn a streak freeze.`}
      </p>
    </div>
  );
}

function LeagueCard({ userId, e }) {
  const queryClient = useQueryClient();
  const [joining, setJoining] = useState(false);
  const [dismissed, setDismissed] = useState(() => {
    try { return localStorage.getItem(LEAGUE_OFFER_KEY) === '1'; } catch { return false; }
  });
  const { data: league } = useQuery({
    queryKey: ['league', userId],
    queryFn: () => engagementAPI.league(userId),
    enabled: !!userId && !!e.leagues_opt_in,
    staleTime: 60 * 1000,
  });

  if (e.leagues_opt_in) {
    if (!league?.opted_in) return null;
    const me = league.rows.find((r) => r.you);
    return (
      <Link to="/league" className={`${card} flex items-center justify-between gap-3 p-4 hover:border-ink-soft`}>
        <span className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-reward/15 text-reward"><Medal size={18} aria-hidden="true" /></span>
          <span>
            <span className="block text-sm font-semibold text-ink">{league.tier_name} league</span>
            <span className="block text-xs text-ink-soft">
              {me ? `You're #${me.rank} of ${league.rows.length}` : 'Your league'} · {daysLeftText(league.days_left)}
            </span>
          </span>
        </span>
        <ArrowRight size={18} className="text-ink-soft" aria-hidden="true" />
      </Link>
    );
  }
  if (dismissed || e.streak < 3) return null;

  const join = async () => {
    setJoining(true);
    try {
      const board = await engagementAPI.setLeague(userId, true);
      queryClient.setQueryData(['league', userId], board);
      queryClient.invalidateQueries({ queryKey: engagementKey(userId) });
      toast.success(`You're in the ${board.tier_name} league. Have fun!`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not join right now.');
    } finally {
      setJoining(false);
    }
  };
  const notNow = () => {
    try { localStorage.setItem(LEAGUE_OFFER_KEY, '1'); } catch { /* private mode: just hide it for now */ }
    setDismissed(true);
  };
  return (
    <section className={`${card} p-4`}>
      <p className="flex items-center gap-2 text-sm font-semibold text-ink"><Medal size={16} className="text-reward" aria-hidden="true" /> Fancy a friendly weekly league?</p>
      <p className="mt-1 text-sm text-ink-soft">
        Up to 20 learners, ranked by the XP they earn that week: effort counts, never test scores.
        Others see only your first name and last initial, and you can leave any time.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button onClick={join} disabled={joining}
          className="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-1.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-60">
          {joining && <Loader2 size={14} className="animate-spin" />} Join
        </button>
        <button onClick={notNow} className="rounded-full px-4 py-1.5 text-sm text-ink-soft hover:text-ink">Not now</button>
      </div>
    </section>
  );
}

function ReferralCard({ userId }) {
  const queryClient = useQueryClient();
  const [code, setCode] = useState(() => pendingReferral());
  const [busy, setBusy] = useState(false);
  const { data } = useQuery({
    queryKey: ['referral-preview', code],
    queryFn: () => engagementAPI.referralPreview(userId, code),
    enabled: !!userId && !!code,
    retry: false,
  });
  const done = () => { clearReferral(); setCode(null); };
  useEffect(() => {
    if (data && !data.eligible) { clearReferral(); setCode(null); } // own link, old account, already linked...
  }, [data]);
  if (!code || !data || !data.eligible) return null;
  const link = async () => {
    setBusy(true);
    try {
      await engagementAPI.claimReferral(userId, code);
      queryClient.invalidateQueries({ queryKey: ['referrals', userId] });
      toast.success(`Linked with ${data.inviter}. Study on ${data.days_needed} days and you both get a streak freeze.`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not link up.');
    } finally {
      setBusy(false);
      done();
    }
  };
  return (
    <section className={`${card} p-4`}>
      <p className="flex items-center gap-2 text-sm font-semibold text-ink"><Gift size={16} className="text-reward" aria-hidden="true" /> {data.inviter} invited you to Delta</p>
      <p className="mt-1 text-sm text-ink-soft">
        Link up and you both get a streak freeze once you've studied on {data.days_needed} days.
        {' '}{data.inviter} will see your first name and last initial, and when you both earn it.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button onClick={link} disabled={busy}
          className="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-1.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-60">
          {busy && <Loader2 size={14} className="animate-spin" />} Link up
        </button>
        <button onClick={done} className="rounded-full px-4 py-1.5 text-sm text-ink-soft hover:text-ink">No thanks</button>
      </div>
    </section>
  );
}

function CollegeCard({ userId }) {
  const { data } = useQuery({ queryKey: ['college-state', userId], queryFn: () => collegeAPI.studentState(userId),
    enabled: !!userId, staleTime: 5 * 60 * 1000 });
  if (!data || data.membership || !data.suggestion) return null;
  return (
    <Link to="/join-college" className={`${card} flex items-center justify-between gap-3 p-4 hover:border-ink-soft`}>
      <span>
        <span className="block text-sm font-semibold text-ink">{data.suggestion.college} is on Delta</span>
        <span className="block text-xs text-ink-soft">Your college gave you a seat. Join to get its plan and practice, and campus recruiters.</span>
      </span>
      <ArrowRight size={18} className="shrink-0 text-ink-soft" aria-hidden="true" />
    </Link>
  );
}

function CollegeTestsCard({ userId }) {
  const { data } = useQuery({ queryKey: ['college-tests', userId], queryFn: () => collegeAPI.studentTests(userId),
    enabled: !!userId, staleTime: 60 * 1000 });
  const open = (data?.tests || []).filter((t) => t.open && t.status !== 'done');
  if (!open.length) return null;
  return (
    <section className={`${card} p-4`}>
      <p className="m-0 text-xs font-semibold uppercase tracking-[0.12em] text-ink-soft">From your college</p>
      <ul className="m-0 mt-2 p-0 list-none grid gap-2">
        {open.map((t) => (
          <li key={t.id}>
            <Link to={`/practice/theory?assignment=${t.id}`} className="flex items-center justify-between gap-3 hover:underline">
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-ink">{t.title}</span>
                <span className="block text-xs text-ink-soft">
                  {t.questions} questions{t.timed ? ', timed' : ''}{t.due_date ? ` · due ${new Date(`${t.due_date}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}` : ''}
                  {t.status === 'started' ? ' · in progress' : ''}
                </span>
              </span>
              <ArrowRight size={18} className="shrink-0 text-ink-soft" aria-hidden="true" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function FriendsCard({ userId }) {
  const { data } = useQuery({ queryKey: ['circles', userId], queryFn: () => circlesAPI.list(userId), enabled: !!userId, staleTime: 60 * 1000 });
  if (!data) return null;
  const c = data.circles[0];
  return (
    <Link to="/circles" className={`${card} flex items-center justify-between gap-3 p-4 hover:border-ink-soft`}>
      <span className="flex min-w-0 items-center gap-3">
        <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-reward/15 text-reward"><Users size={18} aria-hidden="true" /></span>
        {c ? (
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-ink">{c.name}</span>
            <span className="flex items-center gap-1 text-xs text-ink-soft">
              {c.streak > 0 && <><Flame size={12} className="text-reward" aria-hidden="true" /> {c.streak}-day circle streak · </>}
              {c.week.done}/{c.week.target} study days together this week
            </span>
          </span>
        ) : (
          <span>
            <span className="block text-sm font-semibold text-ink">Learn with friends</span>
            <span className="block text-xs text-ink-soft">Start a study circle, or invite a friend and you both get a streak freeze.</span>
          </span>
        )}
      </span>
      <ArrowRight size={18} className="shrink-0 text-ink-soft" aria-hidden="true" />
    </Link>
  );
}

function StudyTimeHint({ userId, e, onChange }) {
  const [dismissed, setDismissed] = useState(() => {
    try { return localStorage.getItem(TIME_HINT_KEY); } catch { return null; }
  });
  const [busy, setBusy] = useState(false);
  const hint = e.suggested_study_time;
  if (!hint || !e.study_time || dismissed === hint) return null;
  const keep = () => {
    try { localStorage.setItem(TIME_HINT_KEY, hint); } catch { /* just hide it for now */ }
    setDismissed(hint);
  };
  const move = async () => {
    setBusy(true);
    try {
      onChange(await engagementAPI.update(userId, { study_time: hint }));
      toast.success(`Your study time is now ${hint}.`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not change your study time.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className={`${card} flex flex-wrap items-center justify-between gap-3 p-4`}>
      <span className="flex items-center gap-2 text-sm text-ink">
        <Clock size={16} className="text-ink-soft" aria-hidden="true" /> You usually start around {hint}. Move your study time there?
      </span>
      <span className="flex gap-2">
        <button onClick={move} disabled={busy} className="rounded-full border border-ink px-4 py-1.5 text-sm font-semibold text-ink">Move to {hint}</button>
        <button onClick={keep} className="rounded-full px-3 py-1.5 text-sm text-ink-soft hover:text-ink">Keep {e.study_time}</button>
      </span>
    </section>
  );
}

export default function Today() {
  const userId = useAuthStore((s) => s.userId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: user } = useUserWithSkills(userId);
  const { data: e, isLoading, isError, refetch } = useEngagement(userId);
  const { data: context } = useCareerContext(userId);
  const [setupDone, setSetupDone] = useState(false);

  const openTasks = useMemo(() => {
    if (!context) return [];
    const { actions, checkedByIndex, skippedByIndex } = getTaskProgress(context, []);
    return actions.filter((_, i) => !checkedByIndex[i] && !skippedByIndex[i]).slice(0, 2);
  }, [context]);

  const setSummary = (s) => queryClient.setQueryData(engagementKey(userId), s);
  const firstName = (user?.name || '').split(' ')[0];

  if (isLoading) {
    return <main className="min-h-screen bg-bone flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-ink-soft" /></main>;
  }
  if (isError || !e) {
    return (
      <main className="min-h-screen bg-bone px-4 pt-24 text-center">
        <p className="text-ink-soft">We couldn't load your day. </p>
        <button onClick={() => refetch()} className="mt-3 rounded-full border border-ink px-4 py-2 text-sm text-ink">Try again</button>
      </main>
    );
  }

  const primary = !e.quick_done_today
    ? { label: "Start today's 5 minutes", to: '/today/quick', hint: 'Quick 5: five questions on your goals and weak spots' }
    : openTasks[0]
      ? { label: `Next: ${openTasks[0].title}`, to: '/roadmap', hint: 'A task from your plan this week' }
      : { label: 'Practise something new', to: '/practice', hint: 'A test, a mock interview or a coding problem' };

  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-20 sm:pt-24">
      <div className="mx-auto grid max-w-3xl grid-cols-1 gap-4">
        {/* Aria + greeting */}
        <section className="flex items-center gap-4">
          <div className="shrink-0"><InterviewerAvatar state="idle" size={76} getLevel={() => 0} /></div>
          <div>
            <h1 className="font-display text-3xl font-semibold leading-tight text-ink sm:text-4xl">
              {greeting()}{firstName ? `, ${firstName}` : ''}!
            </h1>
            <p className="mt-1 text-base text-ink-soft">{ariaLine(e)}</p>
          </div>
        </section>

        {/* The one next step */}
        <section className={`${card} p-5 sm:p-6`}>
          <button onClick={() => navigate(primary.to)}
            className="flex w-full items-center justify-between gap-4 rounded-xl bg-ink px-5 py-4 text-left text-paper hover:opacity-95">
            <span>
              <span className="block text-lg font-semibold">{primary.label}</span>
              <span className="block text-sm opacity-75">{primary.hint}</span>
            </span>
            <ArrowRight size={22} aria-hidden="true" />
          </button>
          <div className="mt-5 flex flex-wrap items-center gap-x-8 gap-y-4">
            <StreakFlame streak={e.streak} freezes={e.freezes} done={e.done_today} />
            <DailyGoalRing xpToday={e.xp_today} goalXp={e.goal_xp} minutes={e.goal_minutes} />
            <LevelBar level={e.level} />
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <WeekStrip week={e.week} />
            <BreakControl userId={userId} e={e} onChange={setSummary} />
          </div>
        </section>

        {e.repair && (
          <section className={`${card} flex items-start gap-3 p-4`}>
            <Sparkles size={18} className="mt-0.5 text-reward" aria-hidden="true" />
            <p className="text-sm text-ink">
              Your <strong>{e.repair.streak}-day streak</strong> can come back: meet your daily goal on {e.repair.needed} days
              ({e.repair.progress} done) by {new Date(`${e.repair.deadline}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long' })}.
            </p>
          </section>
        )}

        <ReferralCard userId={userId} />
        <CollegeCard userId={userId} />
        <CollegeTestsCard userId={userId} />

        {!e.study_time && !setupDone && (
          <HabitSetup userId={userId} e={e} onDone={() => { setSetupDone(true); queryClient.invalidateQueries({ queryKey: engagementKey(userId) }); }} />
        )}

        {/* Today's quests (three) + the weekly challenge */}
        {e.quests && (
          <section className={`${card} p-5 sm:p-6`}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <h2 className="text-sm font-semibold text-ink">Today's quests</h2>
              <span className="text-xs text-ink-soft">
                {e.quests.all_done ? `All done · +${e.quests.bonus_xp} XP earned` : `Finish all three for +${e.quests.bonus_xp} XP`}
              </span>
            </div>
            <ul className="mt-3 divide-y divide-rule">
              {e.quests.items.map((q) => {
                const action = QUEST_ACTION[q.key];
                return (
                  <li key={q.key} className="flex items-center justify-between gap-3 py-3">
                    <span className="flex min-w-0 items-center gap-3">
                      {q.done
                        ? <CheckCircle2 size={18} className="shrink-0 text-reward" aria-label="Done" />
                        : <span className="h-[18px] w-[18px] shrink-0 rounded-full border-2 border-rule" />}
                      <span className={q.done ? 'text-ink-soft' : 'text-ink'}>{q.title}</span>
                    </span>
                    {!q.done && (q.key === 'goal'
                      ? <span className="shrink-0 text-xs text-ink-soft">{e.xp_today}/{e.goal_xp} XP</span>
                      : action && <Link to={action.to} className="shrink-0 text-sm font-semibold text-ink underline-offset-4 hover:underline">{action.label}</Link>)}
                  </li>
                );
              })}
            </ul>
            <WeeklyChallenge c={e.quests.challenge} />
          </section>
        )}

        <LeagueCard userId={userId} e={e} />
        <FriendsCard userId={userId} />

        {/* From the plan (at most 2) */}
        <section className={`${card} p-5 sm:p-6`}>
          <h2 className="text-sm font-semibold text-ink">From your plan this week</h2>
          <ul className="mt-3 divide-y divide-rule">
            {openTasks.map((t) => (
              <li key={t.id || t.title} className="flex items-center justify-between gap-3 py-3">
                <span className="flex items-center gap-3 min-w-0">
                  <span className="h-[18px] w-[18px] shrink-0 rounded-full border-2 border-rule" />
                  <span className="truncate text-ink">{t.title}</span>
                </span>
                <Link to="/roadmap" className="shrink-0 text-sm font-semibold text-ink underline-offset-4 hover:underline">Open</Link>
              </li>
            ))}
            {context && openTasks.length === 0 && (
              <li className="py-3 text-sm text-ink-soft">Your plan tasks for this week are all done. Nice work!</li>
            )}
          </ul>
          <Link to="/roadmap" className="mt-2 inline-flex items-center gap-1 text-sm text-ink-soft underline-offset-4 hover:underline">
            <CalendarClock size={14} /> See this week's plan
          </Link>
        </section>

        <StudyTimeHint userId={userId} e={e} onChange={setSummary} />

        {e.study_time && !e.reminders_opt_in && (
          <section className={`${card} flex flex-wrap items-center justify-between gap-3 p-4`}>
            <span className="flex items-center gap-2 text-sm text-ink"><Bell size={16} className="text-ink-soft" /> Want one friendly reminder at {e.study_time}?</span>
            <button onClick={async () => {
              try { setSummary(await engagementAPI.setReminders(userId, true, 'email')); toast.success('Reminders on. You can turn them off any time.'); }
              catch (err) { toast.error(err?.response?.data?.detail || 'Could not turn on reminders.'); }
            }} className="rounded-full border border-ink px-4 py-1.5 text-sm font-semibold text-ink">Turn on</button>
          </section>
        )}
        {e.reminders_opt_in && (
          <p className="text-center text-xs text-ink-soft">
            Reminders are on for {e.study_time || 'the evening'}.{' '}
            <button className="underline underline-offset-4" onClick={async () => {
              try { setSummary(await engagementAPI.setReminders(userId, false)); toast.success('Reminders off.'); }
              catch { toast.error('Could not update reminders.'); }
            }}>Turn off</button>
          </p>
        )}
      </div>
    </main>
  );
}
