import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, Plus, Play, Trash2, ChevronDown, ChevronUp, ShieldCheck, BookOpen } from 'lucide-react';
import { toast } from 'sonner';
import { schoolAPI } from '../../lib/api';
import { enterChildMode } from '../../lib/childMode';
import { useAuthStore } from '../../store/authStore';

const inputClass = 'w-full bg-paper border border-rule px-3.5 py-3 text-ink placeholder:text-ink-soft text-sm outline-none focus:border-oxblood box-border';
const labelClass = 'block text-[13px] font-semibold text-ink mb-1.5';
const btn = 'inline-flex items-center justify-center gap-2 px-4 py-2.5 border font-mono text-[11px] uppercase tracking-[0.12em] transition-colors';
const btnPrimary = 'bg-oxblood text-bone border-oxblood cursor-pointer hover:bg-ink hover:border-ink';
const btnGhost = 'bg-transparent text-ink border-ink cursor-pointer hover:border-oxblood hover:text-oxblood';
const btnOff = 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed';

/** Delta for School — the parent's page: add children (with parental consent), see progress, start child mode. */
export default function SchoolParent() {
  const userId = useAuthStore((s) => s.userId);
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [isReviewer, setIsReviewer] = useState(false);

  const load = () => schoolAPI.listChildren(userId).then(setData).catch(() => toast.error('Could not load Delta for School.'));
  useEffect(() => {
    if (!userId) return;
    load();
    schoolAPI.reviewerMe().then((r) => setIsReviewer(r.is_reviewer)).catch(() => {});
  }, [userId]); // eslint-disable-line

  const start = (child) => {
    enterChildMode(userId, child.id);
    navigate(`/school/learn/${child.id}`);
  };

  if (!data) {
    return <div className="min-h-screen bg-bone flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div>;
  }

  return (
    <main className="min-h-screen bg-bone text-ink px-4 pt-24 pb-16">
      <div className="max-w-[820px] mx-auto">
        <header className="mb-8">
          <p className="kicker mb-3">Delta for School · {data.board} classes {data.grades[0]}–{data.grades[data.grades.length - 1]}</p>
          <h1 className="font-display text-[clamp(2rem,5vw,2.8rem)] font-semibold text-oxblood leading-tight m-0">Learning your child can do at their own pace.</h1>
          <p className="text-ink-soft text-[15px] leading-relaxed mt-3 m-0">
            Chapter-by-chapter lessons and quizzes that follow the NCERT syllabus, checked by a person before your child sees them.
            You set it up and stay in charge. Your child learns inside your account and needs your PIN to leave it.
          </p>
          {isReviewer && (
            <Link to="/school/review" className="inline-flex items-center gap-1.5 mt-4 text-[13px] text-oxblood no-underline hover:underline">
              <ShieldCheck size={14} /> Review lessons
            </Link>
          )}
        </header>

        {data.children.length > 0 && (
          <section className="grid gap-3 mb-6">
            {data.children.map((c) => <ChildCard key={c.id} child={c} onStart={() => start(c)} onRemoved={load} />)}
          </section>
        )}

        {showForm || data.children.length === 0 ? (
          <AddChildForm grades={data.grades} onAdded={() => { setShowForm(false); load(); }} onCancel={data.children.length ? () => setShowForm(false) : null} />
        ) : (
          <button onClick={() => setShowForm(true)} className={`${btn} ${btnGhost}`}><Plus size={14} /> Add a child</button>
        )}

        <section className="mt-10 bg-paper border border-rule p-5 text-[13.5px] text-ink-soft leading-relaxed">
          <p className="m-0 mb-2 font-semibold text-ink">How we protect your child</p>
          <ul className="m-0 pl-5">
            <li>We store only your child's first name, class, and their lesson progress and quiz scores.</li>
            <li>No ads, no tracking and no profiling. Children are never shown to recruiters.</li>
            <li>Your child doesn't chat with an AI. Every lesson is written in advance and reviewed by a person.</li>
            <li>Remove a child at any time and all their data is deleted. See the <a href="/privacy" className="text-oxblood underline">Privacy Policy</a>, Section 9.</li>
          </ul>
        </section>
      </div>
    </main>
  );
}

