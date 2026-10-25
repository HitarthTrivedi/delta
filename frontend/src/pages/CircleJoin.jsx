import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Users } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../store/authStore';
import { circlesAPI } from '../lib/api';
import { MEMBERS_SEE } from './Circles';

// Landing page of a circle invite link: what the circle is, what joining shares, one button.

export default function CircleJoin() {
  const { code } = useParams();
  const userId = useAuthStore((s) => s.userId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [joining, setJoining] = useState(false);
  const { data, isLoading, error } = useQuery({
    queryKey: ['circle-preview', code], queryFn: () => circlesAPI.preview(userId, code), enabled: !!userId, retry: false,
  });

  const join = async () => {
    setJoining(true);
    try {
      queryClient.setQueryData(['circles', userId], await circlesAPI.join(userId, code));
      toast.success(`You joined ${data.name}!`);
      navigate('/circles');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not join this circle.');
      setJoining(false);
    }
  };

  return (
    <main className="min-h-screen bg-bone px-4 pb-16 pt-24">
      <section className="mx-auto max-w-md rounded-2xl border border-rule bg-paper p-6 text-center">
        <Users size={28} className="mx-auto text-reward" aria-hidden="true" />
        {isLoading ? (
          <Loader2 className="mx-auto mt-4 h-6 w-6 animate-spin text-ink-soft" />
        ) : error || !data ? (
          <>
            <h1 className="mt-3 font-display text-2xl font-semibold text-ink">This invite has expired</h1>
            <p className="mt-2 text-sm text-ink-soft">{error?.response?.data?.detail || 'Ask your friend for a new link.'}</p>
          </>
        ) : (
          <>
            <h1 className="mt-3 font-display text-2xl font-semibold text-ink">Join “{data.name}”?</h1>
            <p className="mt-1 text-sm text-ink-soft">{data.members} of {data.max_members} people so far.</p>
            <p className="mt-4 text-sm text-ink">{MEMBERS_SEE} You can leave any time.</p>
            <button onClick={join} disabled={joining || data.full}
              className="mt-5 inline-flex items-center gap-2 rounded-full bg-ink px-6 py-2.5 text-sm font-semibold text-paper hover:opacity-90 disabled:opacity-60">
              {joining && <Loader2 size={14} className="animate-spin" />} {data.full ? 'This circle is full' : 'Join the circle'}
            </button>
          </>
        )}
      </section>
    </main>
  );
}
