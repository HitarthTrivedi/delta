import React from 'react';
import { ShieldCheck } from 'lucide-react';

// "How this was taken": the same note a recruiter sees (only if the learner is
// visible to recruiters). Neutral ink: a note, never a verdict.
export default function IntegrityNote({ notes, style }) {
  if (!notes) return null;
  const parts = [notes.timed ? 'Timed' : 'Untimed', ...(notes.flags?.length ? notes.flags : ['no notes'])];
  return (
    <p style={{ display: 'flex', gap: 6, alignItems: 'flex-start', margin: 0, fontSize: 12.5, lineHeight: 1.5, color: 'var(--ink-soft)', ...style }}>
      <ShieldCheck size={14} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
      <span>How this was taken: {parts.join(' · ')}. Recruiters see this only if you are visible to them.</span>
    </p>
  );
}
