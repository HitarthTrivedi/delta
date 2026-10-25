import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BadgeCheck, Loader2, Star } from 'lucide-react';
import { publicAPI } from '../lib/api';

// Public "verify this badge" page (no login). Shows only what the learner chose
// to share: first name + last initial, the badge, and when it was earned.

export default function VerifyBadge() {
  const { token } = useParams();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['verify-badge', token], queryFn: () => publicAPI.badge(token), retry: false,
  });

  return (
    <main className="min-h-screen bg-bone px-4 py-16">
      <section className="mx-auto max-w-md rounded-2xl border border-rule bg-paper p-7 text-center">
        <p className="flex items-center justify-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-soft">
          <BadgeCheck size={15} aria-hidden="true" /> Verified by Delta
        </p>
        {isLoading ? (
          <Loader2 className="mx-auto mt-6 h-6 w-6 animate-spin text-ink-soft" />
        ) : isError || !data ? (
          <>
            <h1 className="mt-4 font-display text-2xl font-semibold text-ink">This link isn't active</h1>
            <p className="mt-2 text-sm text-ink-soft">It may be mistyped, or its owner stopped sharing it.</p>
          </>
        ) : (
          <>
            <span className="mx-auto mt-5 inline-flex h-20 w-20 items-center justify-center rounded-full bg-reward/15 text-reward">
              <Star size={34} aria-hidden="true" />
            </span>
            <h1 className="mt-4 font-display text-3xl font-semibold text-ink">{data.title}</h1>
            <span className="mt-2 flex justify-center gap-1" role="img" aria-label={`Tier ${data.tier} of ${data.max_tier}`}>
              {Array.from({ length: data.max_tier }, (_, i) => (
                <span key={i} className={`h-1.5 w-5 rounded-full ${i < data.tier ? 'bg-reward' : 'bg-rule'}`} />
              ))}
            </span>
            <p className="mt-3 text-ink">{data.description}</p>
            <p className="mt-4 text-sm text-ink-soft">
              Earned by <strong className="text-ink">{data.name}</strong> on{' '}
              {new Date(`${data.earned_on}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            <p className="mt-4 text-xs leading-relaxed text-ink-soft">
              Delta awards badges automatically from learning activity it records itself (tests, coding, interviews,
              plan tasks), never from self-reported claims.
            </p>
          </>
        )}
        <Link to="/" className="mt-6 inline-block text-sm font-semibold text-ink underline-offset-4 hover:underline">What is Delta?</Link>
      </section>
    </main>
  );
}
