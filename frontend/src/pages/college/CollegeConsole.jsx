import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { collegeAPI } from '../../lib/api';

// Delta admins (ADMIN_EMAILS): create colleges, set seats and licence, pause or end access.

const btn = 'inline-flex items-center gap-1.5 px-3.5 py-2 border font-mono text-[11px] uppercase tracking-[0.12em] cursor-pointer disabled:opacity-50';
const input = 'border border-rule bg-paper px-3 py-2 text-[14px] text-ink';
const EMPTY = { name: '', city: '', state: '', email_domains: '', seat_limit: 100, licence_valid_until: '', allow_minors: false, first_tpo_email: '' };

function Row({ c, onSaved }) {
  const [seats, setSeats] = useState(c.seat_limit);
  const [until, setUntil] = useState(c.licence_valid_until || '');
  const [status, setStatus] = useState(c.status);
  const [minors, setMinors] = useState(c.allow_minors);
  const save = async () => {
    try {
      await collegeAPI.adminUpdate(c.id, { seat_limit: Number(seats), licence_valid_until: until || null, status, allow_minors: minors });
      onSaved();
      toast.success('Saved.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not save.');
    }
  };
  return (
    <li className="px-4 py-3 grid gap-2 sm:grid-cols-[1fr_auto] sm:items-center">
      <span>
        <Link to={`/college?cid=${c.id}`} className="font-semibold text-ink underline-offset-4 hover:underline">{c.name}</Link>
        <span className="text-ink-soft text-[13px]"> · {c.seats_used}/{c.seat_limit} seats · {c.email_domains.join(', ') || 'no domains'} · {c.live ? 'live' : 'not live'}</span>
      </span>
      <span className="flex flex-wrap items-center gap-2">
        <input className={`${input} w-24`} type="number" min={1} value={seats} onChange={(e) => setSeats(e.target.value)} aria-label="Seats" />
        <input className={input} type="date" value={until} onChange={(e) => setUntil(e.target.value)} aria-label="Licence valid until" />
        <select className={input} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="active">Active</option><option value="suspended">Suspended</option><option value="ended">Ended</option>
        </select>
        <label className="text-[13px] flex items-center gap-1"><input type="checkbox" checked={minors} onChange={() => setMinors((v) => !v)} /> Under-18s</label>
        <button className={`${btn} border-ink text-ink`} onClick={save}>Save</button>
      </span>
    </li>
  );
}

export default function CollegeConsole() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({ queryKey: ['college-admin'], queryFn: collegeAPI.adminList, retry: false });
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['college-admin'] });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  const create = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await collegeAPI.adminCreate({ ...form, seat_limit: Number(form.seat_limit), licence_valid_until: form.licence_valid_until || null,
        email_domains: form.email_domains.split(',').map((d) => d.trim()).filter(Boolean) });
      setForm(EMPTY);
      refresh();
      toast.success('College created. The placement officer can now sign in with that email.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not create the college.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-bone text-ink px-4 pt-8 pb-16">
      <div className="max-w-[1000px] mx-auto">
        <Link to="/college" className="inline-flex items-center gap-1 text-[13px] text-ink-soft"><ArrowLeft size={13} /> College portal</Link>
        <h1 className="font-display text-[clamp(1.9rem,4vw,2.6rem)] font-semibold text-oxblood mt-3 mb-5">Colleges</h1>
        {isLoading ? <Loader2 className="h-6 w-6 animate-spin text-ink-soft" /> : isError ? (
          <p className="text-ink-soft">{error?.response?.status === 403 ? 'Only Delta admins can open this page.' : 'Could not load colleges.'}</p>
        ) : (
          <>
            <ul className="m-0 p-0 list-none border border-rule bg-paper divide-y divide-rule">
              {data.colleges.map((c) => <Row key={c.id} c={c} onSaved={refresh} />)}
              {!data.colleges.length && <li className="px-4 py-3 text-ink-soft text-[14px]">No colleges yet.</li>}
            </ul>
            <form onSubmit={create} className="mt-6 border border-rule bg-paper p-5 grid gap-2 sm:grid-cols-2">
              <h2 className="sm:col-span-2 font-display text-[22px] font-semibold text-ink m-0">Add a college</h2>
              <input className={input} required placeholder="College name" value={form.name} onChange={set('name')} />
              <input className={input} required type="email" placeholder="Placement officer's email" value={form.first_tpo_email} onChange={set('first_tpo_email')} />
              <input className={input} placeholder="City" value={form.city} onChange={set('city')} />
              <input className={input} placeholder="State" value={form.state} onChange={set('state')} />
              <input className={input} placeholder="Student email domains, e.g. svce.ac.in" value={form.email_domains} onChange={set('email_domains')} />
              <input className={input} required type="number" min={1} placeholder="Seats" value={form.seat_limit} onChange={set('seat_limit')} />
              <label className="text-[13px] text-ink">Licence valid until<input className={`${input} mt-1 w-full`} type="date" value={form.licence_valid_until} onChange={set('licence_valid_until')} /></label>
              <label className="text-[13px] text-ink flex items-center gap-2 self-end"><input type="checkbox" checked={form.allow_minors} onChange={set('allow_minors')} /> Allow under-18 students (needs legal sign-off)</label>
              <button type="submit" disabled={busy} className={`${btn} sm:col-span-2 justify-center border-oxblood bg-oxblood text-bone`}>{busy && <Loader2 size={13} className="animate-spin" />} Create college</button>
            </form>
          </>
        )}
      </div>
    </main>
  );
}
