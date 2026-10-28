import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BarChart3, Copy, Loader2, LogOut, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { collegeAPI } from '../../lib/api';
import { useAuthStore } from '../../store/authStore';
import { ExportButton, HBars, Stat, btn, errText, input, pct } from './shared';

// The college's own portal (placement officer = TPO, read-only faculty):
// overview, batches and join codes, roster upload, students, staff and campus recruiters.

const TABS = [['overview', 'Overview'], ['batches', 'Batches'], ['roster', 'Roster upload'], ['students', 'Students'], ['team', 'Team'], ['recruiters', 'Recruiters']];
const PROGRAMS = { none: 'No program', placement_6m: '6-month placement-ready', first_year_4y: 'From first year (4 years)' };

function Accept({ invites, policyVersion, onDone }) {
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const accept = async () => {
    setBusy(true);
    try {
      await collegeAPI.accept(policyVersion);
      onDone();
    } catch (err) {
      toast.error(errText(err, 'Could not accept the invite.'));
      setBusy(false);
    }
  };
  return (
    <section className="border border-rule bg-paper p-6">
      <h1 className="font-display text-[28px] font-semibold text-oxblood m-0">You're invited to manage {invites.map((i) => i.college).join(', ')}</h1>
      <p className="text-ink-soft text-[14px] mt-2">
        As college staff you'll see your students' learning progress (never their chats), manage seats and the roster, and choose
        which recruiters can see your students. You agree to use student data only for your college's training and placement work.
      </p>
      <label className="mt-4 flex items-start gap-3 text-[14px]">
        <input type="checkbox" checked={checked} onChange={() => setChecked((v) => !v)} className="mt-1" />
        <span>I agree to the <a href="/terms" target="_blank" rel="noreferrer" className="text-oxblood underline">Terms of Use</a> (including the duties of college staff) and the <a href="/privacy" target="_blank" rel="noreferrer" className="text-oxblood underline">Privacy Policy</a>.</span>
      </label>
      <button onClick={accept} disabled={!checked || busy} className={`${btn} mt-4 border-oxblood bg-oxblood text-bone`}>
        {busy && <Loader2 size={13} className="animate-spin" />} Accept and open the portal
      </button>
    </section>
  );
}

function Overview({ cid }) {
  const { data, isLoading } = useQuery({ queryKey: ['college-overview', cid], queryFn: () => collegeAPI.overview(cid) });
  if (isLoading) return <Loader2 className="h-6 w-6 animate-spin text-ink-soft" />;
  if (!data) return <p className="text-ink-soft text-[14px]">Could not load the overview.</p>;
  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        <Stat label="Active students" value={data.students} />
        <Stat label="Avg readiness" value={data.avg_readiness ?? '—'} hint="of those who've practised" />
        <Stat label="Active 7 days" value={pct(data.active_7d_pct)} />
        <Stat label="Active 30 days" value={pct(data.active_30d_pct)} />
        <Stat label="Need a nudge" value={data.at_risk} />
      </div>
      <section>
        <h2 className="m-0 text-[15px] font-semibold">Batches</h2>
        <ul className="m-0 mt-2 p-0 list-none border border-rule bg-paper divide-y divide-rule">
          {data.batches.map((b) => (
            <li key={b.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-[14px]">
              <Link to={`/college/batches/${b.id}?cid=${cid}`} className="text-ink font-semibold underline-offset-2 hover:underline">{b.name}</Link>
              <span className="text-ink-soft tabular-nums">
                {b.students} students · avg readiness {b.avg_readiness ?? '—'} · active 7 days {pct(b.active_7d_pct)} · {b.at_risk} need a nudge
              </span>
            </li>
          ))}
          {!data.batches.length && <li className="px-4 py-3 text-ink-soft text-[14px]">No batches yet.</li>}
        </ul>
      </section>
      <section className="border border-rule bg-paper p-4">
        <h2 className="m-0 text-[15px] font-semibold">Weakest skills across the college</h2>
        <div className="mt-3">
          {data.weak_skills.length ? (
            <HBars caption="Students weak in each skill" items={data.weak_skills.map((w) => ({
              label: w.skill, value: w.students_weak, display: `${w.students_weak} of ${w.students_tested} · avg ${w.avg_score}%`,
            }))} />
          ) : <p className="m-0 text-[14px] text-ink-soft">Not enough test results yet.</p>}
        </div>
      </section>
      <section>
        <h2 className="m-0 text-[15px] font-semibold">Exports</h2>
        <p className="m-0 mt-1 text-[13px] text-ink-soft">CSV files that open in Excel. The outcomes sheet has empty placed / employer / package / higher-studies columns for your NAAC 5.2.1 and NIRF returns.</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <ExportButton cid={cid} kind="roster_status">Roster and joining</ExportButton>
          <ExportButton cid={cid} kind="batch_readiness">Readiness, all batches</ExportButton>
          <ExportButton cid={cid} kind="outcomes_naac">Outcomes sheet</ExportButton>
        </div>
      </section>
    </div>
  );
}

