import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { templatesAPI } from '../lib/api';

// Choose how Delta plans your weeks: your personal plan (Aria plans each week
// around you) or a fixed role roadmap that still adapts to what you've proven.

const btn = 'inline-flex items-center gap-1.5 px-3.5 py-2 border font-mono text-[11px] uppercase tracking-[0.12em] cursor-pointer disabled:opacity-50';
const errText = (err, fallback) => err?.response?.data?.detail || fallback;
const months = (weeks) => (weeks >= 52 && weeks % 52 === 0 ? `${weeks / 52} year${weeks > 52 ? 's' : ''}` : `${Math.round(weeks / 4.33)} months`);

function Outline({ id }) {
  const { data, isLoading } = useQuery({ queryKey: ['roadmap-outline', id], queryFn: () => templatesAPI.outline(id) });
  if (isLoading) return <Loader2 size={14} className="animate-spin text-ink-soft" />;
  if (!data) return null;
  return (
    <ol className="m-0 mt-2 pl-5 text-[13px] text-ink-soft grid gap-1">
      {data.phase_list.map((p) => (
        <li key={p.id}>
          <span className="text-ink">{p.name}</span> · weeks {p.weeks[0]}–{p.weeks[1]} · {p.goal}
          {p.gate && ` Moves on after a ${p.gate.topic} test score of ${p.gate.min_score}+.`}
        </li>
      ))}
    </ol>
  );
}

export default function TemplatePicker({ userId, onChanged }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['roadmap-templates', userId], queryFn: () => templatesAPI.mine(userId), enabled: !!userId });
  const [open, setOpen] = useState('');
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState('');

  const apply = async (fn, msg, key) => {
    setBusy(key);
    try {
      queryClient.setQueryData(['roadmap-templates', userId], await fn());
      toast.success(msg);
      onChanged?.();
    } catch (err) {
      toast.error(errText(err, 'Could not change your plan.'));
    } finally {
      setBusy('');
    }
  };

  if (isLoading || !data) return <Loader2 size={15} className="animate-spin text-ink-soft" />;
  const current = data.current;
  const minDate = new Date(Date.now() + 14 * 864e5).toISOString().slice(0, 10);

  return (
    <div className="grid gap-3">
      <p className="m-0 text-[13px] text-ink-soft">
        {current
          ? <>You're following <span className="text-ink font-semibold">{current.title}</span>, week {current.week} of {current.weeks}.{' '}
              {current.college_assigned ? 'Your college set this plan.' : 'It still adapts: skills you prove in tests are skipped, weak ones get a revision task.'}</>
          : 'Your personal plan: Aria plans each week around your goals. Or follow a fixed role roadmap that still adapts to you.'}
      </p>
      {data.can_change && current && (
        <button className={`${btn} border-rule text-ink justify-self-start`} disabled={!!busy}
          onClick={() => apply(() => templatesAPI.stop(userId), 'Back to your personal plan from next week.', 'stop')}>
          {busy === 'stop' && <Loader2 size={12} className="animate-spin" />} Switch to my personal plan
        </button>
      )}
      {data.can_change && (
        <>
          <label className="text-[13px] text-ink flex flex-wrap items-center gap-2">
            Target date (optional)
            <input type="date" min={minDate} value={target} onChange={(e) => setTarget(e.target.value)}
              className="border border-rule bg-paper px-2 py-1.5 text-[13px] text-ink" />
            <span className="text-ink-soft">An earlier date squeezes the roadmap: optional steps and breaks drop out.</span>
          </label>
          <ul className="m-0 p-0 list-none grid gap-2">
            {data.catalog.map((t) => (
              <li key={t.id} className={`border bg-paper p-3 ${current?.template_id === t.id ? 'border-oxblood' : 'border-rule'}`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="m-0 text-[14.5px] font-semibold text-ink">{t.title}</p>
                    <p className="m-0 mt-0.5 text-[13px] text-ink-soft">{months(t.weeks)} · {t.summary}</p>
                    {t.note && <p className="m-0 mt-1 text-[12px] text-ink-soft">{t.note}</p>}
                  </div>
                  <span className="flex gap-2">
                    <button className={`${btn} border-rule text-ink-soft`} aria-expanded={open === t.id}
                      onClick={() => setOpen(open === t.id ? '' : t.id)}>
                      Outline <ChevronDown size={12} style={{ transform: open === t.id ? 'rotate(180deg)' : 'none' }} />
                    </button>
                    <button className={`${btn} border-ink text-ink`} disabled={!!busy || current?.template_id === t.id}
                      onClick={() => apply(() => templatesAPI.start(userId, t.id, target), `Your weeks now follow: ${t.title}.`, t.id)}>
                      {busy === t.id && <Loader2 size={12} className="animate-spin" />}
                      {current?.template_id === t.id ? 'Following' : 'Follow this'}
                    </button>
                  </span>
                </div>
                {open === t.id && <Outline id={t.id} />}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
