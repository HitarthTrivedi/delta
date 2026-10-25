import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, CheckCircle2, Lightbulb, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { quickPracticeAPI } from '../lib/api';
import { refreshEngagement } from '../hooks/useEngagement';
import { celebrate } from '../lib/celebrate';

// Quick 5: five questions, untimed, an explanation after every answer.
// A wrong answer is "not quite", never red: it comes back in a few days.

export default function QuickPractice() {
  const userId = useAuthStore((s) => s.userId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [set, setSet] = useState(null);
  const [error, setError] = useState(null);
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState(null);
  const [result, setResult] = useState(null);
  const [right, setRight] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!userId) return;
    quickPracticeAPI.get(userId)
      .then(setSet)
      .catch((err) => setError(err?.response?.data?.detail || 'Could not load your questions. Try again in a moment.'));
  }, [userId]);

  if (error) {
    return (
      <main className="min-h-screen bg-bone px-4 pt-24 text-center">
        <p className="text-ink-soft">{error}</p>
        <button onClick={() => navigate('/today')} className="mt-4 rounded-full border border-ink px-4 py-2 text-sm text-ink">Back to Today</button>
      </main>
    );
  }
  if (!set) {
    return (
      <main className="min-h-screen bg-bone flex flex-col items-center justify-center gap-3 px-4 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-ink-soft" />
        <p className="text-sm text-ink-soft">Aria is picking five questions for you…</p>
      </main>
    );
  }

  const items = set.items;
  const item = items[index];
  const isLast = index === items.length - 1;

  const choose = async (choice) => {
    if (result || busy) return;
    setPicked(choice);
    setBusy(true);
    try {
      const r = await quickPracticeAPI.answer(userId, item.id, choice);
      setResult(r);
      if (r.correct) setRight((n) => n + 1);
      if (r.set_complete) {
        const award = r.engagement || {};
        // The answer endpoint already awarded the XP: refresh the shared numbers quietly.
        await refreshEngagement(queryClient, userId, { size: 'none' });
        celebrate({
          size: 'big',
          title: r.set_complete.perfect ? 'Perfect 5/5!' : `${r.set_complete.correct}/5. Nice work!`,
          xp: award.awarded,
          subtitle: award.awarded ? `+${award.awarded} XP` : undefined,
          streak: award.streak,
          streakUp: true,
          goalMet: !!award.goal_met,
          levelUp: null,
          badge: award.badges?.[0] || null,
          questsDone: !!award.quests_done,
          challenge: award.challenge_won || null,
          message: 'Questions you missed will come back in a day or two. That spacing is what makes it stick.',
          cta: 'Back to Today',
        });
      }
    } catch (err) {
      toast.error('Could not check that answer. Try again.');
      setPicked(null);
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    if (isLast) {
      navigate('/today');
      return;
    }
    setIndex((i) => i + 1);
    setPicked(null);
    setResult(null);
  };

  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-20 sm:pt-24">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between gap-3">
          <button onClick={() => navigate('/today')} className="inline-flex items-center gap-1 text-sm text-ink-soft hover:text-ink">
            <ArrowLeft size={15} /> Today
          </button>
          <span className="text-sm text-ink-soft">Question {index + 1} of {items.length} · no timer</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-accent-surface" aria-hidden="true">
          <div className="h-full rounded-full bg-reward transition-all" style={{ width: `${(100 * (index + (result ? 1 : 0))) / items.length}%` }} />
        </div>

        <section className="mt-6 rounded-2xl border border-rule bg-paper p-5 sm:p-7">
          {item.skill && <p className="text-xs font-semibold text-ink-soft">{item.skill}</p>}
          <h1 className="mt-1 text-xl font-semibold leading-snug text-ink sm:text-2xl">{item.question}</h1>
          <div className="mt-5 grid gap-3">
            {item.options.map((opt, i) => {
              const isAnswer = result && i === result.answer_index;
              const isWrongPick = result && i === picked && !result.correct;
              const cls = isAnswer
                ? 'border-emerald-600 bg-emerald-50 text-ink dark:bg-emerald-900/30'
                : isWrongPick
                  ? 'border-amber-500 bg-amber-50 text-ink dark:bg-amber-900/30'
                  : 'border-rule bg-paper text-ink hover:border-ink-soft';
              return (
                <button key={i} onClick={() => choose(i)} disabled={!!result || busy}
                  className={`w-full rounded-xl border-2 px-4 py-3.5 text-left text-base transition ${cls}`}>
                  {opt}
                </button>
              );
            })}
          </div>

          {result && (
            <div className="mt-5 rounded-xl bg-accent-surface p-4">
              <p className="flex items-center gap-2 font-semibold text-ink">
                {result.correct
                  ? <><CheckCircle2 size={18} className="text-emerald-600" /> Right!</>
                  : <><Lightbulb size={18} className="text-amber-600" /> Not quite. Here's the idea:</>}
              </p>
              {result.explanation && <p className="mt-1.5 text-sm leading-relaxed text-ink">{result.explanation}</p>}
              <button onClick={next} className="mt-4 inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:opacity-90">
                {isLast ? 'Finish' : 'Next question'} <ArrowRight size={15} />
              </button>
            </div>
          )}
        </section>
        <p className="mt-4 text-center text-sm text-ink-soft">{right} right so far. Every answer helps Aria pick tomorrow's questions.</p>
      </div>
    </main>
  );
}