function ChildCard({ child, onStart, onRemoved }) {
  const userId = useAuthStore((s) => s.userId);
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    setOpen((o) => !o);
    if (!detail) schoolAPI.childHome(userId, child.id).then(setDetail).catch(() => toast.error('Could not load progress.'));
  };

  const remove = async () => {
    setBusy(true);
    try {
      await schoolAPI.removeChild(userId, child.id);
      toast.success(`${child.first_name}'s profile and progress were deleted.`);
      onRemoved();
    } catch {
      toast.error('Could not remove this profile.');
      setBusy(false);
    }
  };

  return (
    <article className="bg-paper border border-rule p-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="m-0 font-display text-[24px] font-semibold text-ink">{child.first_name}</h2>
          <p className="m-0 text-[13px] text-ink-soft">
            Class {child.grade} · {child.chapters_done} chapter{child.chapters_done === 1 ? '' : 's'} done
            {child.average_score !== null && ` · average best score ${child.average_score}%`}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={toggle} className={`${btn} ${btnGhost}`}>{open ? <ChevronUp size={14} /> : <ChevronDown size={14} />} Progress</button>
          <button onClick={onStart} className={`${btn} ${btnPrimary}`}><Play size={14} /> Start learning</button>
        </div>
      </div>

      {open && (
        <div className="mt-5 pt-5 border-t border-rule">
          {!detail ? <Loader2 className="w-5 h-5 animate-spin text-ink-soft" /> : (
            <div className="grid sm:grid-cols-2 gap-5">
              {detail.subjects.map((s) => (
                <div key={s.subject}>
                  <p className="m-0 mb-2 text-[13px] font-semibold text-ink">{s.label}</p>
                  <ul className="m-0 p-0 list-none grid gap-1">
                    {s.chapters.map((ch) => (
                      <li key={ch.chapter_no} className="flex justify-between gap-3 text-[13px]">
                        <span className={ch.available ? 'text-ink' : 'text-ink-soft'}>{ch.chapter_no}. {ch.title}</span>
                        <span className="text-ink-soft shrink-0">{ch.best_score != null ? `${ch.best_score}%` : ch.available ? '—' : 'soon'}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
          <div className="mt-5">
            {confirming ? (
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[13px] text-ink">Delete {child.first_name}'s profile and all progress? This can't be undone.</span>
                <button onClick={remove} disabled={busy} className={`${btn} ${btnPrimary}`}>{busy ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />} Delete</button>
                <button onClick={() => setConfirming(false)} className="text-[13px] text-ink-soft underline bg-transparent border-0 cursor-pointer">Cancel</button>
              </div>
            ) : (
              <button onClick={() => setConfirming(true)} className="text-[12px] text-ink-soft underline bg-transparent border-0 p-0 cursor-pointer hover:text-oxblood">
                Remove {child.first_name} and withdraw consent
              </button>
            )}
          </div>
        </div>
      )}
    </article>
  );
}

function AddChildForm({ grades, onAdded, onCancel }) {
  const userId = useAuthStore((s) => s.userId);
  const [form, setForm] = useState({ first_name: '', grade: '', pin: '', pin2: '' });
  const [guardian, setGuardian] = useState(false);
  const [consent, setConsent] = useState(false);
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const pinOk = /^\d{4,6}$/.test(form.pin) && form.pin === form.pin2;
  const valid = form.first_name.trim() && form.grade && pinOk && guardian && consent;

  const submit = async (e) => {
    e.preventDefault();
    if (!valid) return;
    setSaving(true);
    try {
      await schoolAPI.addChild(userId, {
        first_name: form.first_name.trim(), grade: Number(form.grade), pin: form.pin,
        is_parent_or_guardian: guardian, consent,
      });
      toast.success('Profile added.');
      onAdded();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not add this profile.');
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="bg-paper border border-rule p-5 sm:p-6 grid gap-4">
      <h2 className="m-0 font-display text-[22px] font-semibold text-ink flex items-center gap-2"><BookOpen size={18} /> Add your child</h2>
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className={labelClass} htmlFor="cf">Child's first name</label>
          <input id="cf" className={inputClass} value={form.first_name} onChange={set('first_name')} maxLength={40} autoComplete="off" />
          <p className="text-[12px] text-ink-soft mt-1 mb-0">First name only. We don't need anything else.</p>
        </div>
        <div>
          <label className={labelClass} htmlFor="cg">Class</label>
          <select id="cg" className={inputClass} value={form.grade} onChange={set('grade')}>
            <option value="">Choose…</option>
            {grades.map((g) => <option key={g} value={g}>Class {g}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass} htmlFor="cp">Parent PIN (4–6 digits)</label>
          <input id="cp" type="password" inputMode="numeric" className={inputClass} value={form.pin} onChange={set('pin')} maxLength={6} autoComplete="new-password" />
          <p className="text-[12px] text-ink-soft mt-1 mb-0">Needed to leave your child's learning screen. Don't share it with your child.</p>
        </div>
        <div>
          <label className={labelClass} htmlFor="cp2">Repeat PIN</label>
          <input id="cp2" type="password" inputMode="numeric" className={inputClass} value={form.pin2} onChange={set('pin2')} maxLength={6} autoComplete="new-password" />
          {form.pin2 && !pinOk && <p className="text-[12px] text-oxblood mt-1 mb-0">PINs must match and be 4–6 digits.</p>}
        </div>
      </div>

      <label className="flex items-start gap-3 cursor-pointer text-[14px] leading-relaxed text-ink">
        <input type="checkbox" checked={guardian} onChange={() => setGuardian((v) => !v)} className="mt-1 w-[17px] h-[17px] shrink-0 cursor-pointer accent-[var(--oxblood)]" />
        <span>I am this child's parent or legal guardian, and I am 18 or older.</span>
      </label>
      <label className="flex items-start gap-3 cursor-pointer text-[14px] leading-relaxed text-ink">
        <input type="checkbox" checked={consent} onChange={() => setConsent((v) => !v)} className="mt-1 w-[17px] h-[17px] shrink-0 cursor-pointer accent-[var(--oxblood)]" />
        <span>
          I give my verifiable consent for Delta to process my child's first name, class, lesson progress and quiz scores, only to provide
          Delta for School, as described in the <a href="/privacy" target="_blank" rel="noreferrer" className="text-oxblood underline">Privacy Policy</a>.
          I can withdraw it and delete my child's data at any time.
        </span>
      </label>

      <div className="flex gap-3 flex-wrap">
        <button type="submit" disabled={!valid || saving} className={`${btn} ${valid && !saving ? btnPrimary : btnOff}`}>
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Add child
        </button>
        {onCancel && <button type="button" onClick={onCancel} className="text-[13px] text-ink-soft underline bg-transparent border-0 cursor-pointer">Cancel</button>}
      </div>
    </form>
  );
}
