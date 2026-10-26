import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, LogOut, Search, X, ExternalLink, ShieldCheck, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { privacyAPI, recruiterAPI } from '../../lib/api';
import { useAuthStore } from '../../store/authStore';

const SANDBOX_LABEL = { theory: 'Technical test', coding: 'Coding', interview: 'Mock interview' };

// Shown only when the student opted in to this badge and studied on 20+ of the last 30 days.
function ConsistentBadge() {
  return (
    <span title="Studied on 20 or more of the last 30 days (shared with the student's consent)"
      className="inline-flex items-center font-mono text-[10px] uppercase tracking-[0.12em] px-2 py-0.5 border border-ink text-ink">
      Consistent learner
    </span>
  );
}

const inputClass = 'w-full bg-paper border border-rule px-3.5 py-3 text-ink placeholder:text-ink-soft text-sm outline-none focus:border-oxblood box-border';
const labelClass = 'block text-[13px] font-semibold text-ink mb-1.5';
const primaryBtn = 'inline-flex items-center justify-center gap-2 px-5 py-3 border font-mono text-xs uppercase tracking-[0.14em] transition-colors';
const btnOn = 'bg-oxblood text-bone border-oxblood cursor-pointer hover:bg-ink hover:border-ink';
const btnOff = 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed';

export default function RecruiterPortal() {
  const [state, setState] = useState({ loading: true, recruiter: null });

  const load = () => {
    recruiterAPI.me()
      .then((recruiter) => setState({ loading: false, recruiter }))
      .catch((err) => {
        if (err?.response?.status !== 404) toast.error('Could not load your recruiter account.');
        setState({ loading: false, recruiter: null });
      });
  };
  useEffect(load, []);

  if (state.loading) {
    return <Shell><div className="flex justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div></Shell>;
  }
  const r = state.recruiter;
  if (!r) return <Shell><RegisterForm onDone={load} /></Shell>;
  if (r.status === 'pending') {
    return (
      <Shell recruiter={r}>
        <Notice title="Your account is awaiting approval">
          Thanks, {r.name}. We verify every recruiter before they can see any student, which protects the students who trust Delta with their data.
          We'll review <strong>{r.company}</strong> shortly. Check back here once you've been approved.
        </Notice>
      </Shell>
    );
  }
  if (r.status === 'rejected') {
    return (
      <Shell recruiter={r}>
        <Notice title="We couldn't verify your account">
          If you think this is a mistake, email hitartht318@gmail.com from your work address with your company details.
        </Notice>
      </Shell>
    );
  }
  return <Shell recruiter={r}><Dashboard recruiter={r} /></Shell>;
}

function Shell({ recruiter, children }) {
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-bone text-ink">
      <nav className="border-b border-rule bg-bone">
        <div className="max-w-[1180px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
          <Link to="/recruiter" className="flex items-center gap-2 text-ink no-underline">
            <span className="font-display text-lg font-semibold">Delta</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-oxblood border border-oxblood px-1.5 py-0.5">Recruiters</span>
          </Link>
          <div className="flex items-center gap-3">
            {recruiter?.is_admin && (
              <Link to="/recruiter/admin" className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft hover:text-oxblood no-underline">
                <ShieldCheck size={13} /> Admin
              </Link>
            )}
            {recruiter && (
              <span className="hidden sm:inline text-[13px] text-ink-soft">
                {recruiter.company} · {recruiter.pool === 'campus'
                  ? (recruiter.linked_colleges?.length ? `Campus: ${recruiter.linked_colleges.join(', ')}` : 'Campus: no colleges linked yet')
                  : 'Off-campus'}
              </span>
            )}
            <button
              onClick={async () => { await logout(); navigate('/recruiter/login'); }}
              aria-label="Sign out"
              className="w-10 h-10 flex items-center justify-center border border-rule text-ink-soft hover:text-oxblood hover:border-oxblood bg-transparent cursor-pointer"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-[1180px] mx-auto px-4 sm:px-6 py-10">{children}</main>
    </div>
  );
}

