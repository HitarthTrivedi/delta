import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { publicAPI } from '../lib/api';

// Public page a parent opens from the consent email (no login).

export default function ParentConsent() {
  const { token } = useParams();
  const queryClient = useQueryClient();
  const [guardian, setGuardian] = useState(false);
  const [busy, setBusy] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ['parent-consent', token], queryFn: () => publicAPI.parentConsent(token), retry: false,
  });

  const respond = async (grant) => {
    setBusy(true);
    try {
      queryClient.setQueryData(['parent-consent', token], await publicAPI.parentRespond(token, grant, guardian));
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not save your answer.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-bone px-4 py-16 text-ink">
      <section className="mx-auto max-w-lg border border-rule bg-paper p-6 sm:p-8">
        <p className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft"><ShieldCheck size={14} /> Delta · consent for an under-18 student</p>
        {isLoading ? <Loader2 className="mt-6 h-6 w-6 animate-spin text-ink-soft" /> : isError || !data ? (
          <h1 className="mt-4 font-display text-2xl font-semibold text-oxblood">This link isn't valid</h1>
        ) : data.status !== 'pending' ? (
          <>
            <h1 className="mt-4 font-display text-2xl font-semibold text-oxblood">
              {data.status === 'granted' ? 'Thank you. Consent recorded.' : data.status === 'declined' ? 'Understood. We won\'t open the account.' : 'This link has expired'}
            </h1>
            <p className="mt-2 text-sm text-ink-soft">
              {data.status === 'expired' ? `Ask ${data.student} to send a new request from Delta.` : 'You can close this page.'}
            </p>
          </>
        ) : (
          <>
            <h1 className="mt-4 font-display text-2xl font-semibold text-oxblood">{data.student} wants to use Delta through {data.college}</h1>
            <div className="mt-4 grid gap-3 text-sm leading-relaxed">
              <p className="m-0"><strong>What Delta does:</strong> a study plan for placements, practice tests and coding problems, and progress their college can see.</p>
              <p className="m-0"><strong>What Delta never does for under-18s:</strong> no chat with our AI, no AI mock interviews, no recruiters, no public profiles, leagues or sharing, and no ads. Their personal data is never sent to AI providers.</p>
              <p className="m-0">You can withdraw consent later by writing to us; their account is then deleted. Read the <a href="/privacy" target="_blank" rel="noreferrer" className="text-oxblood underline">Privacy Policy</a>.</p>
            </div>
            <label className="mt-5 flex items-start gap-3 text-sm">
              <input type="checkbox" checked={guardian} onChange={() => setGuardian((v) => !v)} className="mt-1" />
              <span>I am {data.student}'s parent or legal guardian.</span>
            </label>
            <div className="mt-5 flex flex-wrap gap-3">
              <button onClick={() => respond(true)} disabled={!guardian || busy}
                className={`px-5 py-2.5 border font-mono text-xs uppercase tracking-[0.12em] ${guardian && !busy ? 'bg-oxblood text-bone border-oxblood cursor-pointer' : 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'}`}>
                I give consent
              </button>
              <button onClick={() => respond(false)} disabled={busy}
                className="px-5 py-2.5 border border-ink text-ink bg-transparent font-mono text-xs uppercase tracking-[0.12em] cursor-pointer">
                No, I don't
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
