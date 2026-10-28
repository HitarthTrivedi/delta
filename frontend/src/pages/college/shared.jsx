import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';
import { toast } from 'sonner';
import { collegeAPI } from '../../lib/api';

// Pieces shared by the college portal pages (TPO / faculty).

export const btn = 'inline-flex items-center gap-1.5 px-3.5 py-2 border font-mono text-[11px] uppercase tracking-[0.12em] cursor-pointer disabled:opacity-50';
export const input = 'border border-rule bg-paper px-3 py-2 text-[14px] text-ink';
export const errText = (err, fallback) => err?.response?.data?.detail || fallback;
export const day = (iso) => (iso ? new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '—');
export const pct = (v) => (v == null ? '—' : `${Math.round(v)}%`);

export async function downloadCsv(cid, kind, params) {
  try {
    const blob = await collegeAPI.exportCsv(cid, kind, params);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${kind}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    toast.error('Could not export. Try again.');
  }
}

export function ExportButton({ cid, kind, params, children }) {
  return (
    <button className={`${btn} border-rule text-ink`} onClick={() => downloadCsv(cid, kind, params)}>
      <Download size={12} /> {children}
    </button>
  );
}

export function SubpageShell({ cid, back = 'Back to the portal', children }) {
  return (
    <main className="min-h-screen bg-bone text-ink px-4 pt-8 pb-16">
      <div className="max-w-[1000px] mx-auto">
        <header className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <p className="kicker m-0">Delta for College</p>
          <Link to={`/college${cid ? `?cid=${cid}` : ''}`} className={`${btn} border-rule text-ink`}><ArrowLeft size={12} /> {back}</Link>
        </header>
        {children}
      </div>
    </main>
  );
}

export function Stat({ label, value, hint }) {
  return (
    <div className="border border-rule bg-paper px-4 py-3 min-w-0">
      <p className="m-0 font-mono text-[10.5px] uppercase tracking-[0.12em] text-ink-soft">{label}</p>
      <p className="m-0 mt-1 text-[24px] font-semibold text-ink tabular-nums">{value}</p>
      {hint && <p className="m-0 text-[12px] text-ink-soft">{hint}</p>}
    </div>
  );
}

// One series, one hue: horizontal bars with the value written beside each bar.
export function HBars({ items, max, caption }) {
  const top = max || Math.max(1, ...items.map((i) => i.value || 0));
  return (
    <figure className="m-0">
      <ul className="m-0 p-0 list-none grid gap-1.5" aria-hidden="true">
        {items.map((i) => (
          <li key={i.label} className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-2 text-[13px]" title={`${i.label}: ${i.display ?? i.value}`}>
            <span className="truncate text-ink">{i.label}</span>
            <span className="h-3 bg-rule/40">
              <span className="block h-3 bg-oxblood rounded-r-[4px]" style={{ width: `${Math.max(0, Math.min(100, (100 * (i.value || 0)) / top))}%` }} />
            </span>
            <span className="text-ink-soft tabular-nums">{i.display ?? i.value}</span>
          </li>
        ))}
      </ul>
      <table className="sr-only">
        <caption>{caption}</caption>
        <tbody>{items.map((i) => <tr key={i.label}><th scope="row">{i.label}</th><td>{i.display ?? i.value}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}

// One series, one hue: a column per week, value on hover and under the latest week.
export function WeekBars({ weeks, max = 100, format = pct, caption }) {
  return (
    <figure className="m-0">
      <div className="flex items-end gap-[2px] h-28 border-b border-rule" aria-hidden="true">
        {weeks.map((w, idx) => (
          <div key={w.week_of} className="flex-1 h-full flex flex-col justify-end items-center" title={`Week of ${day(w.week_of)}: ${format(w.value)}`}>
            {idx === weeks.length - 1 && <span className="text-[11px] text-ink-soft tabular-nums mb-0.5">{format(w.value)}</span>}
            <span className="block w-full max-w-[36px] bg-oxblood rounded-t-[4px]" style={{ height: `${w.value ? Math.max(2, (85 * w.value) / max) : 0}%` }} />
          </div>
        ))}
      </div>
      <div className="flex gap-[2px] mt-1" aria-hidden="true">
        {weeks.map((w) => <span key={w.week_of} className="flex-1 text-center text-[10.5px] text-ink-soft truncate">{day(w.week_of)}</span>)}
      </div>
      <table className="sr-only">
        <caption>{caption}</caption>
        <tbody>{weeks.map((w) => <tr key={w.week_of}><th scope="row">Week of {day(w.week_of)}</th><td>{format(w.value)}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}