function Notice({ title, children }) {
  return (
    <div className="max-w-[620px] mx-auto bg-paper border border-rule p-6 sm:p-8 mt-8">
      <h1 className="font-display text-[28px] font-semibold text-oxblood m-0 mb-3">{title}</h1>
      <p className="text-ink-soft text-[15px] leading-relaxed m-0">{children}</p>
    </div>
  );
}

function RegisterForm({ onDone }) {
  const userId = useAuthStore((s) => s.userId);
  const [form, setForm] = useState({ name: '', company: '', designation: '', company_website: '' });
  const [agreed, setAgreed] = useState(false);
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const valid = form.name.trim() && form.company.trim() && agreed;

  const submit = async (e) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    try {
      const { current_policy_version } = await privacyAPI.getConsent(userId);
      await recruiterAPI.register({ ...form, accepted_terms: true, policy_version: current_policy_version });
      onDone();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not register. Try again.');
      setSaving(false);
    }
  };

  return (
    <div className="max-w-[560px] mx-auto">
      <p className="kicker mb-3">Recruiter registration</p>
      <h1 className="font-display text-[clamp(2rem,5vw,2.6rem)] font-semibold text-oxblood leading-tight m-0">Tell us about your company</h1>
      <p className="text-ink-soft text-[15px] leading-relaxed mt-3 mb-7">
        We verify every recruiter by hand before they can see students. Use your work details so we can confirm you quickly.
      </p>
      <form onSubmit={submit} className="grid gap-4">
        <div><label className={labelClass} htmlFor="rn">Your full name *</label><input id="rn" className={inputClass} value={form.name} onChange={set('name')} /></div>
        <div><label className={labelClass} htmlFor="rc">Company *</label><input id="rc" className={inputClass} value={form.company} onChange={set('company')} /></div>
        <div><label className={labelClass} htmlFor="rd">Your designation</label><input id="rd" className={inputClass} value={form.designation} onChange={set('designation')} placeholder="e.g. Talent Acquisition Lead" /></div>
        <div><label className={labelClass} htmlFor="rw">Company website</label><input id="rw" className={inputClass} value={form.company_website} onChange={set('company_website')} placeholder="https://" /></div>

        <label className="flex items-start gap-3 cursor-pointer text-[14px] leading-relaxed text-ink mt-2">
          <input type="checkbox" checked={agreed} onChange={() => setAgreed((v) => !v)} className="mt-1 w-[17px] h-[17px] shrink-0 cursor-pointer accent-[var(--oxblood)]" />
          <span>
            I agree to the <a href="/terms" target="_blank" rel="noreferrer" className="text-oxblood underline">Terms of Use</a>, including the
            Recruiter Terms, and the <a href="/privacy" target="_blank" rel="noreferrer" className="text-oxblood underline">Privacy Policy</a>.
            I will use candidate data only to evaluate candidates for roles at my company, will not copy, share or sell it, and will delete it
            once it is no longer needed for that purpose.
          </span>
        </label>

        <button type="submit" disabled={!valid || saving} className={`${primaryBtn} mt-2 w-full ${valid && !saving ? btnOn : btnOff}`}>
          {saving && <Loader2 size={16} className="animate-spin" />} Submit for approval
        </button>
      </form>
    </div>
  );
}

