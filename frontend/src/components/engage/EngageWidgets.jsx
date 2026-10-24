import React from 'react';
import { Flame, Snowflake } from 'lucide-react';

// Small, reusable pieces of the daily habit UI. Rewards use the warm "reward"
// token only; scores and errors never do (see DESIGN.md, Rewards).

export function StreakFlame({ streak = 0, freezes = 0, done = false, compact = false }) {
  const lit = streak > 0;
  return (
    <div className="flex items-center gap-2" title={lit ? `${streak}-day streak` : 'Start a streak today'}>
      <span
        className={`inline-flex items-center justify-center rounded-full ${compact ? 'w-7 h-7' : 'w-11 h-11'} ${lit ? 'bg-reward/15 text-reward' : 'bg-accent-surface text-ink-soft'}`}
      >
        <Flame size={compact ? 15 : 22} fill={done ? 'currentColor' : 'none'} aria-hidden="true" />
      </span>
      <span className="leading-tight">
        <span className={`block font-semibold text-ink ${compact ? 'text-sm' : 'text-xl'}`}>{streak}</span>
        {!compact && <span className="block text-xs text-ink-soft">day streak</span>}
      </span>
      {!compact && freezes > 0 && (
        <span className="ml-1 inline-flex items-center gap-1 text-xs text-ink-soft" title="Streak freezes: a missed day is covered automatically">
          <Snowflake size={13} aria-hidden="true" /> {freezes}
        </span>
      )}
    </div>
  );
}

export function DailyGoalRing({ xpToday = 0, goalXp = 20, minutes = 10 }) {
  const pct = Math.max(0, Math.min(1, goalXp ? xpToday / goalXp : 0));
  const r = 18;
  const c = 2 * Math.PI * r;
  const met = pct >= 1;
  return (
    <div className="flex items-center gap-2" title={`Daily goal: ${minutes} minutes`}>
      <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
        <circle cx="22" cy="22" r={r} fill="none" stroke="rgb(var(--rule-rgb))" strokeWidth="5" />
        <circle
          cx="22" cy="22" r={r} fill="none" strokeWidth="5" strokeLinecap="round"
          stroke={met ? 'rgb(var(--reward-rgb))' : 'rgb(var(--ink-rgb))'}
          strokeDasharray={`${pct * c} ${c}`} transform="rotate(-90 22 22)"
          style={{ transition: 'stroke-dasharray 600ms ease' }}
        />
      </svg>
      <span className="leading-tight">
        <span className="block text-xl font-semibold text-ink">{met ? 'Done!' : `${Math.round(pct * 100)}%`}</span>
        <span className="block text-xs text-ink-soft">today's goal</span>
      </span>
    </div>
  );
}

export function LevelBar({ level }) {
  if (!level) return null;
  const pct = level.xp_for_next ? Math.min(100, Math.round((100 * level.xp_into_level) / level.xp_for_next)) : 0;
  return (
    <div className="min-w-[150px] flex-1" title={`${level.xp_into_level} / ${level.xp_for_next} XP to the next level`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-semibold text-ink">Level {level.level}</span>
        <span className="text-xs text-ink-soft">{level.name}</span>
      </div>
      <div className="mt-1.5 h-2 w-full rounded-full bg-accent-surface overflow-hidden">
        <div className="h-full rounded-full bg-reward" style={{ width: `${pct}%`, transition: 'width 600ms ease' }} />
      </div>
    </div>
  );
}

const DAY = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export function WeekStrip({ week = [] }) {
  return (
    <ol className="flex gap-2" aria-label="Your last 7 days">
      {week.map((d) => {
        const day = DAY[new Date(`${d.date}T12:00:00`).getDay()];
        const cls = d.goal_met ? 'bg-reward text-paper' : d.active ? 'bg-reward/25 text-ink' : d.protected ? 'bg-accent-surface text-ink-soft' : 'bg-paper text-ink-soft border border-rule';
        const label = d.goal_met ? 'goal met' : d.active ? 'studied' : d.protected ? 'protected (freeze or break)' : 'rest day';
        return (
          <li key={d.date} className="flex flex-col items-center gap-1">
            <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold ${cls}`} title={`${d.date}: ${label}`}>
              {d.protected && !d.active ? <Snowflake size={13} aria-hidden="true" /> : day}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
