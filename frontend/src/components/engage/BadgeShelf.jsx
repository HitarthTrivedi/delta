import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Code2, Copy, Flame, ListChecks, Loader2, Mic, Share2, Star, Target, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { engagementAPI } from '../../lib/api';
import { shareBadge, verifyLink } from '../../lib/shareCard';

// Badges earned automatically from verified activity (server-side). Locked
// badges show friendly progress, never a judgement.

const ICONS = { streak: Flame, quick5: Zap, plan: ListChecks, tests: BookOpen, coding: Code2, interviews: Mic, quests: Target, mastery: Star };

function shortName(name) {
  const parts = (name || '').split(' ').filter(Boolean);
  if (!parts.length) return '';
  return parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1][0].toUpperCase()}.` : parts[0];
}

export default function BadgeShelf({ userId, userName }) {
  const queryClient = useQueryClient();
  const [sharing, setSharing] = useState('');
  const [confirming, setConfirming] = useState(''); // badge key awaiting "create a public link?"
  const { data, isLoading, isError } = useQuery({
    queryKey: ['badges', userId],
    queryFn: () => engagementAPI.badges(userId),
    enabled: !!userId,
  });

  const setToken = (key, token) => queryClient.setQueryData(['badges', userId], (d) => d && ({
    ...d, badges: d.badges.map((x) => (x.key === key ? { ...x, share_token: token } : x)),
  }));

  const share = async (b) => {
    setConfirming('');
    setSharing(b.key);
    try {
      const token = b.share_token || (await engagementAPI.shareBadge(userId, b.key)).token;
      setToken(b.key, token);
      const how = await shareBadge(b, shortName(userName), verifyLink(token));
      if (how === 'downloaded') toast.success('Image saved. Add it to a LinkedIn or WhatsApp post with your verify link.');
    } catch {
      toast.error('Could not share this badge. Try again.');
    } finally {
      setSharing('');
    }
  };

  const copyLink = async (b) => {
    try {
      await navigator.clipboard.writeText(verifyLink(b.share_token));
      toast.success('Verify link copied.');
    } catch {
      toast.message(verifyLink(b.share_token));
    }
  };

  const stopSharing = async (b) => {
    try {
      await engagementAPI.unshareBadge(userId, b.key);
      setToken(b.key, null);
      toast.success('Link turned off. Anyone opening it now sees nothing.');
    } catch {
      toast.error('Could not turn the link off. Try again.');
    }
  };

  if (isLoading) return <div className="flex items-center gap-2 py-6 text-sm text-ink-soft"><Loader2 size={16} className="animate-spin" /> Loading badges...</div>;
  if (isError || !data) return null;

  const badges = data.badges || [];
  const earned = badges.filter((b) => b.tier > 0).length;
  return (
    <section aria-labelledby="badges-heading" className="mb-8">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="badges-heading" className="font-display text-2xl font-semibold text-ink">Badges</h2>
        <span className="text-sm text-ink-soft">{earned} of {badges.length} earned · they come automatically as you learn</span>
      </div>
      <ul className="grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 md:grid-cols-4">
        {badges.map((b) => {
          const Icon = ICONS[b.key] || Star;
          const got = b.tier > 0;
          const pct = b.next ? Math.min(100, Math.round((100 * b.progress) / b.next.at)) : 100;
          return (
            <li key={b.key} className={`flex flex-col rounded-2xl border p-4 ${got ? 'border-reward/40 bg-reward/10' : 'border-rule bg-paper'}`}>
              <div className="flex items-center gap-3">
                <span className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${got ? 'bg-reward/20 text-reward' : 'bg-accent-surface text-ink-soft'}`}>
                  <Icon size={19} aria-hidden="true" />
                </span>
                <span className="min-w-0">
                  <span className="block font-semibold leading-tight text-ink">{got ? b.title : b.next?.title}</span>
                  <span className="mt-1 flex gap-1" role="img" aria-label={`Tier ${b.tier} of ${b.max_tier}`}>
                    {Array.from({ length: b.max_tier }, (_, i) => (
                      <span key={i} className={`h-1.5 w-4 rounded-full ${i < b.tier ? 'bg-reward' : 'bg-rule'}`} />
                    ))}
                  </span>
                </span>
              </div>
              <p className="mt-3 text-sm text-ink-soft">{got ? b.description : b.next?.description}</p>
              {b.next && (
                <div className="mt-3">
                  <div className="h-1.5 rounded-full bg-rule" aria-hidden="true"><div className="h-1.5 rounded-full bg-ink" style={{ width: `${pct}%` }} /></div>
                  <p className="mt-1 text-xs text-ink-soft">{got ? `Next: ${b.next.title} · ` : ''}{Math.min(b.progress, b.next.at)} / {b.next.at}</p>
                </div>
              )}
              {got && confirming === b.key && (
                <div className="mt-3 rounded-xl bg-paper p-3 text-xs text-ink-soft">
                  Sharing makes a public link: anyone with it sees your first name, last initial and this badge. You can turn it off any time.
                  <div className="mt-2 flex gap-3">
                    <button onClick={() => share(b)} className="font-semibold text-ink underline-offset-4 hover:underline">Create link and share</button>
                    <button onClick={() => setConfirming('')} className="underline-offset-4 hover:underline">Cancel</button>
                  </div>
                </div>
              )}
              {got && confirming !== b.key && (
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                  <button onClick={() => (b.share_token ? share(b) : setConfirming(b.key))} disabled={sharing === b.key}
                    className="inline-flex items-center gap-1.5 font-semibold text-ink underline-offset-4 hover:underline disabled:opacity-60">
                    {sharing === b.key ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />} Share
                  </button>
                  {b.share_token && (
                    <>
                      <button onClick={() => copyLink(b)} className="inline-flex items-center gap-1 text-ink-soft underline-offset-4 hover:underline"><Copy size={13} /> Copy link</button>
                      <button onClick={() => stopSharing(b)} className="text-ink-soft underline-offset-4 hover:underline">Stop sharing</button>
                    </>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
