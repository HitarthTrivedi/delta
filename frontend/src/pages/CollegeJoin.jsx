import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { GraduationCap, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { collegeAPI } from '../lib/api';

// A student takes their college seat: by the batch join link/code, or by their
// college email. Says plainly what the college will see before they join.

const PROGRAM = { placement_6m: '6-month placement-ready plan', first_year_4y: 'From-first-year track' };

export default function CollegeJoin() {
  const { code: codeParam } = useParams();
  const userId = useAuthStore((s) => s.userId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [code, setCode] = useState('');
  const [roll, setRoll] = useState('');
  const [busy, setBusy] = useState(false);

  const preview = useQuery({
    queryKey: ['college-preview', codeParam], queryFn: () => collegeAPI.preview(codeParam), enabled: !!codeParam, retry: false,
  });
  const state = useQuery({ queryKey: ['college-state', userId], queryFn: () => collegeAPI.studentState(userId), enabled: !!userId });

  const done = (res) => {
    queryClient.invalidateQueries({ queryKey: ['consent', userId] });
    queryClient.setQueryData(['college-state', userId], res);
    const m = res.membership;
    toast.success(m?.status === 'pending'
      ? `Request sent. ${m.college}'s placement office will confirm your seat.`
      : `You're in! Welcome to ${m?.college} on Delta.`);
    navigate('/today');
  };

  const join = async (payload) => {
    setBusy(true);
    try {
      done(await collegeAPI.join(userId, payload));
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not join right now.');
      setBusy(false);
    }
  };

  const card = 'mx-auto max-w-md rounded-2xl border border-rule bg-paper p-6';
  const current = state.data?.membership;
  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-24">
      <section className={card}>
        <GraduationCap size={28} className="mx-auto text-reward" aria-hidden="true" />
        {current ? (
          <div className="text-center">
            <h1 className="mt-3 font-display text-2xl font-semibold text-ink">You're on {current.college}'s seat</h1>
            <p className="mt-2 text-sm text-ink-soft">{current.status === 'pending' ? 'Your placement office still has to confirm it.' : 'All set.'}</p>
          </div>
        ) : codeParam ? (
          preview.isLoading ? <Loader2 className="mx-auto mt-4 h-6 w-6 animate-spin text-ink-soft" /> :
          preview.isError || !preview.data ? (
            <div className="text-center">
              <h1 className="mt-3 font-display text-2xl font-semibold text-ink">This join code isn't valid</h1>
              <p className="mt-2 text-sm text-ink-soft">{preview.error?.response?.data?.detail || 'Ask your placement office for a new one.'}</p>
            </div>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); join({ code: codeParam, roll_no: roll.trim() || null }); }}>
              <h1 className="mt-3 text-center font-display text-2xl font-semibold text-ink">Join {preview.data.college}?</h1>
              <p className="mt-1 text-center text-sm text-ink-soft">
                {preview.data.batch}{PROGRAM[preview.data.program] ? ` · ${PROGRAM[preview.data.program]}` : ''}
              </p>
              {preview.data.needs_roll_no && (
                <label className="mt-4 block text-sm font-semibold text-ink">Your roll number
                  <input value={roll} onChange={(e) => setRoll(e.target.value)} required
                    className="mt-1 w-full rounded-lg border border-rule bg-paper px-3 py-2 text-ink uppercase" />
                </label>
              )}
              <p className="mt-4 text-sm text-ink">
                Your college will see your learning progress: readiness, practice results, active days and plan progress.
                It never sees your chats with Aria, your résumé, or whether you're visible to recruiters.
              </p>
              <p className="mt-2 text-xs text-ink-soft">
                Once you join, only recruiters your college works with can see you (if you switch visibility on).
                If it was on, it switches off so you can choose again.
              </p>
              <button type="submit" disabled={busy}
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink px-6 py-2.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-60">
                {busy && <Loader2 size={14} className="animate-spin" />} Join my college
              </button>
            </form>
          )
        ) : (
          <div>
            <h1 className="mt-3 text-center font-display text-2xl font-semibold text-ink">Join your college</h1>
            {state.data?.suggestion && (
              <div className="mt-4 rounded-xl bg-accent-surface p-3 text-sm text-ink">
                {state.data.suggestion.college} is on Delta and your email matches it.
                <button onClick={() => join({ via_domain: true })} disabled={busy}
                  className="mt-2 block font-semibold underline underline-offset-4">Join with my college email</button>
              </div>
            )}
            <form onSubmit={(e) => { e.preventDefault(); if (code.trim()) navigate(`/join-college/${code.trim()}`); }} className="mt-4 flex gap-2">
              <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Join code" aria-label="Join code"
                className="min-w-0 flex-1 rounded-lg border border-rule bg-paper px-3 py-2 text-ink uppercase" />
              <button type="submit" className="rounded-full bg-ink px-5 py-2 text-sm font-semibold text-paper">Continue</button>
            </form>
          </div>
        )}
      </section>
    </main>
  );
}
