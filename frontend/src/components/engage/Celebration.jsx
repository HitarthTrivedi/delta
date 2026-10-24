import React, { useEffect, useMemo } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Flame, Sparkles, Trophy, X } from 'lucide-react';
import { useCelebration } from '../../lib/celebrate';
import InterviewerAvatar from '../interview/InterviewerAvatar';

// Earned moments only (server-confirmed XP). Small = a corner card that fades
// out; big = a short centered moment with Aria. Motion is skipped for users
// who prefer reduced motion; there is no sound.

function Confetti() {
  const pieces = useMemo(() => Array.from({ length: 26 }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    delay: Math.random() * 0.25,
    rotate: Math.random() * 360,
    drift: (Math.random() - 0.5) * 120,
    color: ['rgb(var(--reward-rgb))', 'rgb(var(--oxblood-rgb))', 'rgb(var(--ink-rgb))'][i % 3],
  })), []);
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      {pieces.map((p) => (
        <motion.span
          key={p.id}
          initial={{ y: -20, x: 0, opacity: 1, rotate: p.rotate }}
          animate={{ y: 420, x: p.drift, opacity: 0, rotate: p.rotate + 240 }}
          transition={{ duration: 1.6, delay: p.delay, ease: 'easeOut' }}
          style={{ position: 'absolute', top: 0, left: `${p.left}%`, width: 8, height: 12, borderRadius: 2, background: p.color }}
        />
      ))}
    </div>
  );
}

function lines(c) {
  const out = [];
  if (c.levelUp) out.push({ icon: Trophy, text: `Level ${c.levelUp.level}: ${c.levelUp.name}!` });
  if (c.goalMet) out.push({ icon: Sparkles, text: "Today's goal: done!" });
  if (c.streakUp && c.streak > 0) out.push({ icon: Flame, text: c.streak === 1 ? 'Streak started!' : `${c.streak}-day streak!` });
  return out;
}

export default function Celebration() {
  const current = useCelebration((s) => s.current);
  const clear = useCelebration((s) => s.clear);
  const reduce = useReducedMotion();

  useEffect(() => {
    if (!current) return undefined;
    const t = setTimeout(clear, current.size === 'big' ? 5000 : 3200);
    return () => clearTimeout(t);
  }, [current, clear]);

  const items = current ? lines(current) : [];
  const heading = current?.title || (current?.xp ? `+${current.xp} XP` : 'Nice work!');

  return (
    <AnimatePresence>
      {current && current.size === 'small' && (
        <motion.div
          key={current.id}
          role="status"
          initial={reduce ? { opacity: 0 } : { opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: reduce ? 0 : 12 }}
          className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[70] flex items-center gap-3 rounded-full border border-rule bg-paper px-4 py-2.5 shadow-lg"
        >
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-reward/15 text-reward">
            <Sparkles size={16} aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold text-ink">{heading}</span>
          {items[0] && <span className="text-sm text-ink-soft">{items[0].text}</span>}
        </motion.div>
      )}
      {current && current.size === 'big' && (
        <motion.div
          key={current.id}
          className="fixed inset-0 z-[70] flex items-center justify-center bg-ink/30 px-4"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={clear}
        >
          <motion.div
            role="dialog" aria-modal="true" aria-label="Celebration"
            onClick={(e) => e.stopPropagation()}
            initial={reduce ? { opacity: 0 } : { scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            className="relative w-full max-w-sm overflow-hidden rounded-2xl border border-rule bg-paper p-7 text-center shadow-2xl"
          >
            {!reduce && <Confetti />}
            <button onClick={clear} aria-label="Close" className="absolute right-3 top-3 rounded-full p-1.5 text-ink-soft hover:bg-accent-surface">
              <X size={16} />
            </button>
            <div className="mx-auto mb-2 w-[96px]">
              <InterviewerAvatar state="speaking" size={96} getLevel={() => 0.25} />
            </div>
            <p className="font-display text-3xl font-semibold text-ink">{heading}</p>
            {current.subtitle && <p className="mt-1 text-sm text-ink-soft">{current.subtitle}</p>}
            <ul className="mt-4 space-y-2">
              {items.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center justify-center gap-2 text-ink">
                  <Icon size={17} className="text-reward" aria-hidden="true" /> <span className="font-semibold">{text}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm text-ink-soft">{current.message || 'Aria: "That\'s how habits are built. See you tomorrow!"'}</p>
            <button onClick={clear} className="mt-5 w-full rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper hover:opacity-90">
              {current.cta || 'Keep going'}
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