function Dashboard({ recruiter }) {
  const saved = recruiter.preferences || {};
  const [prefs, setPrefs] = useState({
    target_role: saved.target_role || '',
    skills: (saved.skills || []).join(', '),
    min_score: saved.min_score ?? '',
  });
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [openId, setOpenId] = useState(null);
  // Stable so the detail panel doesn't refetch (and re-log a view) on re-render.
  const closeDetail = useCallback(() => setOpenId(null), []);

  const toPayload = () => ({
    target_role: prefs.target_role.trim() || null,
    skills: prefs.skills.split(',').map((s) => s.trim()).filter(Boolean).slice(0, 20),
    min_score: prefs.min_score === '' ? null : Math.max(0, Math.min(100, Number(prefs.min_score))),
  });

  const runSearch = async (e) => {
    e?.preventDefault();
    setSearching(true);
    try {
      const payload = toPayload();
      const [data] = await Promise.all([recruiterAPI.search(payload), recruiterAPI.savePreferences(payload)]);
      setResults(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Search failed. Try again.');
    } finally {
      setSearching(false);
    }
  };

  // Run the saved search on first load.
  useEffect(() => { runSearch(); }, []);

  return (
    <div className="grid lg:grid-cols-[320px_1fr] gap-8 items-start">
      <aside className="bg-paper border border-rule p-5 lg:sticky lg:top-6">
        <h2 className="font-display text-[22px] font-semibold text-ink m-0 mb-1">What you're hiring for</h2>
        <p className="text-ink-soft text-[13px] leading-relaxed m-0 mb-4">We rank opted-in students by skill match, verified practice scores and target role.</p>
        <form onSubmit={runSearch} className="grid gap-4">
          <div>
            <label className={labelClass} htmlFor="pr">Role</label>
            <input id="pr" className={inputClass} value={prefs.target_role} onChange={(e) => setPrefs((p) => ({ ...p, target_role: e.target.value }))} placeholder="e.g. Backend Engineer" />
          </div>
          <div>
            <label className={labelClass} htmlFor="ps">Must-have skills</label>
            <input id="ps" className={inputClass} value={prefs.skills} onChange={(e) => setPrefs((p) => ({ ...p, skills: e.target.value }))} placeholder="Python, SQL, REST APIs" />
            <p className="text-[12px] text-ink-soft mt-1 mb-0">Comma-separated</p>
          </div>
          <div>
            <label className={labelClass} htmlFor="pm">Minimum practice score</label>
            <input id="pm" type="number" min="0" max="100" className={inputClass} value={prefs.min_score} onChange={(e) => setPrefs((p) => ({ ...p, min_score: e.target.value }))} placeholder="0–100, optional" />
          </div>
          <button type="submit" disabled={searching} className={`${primaryBtn} ${searching ? btnOff : btnOn}`}>
            {searching ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />} Find candidates
          </button>
        </form>
        <DeleteRecruiter />
      </aside>

      <section>
        {!results ? (
          <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div>
        ) : results.candidates.length === 0 ? (
          <div className="bg-paper border border-rule p-8 text-center">
            <p className="font-display text-[22px] text-ink m-0 mb-2">No matching candidates yet</p>
            <p className="text-ink-soft text-[14px] m-0">
              {results.total_visible === 0
                ? 'No students have opted in to recruiter visibility yet.'
                : `${results.total_visible} student${results.total_visible === 1 ? ' is' : 's are'} visible, but none match these filters. Try fewer skills or a lower minimum score.`}
            </p>
          </div>
        ) : (
          <>
            <p className="text-ink-soft text-[13px] mb-4">
              {results.candidates.length} match{results.candidates.length === 1 ? '' : 'es'} · only students who chose to be visible appear here.
            </p>
            <div className="grid gap-3">
              {results.candidates.map((c) => <CandidateCard key={c.id} c={c} onOpen={() => setOpenId(c.id)} />)}
            </div>
          </>
        )}
      </section>

      {openId && <CandidateDetail id={openId} onClose={closeDetail} />}
    </div>
  );
}

function CandidateCard({ c, onOpen }) {
  const edu = c.work
    ? [c.work.current_role, c.work.industry, c.work.years_experience && `${c.work.years_experience} yrs`].filter(Boolean).join(' · ')
    : [c.education?.institution, c.education?.major, c.education?.year].filter(Boolean).join(' · ');
  return (
    <article className="bg-paper border border-rule p-5 flex gap-5 items-start flex-wrap sm:flex-nowrap">
      <div className="w-16 shrink-0 text-center">
        <div className="font-display text-[30px] font-semibold text-oxblood leading-none">{c.fit ?? '—'}</div>
        <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft mt-1">Fit</div>
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="m-0 text-[17px] font-semibold text-ink flex flex-wrap items-center gap-2">{c.name}{c.consistent_learner && <ConsistentBadge />}</h3>
        {c.field_label && <p className="m-0 font-mono text-[10px] uppercase tracking-[0.12em] text-oxblood mt-0.5">{c.field_label}</p>}
        <p className="m-0 text-[13px] text-ink-soft">{c.target_role || 'No target role'}{edu && ` · ${edu}`}</p>
        <div className="flex flex-wrap gap-1.5 mt-3">
          {c.top_skills.map((s) => (
            <span key={s.name} className={`text-[12px] px-2 py-0.5 border ${c.matched_skills.some((m) => s.name.toLowerCase().includes(m) || m.includes(s.name.toLowerCase())) ? 'border-oxblood text-oxblood' : 'border-rule text-ink-soft'}`}>
              {s.name} {s.proficiency}/10
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-1 mt-3 text-[12.5px] text-ink-soft">
          {Object.entries(c.sandbox).map(([type, s]) => (
            <span key={type}>{SANDBOX_LABEL[type] || type}: <strong className="text-ink">{s.average}</strong> avg ({s.count})</span>
          ))}
          {Object.keys(c.sandbox).length === 0 && <span>No practice results yet</span>}
        </div>
      </div>
      <button onClick={onOpen} className={`${primaryBtn} py-2 px-4 text-[11px] border-ink text-ink bg-transparent cursor-pointer hover:border-oxblood hover:text-oxblood shrink-0`}>
        View profile
      </button>
    </article>
  );
}

function CandidateDetail({ id, onClose }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    recruiterAPI.candidate(id).then(setD).catch((err) => {
      toast.error(err?.response?.data?.detail || 'This candidate is no longer available.');
      onClose();
    });
  }, [id, onClose]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Candidate profile">
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <div className="relative w-full max-w-[560px] h-full overflow-y-auto bg-bone border-l border-rule p-6 sm:p-8">
        <button onClick={onClose} aria-label="Close" className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center border border-rule bg-transparent text-ink-soft cursor-pointer hover:text-oxblood">
          <X size={16} />
        </button>
        {!d ? (
          <div className="flex justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div>
        ) : (
          <>
            <p className="kicker mb-2">Candidate</p>
            <h2 className="font-display text-[30px] font-semibold text-oxblood m-0">{d.name}</h2>
            {d.consistent_learner && <div className="mt-2"><ConsistentBadge /></div>}
            {d.field_label && <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft m-0 mt-1">{d.field_label}</p>}
            <p className="text-ink-soft text-[14px] m-0 mt-1">{d.target_role}</p>
            {d.work && (
              <p className="text-ink-soft text-[13px] m-0 mt-1">
                Working professional · {[d.work.current_role, d.work.industry, d.work.years_experience && `${d.work.years_experience} yrs experience`].filter(Boolean).join(' · ')}
              </p>
            )}
            <p className="text-ink-soft text-[13px] m-0 mt-1">
              {[d.education?.institution, d.education?.major, d.education?.year].filter(Boolean).join(' · ')}
              {d.education?.verified_by_college && <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.12em] px-1.5 py-0.5 border border-ink text-ink">Verified by college</span>}
            </p>

            <div className="mt-5 grid gap-1.5 text-[14px]">
              {d.email && <a href={`mailto:${d.email}`} className="text-oxblood underline">{d.email}</a>}
              {Object.entries(d.links || {}).map(([k, v]) => (
                <a key={k} href={v.startsWith('http') ? v : `https://${v}`} target="_blank" rel="noreferrer" className="text-oxblood underline inline-flex items-center gap-1">
                  {k} <ExternalLink size={12} />
                </a>
              ))}
            </div>

            <h3 className="font-display text-[20px] text-ink mt-7 mb-2">Practice scores</h3>
            {Object.keys(d.sandbox).length === 0 ? <p className="text-ink-soft text-[14px] m-0">No completed practice sessions yet.</p> : (
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(d.sandbox).map(([type, s]) => (
                  <div key={type} className="bg-paper border border-rule p-3">
                    <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-soft">{SANDBOX_LABEL[type] || type}</div>
                    <div className="font-display text-[26px] text-ink">{s.average}</div>
                    <div className="text-[12px] text-ink-soft">best {s.best} · {s.count} done</div>
                  </div>
                ))}
              </div>
            )}
            {d.integrity?.sessions > 0 && (
              <p className="text-[12.5px] text-ink-soft mt-2 mb-0" title="Tab and paste counts come from the candidate's browser: treat them as signals, not proof. Timing comes from Delta's server.">
                {d.integrity.timed} of {d.integrity.sessions} sessions timed · {d.integrity.with_notes === 0 ? 'no integrity notes' : `${d.integrity.with_notes} with integrity notes (see below)`}
              </p>
            )}

            {Object.keys(d.theory_skill_breakdown || {}).length > 0 && (
              <>
                <h3 className="font-display text-[20px] text-ink mt-7 mb-2">Technical test, by skill</h3>
                <div className="grid gap-2">
                  {Object.entries(d.theory_skill_breakdown).map(([skill, s]) => {
                    const pct = s.total ? Math.round((100 * s.correct) / s.total) : 0;
                    return (
                      <div key={skill}>
                        <div className="flex justify-between text-[13px]"><span className="text-ink">{skill}</span><span className="text-ink-soft">{s.correct}/{s.total}</span></div>
                        <div className="h-1.5 bg-accent-surface mt-1"><div className="h-full bg-oxblood" style={{ width: `${pct}%` }} /></div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            <h3 className="font-display text-[20px] text-ink mt-7 mb-2">Skills</h3>
            <div className="flex flex-wrap gap-1.5">
              {d.skills.map((s) => <span key={s.name} className="text-[12px] px-2 py-0.5 border border-rule text-ink-soft">{s.name} {s.proficiency}/10</span>)}
            </div>

            {d.recent_sessions.length > 0 && (
              <>
                <h3 className="font-display text-[20px] text-ink mt-7 mb-2">Recent sessions</h3>
                <ul className="m-0 p-0 list-none grid gap-1.5">
                  {d.recent_sessions.map((s, i) => (
                    <li key={i} className="text-[13px] border-b border-rule pb-1.5">
                      <div className="flex justify-between gap-3">
                        <span className="text-ink truncate">
                          {s.title}
                          {s.timed && <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.12em] px-1.5 py-0.5 border border-rule text-ink-soft">Timed</span>}
                        </span>
                        <span className="text-ink-soft shrink-0">{s.score}/100</span>
                      </div>
                      {s.flags?.length > 0 && <p className="m-0 mt-0.5 text-[12px] text-ink-soft">{s.flags.join(' · ')}</p>}
                    </li>
                  ))}
                </ul>
              </>
            )}

            <p className="text-[12px] text-ink-soft leading-relaxed mt-8">
              This student opted in to being visible. Your view has been logged and they can see that your company viewed their profile.
              Use this data only to assess them for roles at your company.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function DeleteRecruiter() {
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);

  const remove = async () => {
    setBusy(true);
    try {
      await recruiterAPI.deleteAccount();
      toast.success('Your recruiter account has been deleted.');
      await logout();
      navigate('/');
    } catch (err) {
      toast.error('Could not delete your account. Try again.');
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="mt-6 text-[12px] text-ink-soft underline bg-transparent border-0 p-0 cursor-pointer hover:text-oxblood">
        Delete my recruiter account
      </button>
    );
  }
  return (
    <div className="mt-6 pt-4 border-t border-rule">
      <label htmlFor="rdel" className="block text-[12px] text-ink mb-1.5">Type <strong>DELETE</strong> to permanently delete your account</label>
      <div className="flex gap-2">
        <input id="rdel" value={text} onChange={(e) => setText(e.target.value)} className={`${inputClass} py-2`} autoComplete="off" />
        <button onClick={remove} disabled={text !== 'DELETE' || busy} aria-label="Delete account" className={`px-3 border ${text === 'DELETE' ? btnOn : btnOff}`}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
        </button>
      </div>
    </div>
  );
}
