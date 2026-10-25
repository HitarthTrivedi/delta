import React from 'react';
import { Check, MapPin } from 'lucide-react';

// The roadmap drawn as a path: phases in order, each skill a stop, and a
// "You are here" marker. Purely a view of the existing roadmap statuses.

const OFFSETS = [0, 28, 48, 28, 0, -28, -48, -28]; // px, gentle zig-zag that fits a phone

export default function ProgressPath({ phases, activePhaseId }) {
  const list = (phases || []).filter((p) => (p.nodes || []).length);
  if (!list.length) return null;

  const all = list.flatMap((p) => p.nodes.map((n) => ({ ...n, phaseId: p.id })));
  const here = all.find((n) => n.phaseId === activePhaseId && n.status === 'in_progress')
    || all.find((n) => n.status === 'in_progress')
    || all.find((n) => n.status !== 'mastered');
  const mastered = all.filter((n) => n.status === 'mastered').length;
  let step = 0;

  return (
    <section aria-labelledby="path-heading" className="rounded-2xl border border-rule bg-paper p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="path-heading" className="font-display text-2xl font-semibold text-ink">Your path</h2>
        <span className="text-sm text-ink-soft">{mastered} of {all.length} skills mastered</span>
      </div>
      {list.map((phase, pi) => (
        <div key={phase.id || pi} className="mt-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Phase {pi + 1}{phase.name ? ` · ${phase.name}` : ''}{phase.id === activePhaseId ? ' · now' : ''}
          </p>
          <ol className="mt-3 grid gap-3">
            {phase.nodes.map((n) => {
              const offset = OFFSETS[step % OFFSETS.length];
              step += 1;
              const isHere = here && n.id === here.id && phase.id === here.phaseId;
              const done = n.status === 'mastered';
              return (
                <li key={n.id || n.label} className="flex items-center gap-3" aria-current={isHere ? 'step' : undefined}>
                  <span className="w-[112px] shrink-0">
                    <span
                      style={{ transform: `translateX(${offset + 48}px)` }}
                      className={`inline-flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                        done ? 'border-reward bg-reward text-paper'
                          : isHere ? 'border-reward bg-reward/15 text-reward ring-4 ring-reward/20'
                            : 'border-rule bg-accent-surface text-ink-soft'}`}
                    >
                      {done ? <Check size={18} aria-hidden="true" /> : isHere ? <MapPin size={18} aria-hidden="true" /> : <span className="h-2 w-2 rounded-full bg-current" />}
                    </span>
                  </span>
                  <span className="min-w-0">
                    <span className={`block truncate text-sm ${isHere ? 'font-semibold text-ink' : done ? 'text-ink' : 'text-ink-soft'}`}>
                      {n.label || n.skill_name}
                    </span>
                    {isHere && <span className="block text-xs text-reward">You are here</span>}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      ))}
    </section>
  );
}
