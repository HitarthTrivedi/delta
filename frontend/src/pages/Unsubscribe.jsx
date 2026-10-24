import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { engagementAPI } from '../lib/api';

// One-click unsubscribe from a reminder email. No sign-in needed: the link is signed.
export default function Unsubscribe() {
  const [params] = useSearchParams();
  const [state, setState] = useState('working');

  useEffect(() => {
    const u = params.get('u');
    const t = params.get('t');
    if (!u || !t) {
      setState('invalid');
      return;
    }
    engagementAPI.unsubscribe(u, t).then(() => setState('done')).catch(() => setState('invalid'));
  }, [params]);

  return (
    <main className="min-h-screen bg-bone flex items-center justify-center px-4">
      <div className="max-w-md rounded-2xl border border-rule bg-paper p-7 text-center">
        {state === 'working' && <p className="text-ink-soft">One moment…</p>}
        {state === 'done' && (
          <>
            <h1 className="font-display text-2xl font-semibold text-ink">Reminders are off</h1>
            <p className="mt-2 text-sm text-ink-soft">You won't get study reminders any more. You can turn them back on from the Today page whenever you like.</p>
          </>
        )}
        {state === 'invalid' && (
          <>
            <h1 className="font-display text-2xl font-semibold text-ink">This link didn't work</h1>
            <p className="mt-2 text-sm text-ink-soft">You can turn reminders off from the Today page after signing in.</p>
          </>
        )}
        <Link to="/today" className="mt-5 inline-block rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper">Go to Delta</Link>
      </div>
    </main>
  );
}