function Batches({ cid, canEdit }) {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ['college-batches', cid], queryFn: () => collegeAPI.batches(cid) });
  const [form, setForm] = useState({ name: '', grad_year: '', branch: '', section: '', program: 'none' });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['college-batches', cid] });
  const run = async (fn, msg) => {
    try { await fn(); refresh(); if (msg) toast.success(msg); } catch (err) { toast.error(errText(err, 'Could not save.')); }
  };
  const link = (code) => `${window.location.origin}/join-college/${code}`;
  return (
    <div className="grid gap-3">
      {(data?.batches || []).map((b) => (
        <article key={b.id} className="border border-rule bg-paper p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="m-0 text-[17px] font-semibold text-ink">{b.name}</h3>
              <p className="m-0 text-[13px] text-ink-soft">{b.members} joined · {b.roster} on roster · {PROGRAMS[b.program]}</p>
            </div>
            {canEdit && (
              <select aria-label="Program" value={b.program} className={input}
                onChange={(e) => run(() => collegeAPI.updateBatch(cid, b.id, { program: e.target.value }), 'Program updated.')}>
                {Object.entries(PROGRAMS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[13px]">
            <Link to={`/college/batches/${b.id}?cid=${cid}`} className={`${btn} border-ink text-ink`}><BarChart3 size={12} /> Dashboard</Link>
            <span className="font-mono tracking-[0.12em] text-ink">{b.join_code}</span>
            <button className={`${btn} border-rule text-ink`} onClick={async () => {
              try { await navigator.clipboard.writeText(link(b.join_code)); toast.success('Join link copied. Share it with this batch.'); } catch { toast.message(link(b.join_code)); }
            }}><Copy size={12} /> Copy join link</button>
            {canEdit && <button className={`${btn} border-rule text-ink-soft`} onClick={() => run(() => collegeAPI.rotateCode(cid, b.id), 'New code made. The old link stops working.')}><RefreshCw size={12} /> New code</button>}
          </div>
        </article>
      ))}
      {!data?.batches?.length && <p className="text-ink-soft text-[14px] m-0">No batches yet. Upload your roster (it creates batches from year, branch and section) or add one here.</p>}
      {canEdit && (
        <form className="border border-dashed border-rule p-4 grid gap-2 sm:grid-cols-6" onSubmit={(e) => {
          e.preventDefault();
          run(() => collegeAPI.createBatch(cid, { ...form, grad_year: form.grad_year ? Number(form.grad_year) : null }), 'Batch added.');
          setForm({ name: '', grad_year: '', branch: '', section: '', program: 'none' });
        }}>
          <input className={`${input} sm:col-span-2`} placeholder="Name (optional)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className={input} placeholder="Grad year" inputMode="numeric" value={form.grad_year} onChange={(e) => setForm({ ...form, grad_year: e.target.value })} />
          <input className={input} placeholder="Branch" value={form.branch} onChange={(e) => setForm({ ...form, branch: e.target.value })} />
          <input className={input} placeholder="Section" value={form.section} onChange={(e) => setForm({ ...form, section: e.target.value })} />
          <select className={input} value={form.program} onChange={(e) => setForm({ ...form, program: e.target.value })} aria-label="Program">
            {Object.entries(PROGRAMS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button type="submit" className={`${btn} border-ink text-ink sm:col-span-6 justify-center`}>Add batch</button>
        </form>
      )}
    </div>
  );
}

function Roster({ cid, college, canEdit }) {
  const queryClient = useQueryClient();
  const [csv, setCsv] = useState('');
  const [fileName, setFileName] = useState('');
  const [createBatches, setCreateBatches] = useState(true);
  const [ref, setRef] = useState('');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  if (!canEdit) return <p className="text-ink-soft text-[14px]">Only the placement officer can upload the roster.</p>;

  const send = async (dryRun) => {
    setBusy(true);
    try {
      const res = await collegeAPI.importRoster(cid, { csv, dry_run: dryRun, create_batches: createBatches, minors_consent_ref: ref || null });
      setPreview(res);
      if (!dryRun) {
        toast.success(`Roster saved: ${res.created} new, ${res.updated} updated.`);
        queryClient.invalidateQueries({ queryKey: ['college-batches', cid] });
      }
    } catch (err) {
      toast.error(errText(err, 'Could not read that file.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border border-rule bg-paper p-5">
      <p className="m-0 text-[14px] text-ink-soft">
        Upload a CSV with at least a roll number and a name. Optional columns: email, grad year (batch), branch, section, course, CGPA, backlogs{college.allow_minors ? ', date of birth' : ''}.
        Re-uploading updates students by roll number; it never removes anyone.
      </p>
      <input type="file" accept=".csv,text/csv" className="mt-3 block text-[14px]" onChange={async (e) => {
        const f = e.target.files?.[0];
        if (!f) return;
        if (f.size > 2 * 1024 * 1024) { toast.error('That file is over 2 MB. Split it by batch.'); return; }
        setFileName(f.name);
        setCsv(await f.text());
        setPreview(null);
      }} />
      <label className="mt-3 flex items-center gap-2 text-[14px]"><input type="checkbox" checked={createBatches} onChange={() => setCreateBatches((v) => !v)} /> Create batches from grad year, branch and section</label>
      {college.allow_minors && (
        <label className="mt-3 block text-[13px] text-ink">If any students are under 18: your reference for the parental consent your college holds
          <input className={`${input} mt-1 w-full`} value={ref} onChange={(e) => setRef(e.target.value)} placeholder="e.g. Consent forms 2026, register 3" />
        </label>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <button className={`${btn} border-ink text-ink`} disabled={!csv || busy} onClick={() => send(true)}>{busy && <Loader2 size={13} className="animate-spin" />} Check {fileName || 'file'}</button>
        <button className={`${btn} border-oxblood bg-oxblood text-bone`} disabled={!preview || !preview.dry_run || busy} onClick={() => send(false)}>Import</button>
      </div>
      {preview && (
        <div className="mt-4 text-[14px]">
          <p className="m-0 text-ink">
            {preview.dry_run ? 'Preview: ' : 'Done: '}{preview.created} new · {preview.updated} updated · {preview.unchanged} unchanged · {preview.new_batches} new batches
            {preview.minors ? ` · ${preview.minors} under 18` : ''}
          </p>
          {preview.errors.length > 0 && (
            <>
              <p className="m-0 mt-2 text-ink">{preview.errors.length} rows need fixing (they're skipped; the rest import fine):</p>
              <ul className="m-0 mt-1 pl-5 text-ink-soft max-h-60 overflow-y-auto">
                {preview.errors.slice(0, 200).map((e, i) => <li key={i}>Row {e.row || '—'} · {e.field}: {e.message}</li>)}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Students({ cid, canEdit }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('');
  const [confirm, setConfirm] = useState('');
  const { data } = useQuery({ queryKey: ['college-members', cid, status], queryFn: () => collegeAPI.members(cid, status ? { status } : {}) });
  const { data: batches } = useQuery({ queryKey: ['college-batches', cid], queryFn: () => collegeAPI.batches(cid) });
  const names = Object.fromEntries((batches?.batches || []).map((b) => [b.id, b.name]));
  const refresh = () => { queryClient.invalidateQueries({ queryKey: ['college-members', cid] }); queryClient.invalidateQueries({ queryKey: ['college', cid] }); };
  const run = async (fn, msg) => { try { await fn(); refresh(); toast.success(msg); } catch (err) { toast.error(errText(err, 'Could not update.')); } finally { setConfirm(''); } };
  return (
    <div>
      <select aria-label="Filter" className={input} value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="">All</option><option value="pending">Waiting for approval</option><option value="active">Active</option><option value="removed">Removed</option><option value="expired">Expired</option>
      </select>
      <ul className="m-0 mt-3 p-0 list-none border border-rule bg-paper divide-y divide-rule">
        {(data?.members || []).map((m) => (
          <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-[14px]">
            <span className="min-w-0">
              <span className="text-ink font-semibold">{m.name}</span>
              <span className="text-ink-soft"> · {m.roll_no || 'no roll no.'} · {names[m.batch_id] || 'no batch'} · {m.status}{m.verified ? ' · on roster' : m.status === 'active' ? ' · not on roster' : ''}</span>
            </span>
            {canEdit && (
              <span className="flex gap-2">
                {m.status === 'pending' && <button className={`${btn} border-ink text-ink`} onClick={() => run(() => collegeAPI.approve(cid, m.id), `${m.name} approved.`)}>Approve</button>}
                {['pending', 'active'].includes(m.status) && (confirm === m.id
                  ? <button className={`${btn} border-oxblood text-oxblood`} onClick={() => run(() => collegeAPI.removeMember(cid, m.id), `${m.name}'s seat was freed.`)}>Remove?</button>
                  : <button className={`${btn} border-rule text-ink-soft`} onClick={() => setConfirm(m.id)}>Remove</button>)}
              </span>
            )}
          </li>
        ))}
        {!data?.members?.length && <li className="px-4 py-3 text-ink-soft text-[14px]">No students here yet. Share a batch join link.</li>}
      </ul>
    </div>
  );
}

function Team({ cid, canEdit }) {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ['college-team', cid], queryFn: () => collegeAPI.team(cid) });
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('faculty');
  const set = (res) => queryClient.setQueryData(['college-team', cid], res);
  return (
    <div className="grid gap-3">
      <ul className="m-0 p-0 list-none border border-rule bg-paper divide-y divide-rule">
        {(data?.admins || []).map((a) => (
          <li key={a.id} className="flex items-center justify-between gap-2 px-4 py-3 text-[14px]">
            <span>{a.email} <span className="text-ink-soft">· {a.role === 'tpo' ? 'Placement officer' : 'Faculty (view only)'} · {a.status}</span></span>
            {canEdit && <button className={`${btn} border-rule text-ink-soft`} onClick={async () => {
              try { set(await collegeAPI.removeStaff(cid, a.id)); } catch (err) { toast.error(errText(err, 'Could not remove.')); }
            }}>Remove</button>}
          </li>
        ))}
      </ul>
      {canEdit && (
        <form className="flex flex-wrap gap-2" onSubmit={async (e) => {
          e.preventDefault();
          try { set(await collegeAPI.invite(cid, email, role)); setEmail(''); toast.success('Invite saved. They sign in with that email to accept.'); } catch (err) { toast.error(errText(err, 'Could not invite.')); }
        }}>
          <input className={`${input} min-w-0 flex-1`} type="email" required placeholder="colleague@college.edu" value={email} onChange={(e) => setEmail(e.target.value)} />
          <select className={input} value={role} onChange={(e) => setRole(e.target.value)} aria-label="Role"><option value="faculty">Faculty (view only)</option><option value="tpo">Placement officer</option></select>
          <button className={`${btn} border-ink text-ink`} type="submit">Invite</button>
        </form>
      )}
    </div>
  );
}

function Recruiters({ cid, canEdit }) {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ['college-recruiters', cid], queryFn: () => collegeAPI.recruiters(cid) });
  const [email, setEmail] = useState('');
  const set = (res) => queryClient.setQueryData(['college-recruiters', cid], res);
  return (
    <div className="grid gap-3">
      <p className="m-0 text-[14px] text-ink-soft">
        Recruiters you add here can see your students who opted in, and no one else's. They need a Delta campus recruiter account;
        if they don't have one yet, the link activates once Delta verifies them.
      </p>
      <ul className="m-0 p-0 list-none border border-rule bg-paper divide-y divide-rule">
        {(data?.recruiters || []).map((r) => (
          <li key={r.id} className="flex items-center justify-between gap-2 px-4 py-3 text-[14px]">
            <span>{r.company || r.email} <span className="text-ink-soft">· {r.email} · {r.status === 'active' ? 'can see opted-in students' : 'waiting for Delta to verify them'}</span></span>
            {canEdit && <button className={`${btn} border-rule text-ink-soft`} onClick={async () => {
              try { set(await collegeAPI.revokeRecruiter(cid, r.id)); toast.success('Access removed.'); } catch (err) { toast.error(errText(err, 'Could not remove.')); }
            }}>Remove</button>}
          </li>
        ))}
        {!data?.recruiters?.length && <li className="px-4 py-3 text-ink-soft text-[14px]">No recruiters yet.</li>}
      </ul>
      {canEdit && (
        <form className="flex flex-wrap gap-2" onSubmit={async (e) => {
          e.preventDefault();
          try { set(await collegeAPI.linkRecruiter(cid, email)); setEmail(''); } catch (err) { toast.error(errText(err, 'Could not add.')); }
        }}>
          <input className={`${input} min-w-0 flex-1`} type="email" required placeholder="hr@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className={`${btn} border-ink text-ink`} type="submit">Add recruiter</button>
        </form>
      )}
    </div>
  );
}

export default function CollegePortal() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logout = useAuthStore((s) => s.logout);
  const [params] = useSearchParams();
  const [tab, setTab] = useState('overview');
  const me = useQuery({ queryKey: ['college-me'], queryFn: collegeAPI.me });
  const cid = params.get('cid') || me.data?.colleges?.[0]?.id;
  const college = useQuery({ queryKey: ['college', cid], queryFn: () => collegeAPI.get(cid), enabled: !!cid });
  useEffect(() => { setTab('overview'); }, [cid]);

  const signOut = async () => { await logout(); navigate('/college/login'); };
  const shell = (body) => (
    <main className="min-h-screen bg-bone text-ink px-4 pt-8 pb-16">
      <div className="max-w-[1000px] mx-auto">
        <header className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <p className="kicker m-0">Delta for College</p>
          <span className="flex gap-2">
            {me.data?.is_admin && <Link to="/college/admin" className={`${btn} border-rule text-ink`}>All colleges</Link>}
            <button onClick={signOut} className={`${btn} border-rule text-ink-soft`}><LogOut size={12} /> Sign out</button>
          </span>
        </header>
        {body}
      </div>
    </main>
  );

  if (me.isLoading || (cid && college.isLoading)) return shell(<Loader2 className="h-6 w-6 animate-spin text-ink-soft" />);
  if (!cid) {
    if (me.data?.pending_invites?.length) {
      return shell(<Accept invites={me.data.pending_invites} policyVersion={me.data.policy_version}
        onDone={() => queryClient.invalidateQueries({ queryKey: ['college-me'] })} />);
    }
    return shell(<p className="text-ink-soft">This login has no college access. Sign in with the email your college or Delta invited.
      {me.data?.is_admin && <> Or <Link to="/college/admin" className="text-oxblood underline">open the college console</Link>.</>}</p>);
  }
  if (college.isError || !college.data) return shell(<p className="text-ink-soft">{errText(college.error, 'Could not load this college.')}</p>);

  const c = college.data;
  const canEdit = c.role === 'tpo' || c.role === 'delta';
  return shell(
    <>
      <h1 className="font-display text-[clamp(1.9rem,4vw,2.6rem)] font-semibold text-oxblood m-0">{c.name}</h1>
      <p className="text-ink-soft text-[14px] mt-1">
        {c.seats_used} of {c.seat_limit} seats used
        {c.licence_valid_until ? ` · licence until ${new Date(`${c.licence_valid_until}T12:00:00`).toLocaleDateString()}` : ''}
        {!c.live && ' · access paused'} · you are {c.role === 'tpo' ? 'the placement officer' : c.role === 'delta' ? 'a Delta admin' : 'faculty (view only)'}
      </p>
      <nav className="mt-5 mb-4 flex flex-wrap gap-1 border-b border-rule" role="tablist">
        {TABS.map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`px-3 py-2 text-[14px] border-b-2 -mb-px cursor-pointer bg-transparent ${tab === k ? 'border-oxblood text-oxblood' : 'border-transparent text-ink-soft'}`}>{label}</button>
        ))}
      </nav>
      {tab === 'overview' && <Overview cid={cid} />}
      {tab === 'batches' && <Batches cid={cid} canEdit={canEdit} />}
      {tab === 'roster' && <Roster cid={cid} college={c} canEdit={canEdit} />}
      {tab === 'students' && <Students cid={cid} canEdit={canEdit} />}
      {tab === 'team' && <Team cid={cid} canEdit={canEdit} />}
      {tab === 'recruiters' && <Recruiters cid={cid} canEdit={canEdit} />}
    </>
  );
}
