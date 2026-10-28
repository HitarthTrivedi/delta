import React, { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Download, Loader2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { companyAPI } from '../../lib/api';

// Company roadmaps, recruiter side: build a roadmap from the skills you need
// (or a job ad), Delta reviews it, students in your pool follow it, and you
// see their progress, skill scores and your own tests' results.

const btn = 'inline-flex items-center gap-1.5 px-3.5 py-2 border font-mono text-[11px] uppercase tracking-[0.12em] cursor-pointer disabled:opacity-50';
const input = 'border border-rule bg-paper px-3 py-2 text-[14px] text-ink';
const errText = (err, fallback) => err?.response?.data?.detail || fallback;
const STATUS = { draft: 'Draft', pending_review: 'Waiting for Delta review', approved: 'Live', rejected: 'Changes requested', archived: 'Archived' };
const KIND = { learn: 'Learn', practice: 'Practise', project: 'Build', test: 'Test', interview: 'Speak', career: 'Career' };

function Builder({ existing, onSaved, onCancel }) {
  const [mode, setMode] = useState('skills');
  const [skillsText, setSkillsText] = useState((existing?.skills || []).join(', '));
  const [ad, setAd] = useState('');
  const [weeks, setWeeks] = useState(existing?.weeks || 8);
  const [draft, setDraft] = useState(existing ? { skills: existing.skills, milestones: existing.milestones } : null);
  const [meta, setMeta] = useState({ title: existing?.title || '', role: existing?.role || '', summary: existing?.summary || '' });
  const [busy, setBusy] = useState('');

  const build = async () => {
    setBusy('draft');
    try {
      const d = mode === 'skills'
        ? await companyAPI.draftFromSkills(skillsText.split(',').map((s) => s.trim()).filter(Boolean), Number(weeks))
        : await companyAPI.draftFromText(ad, Number(weeks));
      setDraft({ skills: d.skills, milestones: d.milestones });
      setSkillsText(d.skills.join(', '));
      if (d.title && !meta.title) setMeta((m) => ({ ...m, title: d.title, role: d.role || m.role }));
    } catch (err) {
      toast.error(errText(err, 'Could not build a draft.'));
    } finally {
      setBusy('');
    }
  };

  const setStep = (i, patch) => setDraft((d) => ({ ...d, milestones: d.milestones.map((m, j) => (j === i ? { ...m, ...patch } : m)) }));
  const save = async () => {
    setBusy('save');
    const payload = { ...meta, skills: draft.skills, milestones: draft.milestones, weeks: Number(weeks) };
    try {
      onSaved(existing ? await companyAPI.update(existing.id, payload) : await companyAPI.create(payload));
      toast.success('Saved as a draft. Submit it when it looks right.');
    } catch (err) {
      toast.error(errText(err, 'Could not save.'));
    } finally {
      setBusy('');
    }
  };

  return (
    <section className="bg-paper border border-rule p-5 grid gap-4">
      <h2 className="font-display text-[22px] font-semibold text-ink m-0">{existing ? 'Edit roadmap' : 'New roadmap'}</h2>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Start from">
        {[['skills', 'From skills'], ['ad', 'From a job ad']].map(([k, label]) => (
          <button key={k} onClick={() => setMode(k)} aria-pressed={mode === k} className={`${btn} ${mode === k ? 'border-ink bg-ink text-bone' : 'border-rule text-ink'}`}>{label}</button>
        ))}
      </div>
      {mode === 'skills'
        ? <input className={input} value={skillsText} onChange={(e) => setSkillsText(e.target.value)} placeholder="Skills you hire for, comma-separated: SQL, Excel, Communication" aria-label="Skills" />
        : <textarea className={`${input} min-h-[120px]`} value={ad} onChange={(e) => setAd(e.target.value)} placeholder="Paste the job description" aria-label="Job description" />}
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-[13px] text-ink-soft flex items-center gap-2">Weeks
          <input type="number" min={4} max={16} className={`${input} w-20`} value={weeks} onChange={(e) => setWeeks(e.target.value)} />
        </label>
        <button className={`${btn} border-ink text-ink`} disabled={!!busy || (mode === 'skills' ? !skillsText.trim() : ad.trim().length < 40)} onClick={build}>
          {busy === 'draft' && <Loader2 size={12} className="animate-spin" />} {draft ? 'Rebuild steps' : 'Build the steps'}
        </button>
      </div>
      <p className="m-0 text-[12.5px] text-ink-soft">Steps come from Delta's reviewed skill library. Edit any wording; Delta checks every roadmap before students see it.</p>

      {draft && (
        <>
          <div className="grid gap-2 sm:grid-cols-2">
            <input className={input} placeholder="Title, e.g. Ready for our analyst role" value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} aria-label="Title" />
            <input className={input} placeholder="Role (optional)" value={meta.role} onChange={(e) => setMeta({ ...meta, role: e.target.value })} aria-label="Role" />
            <textarea className={`${input} sm:col-span-2`} placeholder="One or two lines for students: who this is for and what you look for" value={meta.summary} onChange={(e) => setMeta({ ...meta, summary: e.target.value })} aria-label="Summary" />
          </div>
          <ol className="m-0 pl-0 list-none grid gap-2">
            {draft.milestones.map((m, i) => (
              <li key={m.id || i} className="border border-rule p-3 grid gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-ink-soft">{i + 1} · {m.skill} · {KIND[m.kind] || m.kind}</span>
                  <button aria-label="Remove step" className="bg-transparent border-0 text-ink-soft cursor-pointer p-1" onClick={() => setDraft((d) => ({ ...d, milestones: d.milestones.filter((_, j) => j !== i) }))}><Trash2 size={13} /></button>
                </div>
                <input className={input} value={m.title} onChange={(e) => setStep(i, { title: e.target.value })} aria-label={`Step ${i + 1} title`} />
                <input className={`${input} text-[13px]`} value={m.detail} onChange={(e) => setStep(i, { detail: e.target.value })} aria-label={`Step ${i + 1} detail`} />
              </li>
            ))}
          </ol>
          <div className="flex flex-wrap gap-2">
            <button className={`${btn} border-oxblood bg-oxblood text-bone`} disabled={!!busy || !meta.title.trim() || !draft.milestones.length} onClick={save}>
              {busy === 'save' && <Loader2 size={12} className="animate-spin" />} Save draft
            </button>
            <button className={`${btn} border-rule text-ink-soft`} onClick={onCancel}>Cancel</button>
          </div>
        </>
      )}
      {!draft && <button className={`${btn} border-rule text-ink-soft justify-self-start`} onClick={onCancel}>Cancel</button>}
    </section>
  );
}

function Students({ roadmap }) {
  const { data, isLoading } = useQuery({ queryKey: ['company-students', roadmap.id], queryFn: () => companyAPI.students(roadmap.id) });
  const download = async () => {
    try {
      const url = URL.createObjectURL(await companyAPI.studentsCsv(roadmap.id));
      const a = document.createElement('a');
      a.href = url;
      a.download = `roadmap-students-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Could not export.'); }
  };
  if (isLoading) return <Loader2 size={16} className="animate-spin text-ink-soft" />;
  const students = data?.students || [];
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="m-0 text-[16px] font-semibold">Students following ({students.length})</h3>
        {students.length > 0 && <button className={`${btn} border-rule text-ink`} onClick={download}><Download size={12} /> CSV</button>}
      </div>
      <p className="m-0 mt-1 text-[13px] text-ink-soft">Only students who chose to share this roadmap with you, and only while they do.</p>
      {students.length ? (
        <div className="mt-2 overflow-x-auto border border-rule bg-paper">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="text-left text-ink-soft font-mono text-[10.5px] uppercase tracking-[0.1em]">
                <th className="px-3 py-2 font-normal">Student</th><th className="px-3 py-2 font-normal">Progress</th>
                <th className="px-3 py-2 font-normal">Readiness</th><th className="px-3 py-2 font-normal">Your skills</th>
                <th className="px-3 py-2 font-normal">Your tests</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.user_id} className="border-t border-rule align-top">
                  <td className="px-3 py-2"><span className="font-semibold text-ink">{s.name}</span><br /><span className="text-ink-soft">{s.education?.institution || s.target_role || ''}{s.education?.verified_by_college ? ' · verified by college' : ''}</span></td>
                  <td className="px-3 py-2 tabular-nums">{s.done}/{s.total} steps · week {s.week} of {s.weeks}<br /><span className="text-ink-soft">{s.on_track ? 'On track' : 'Catching up'}</span></td>
                  <td className="px-3 py-2 tabular-nums">{s.readiness ?? '—'} <span className="text-ink-soft">{s.readiness_label}</span></td>
                  <td className="px-3 py-2 text-ink-soft">{s.skills.map((k) => `${k.skill} ${k.score ?? '—'}`).join(' · ')}</td>
                  <td className="px-3 py-2 text-ink-soft">{s.tests.length ? s.tests.map((t) => `${t.title}: ${t.score ?? t.status}${t.notes.length ? ` (${t.notes.join('; ')})` : ''}`).join(' · ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="mt-2 text-[14px] text-ink-soft">No one yet.</p>}
    </section>
  );
}

function Tests({ roadmap }) {
  const queryClient = useQueryClient();
  const key = ['company-tests', roadmap.id];
  const { data } = useQuery({ queryKey: key, queryFn: () => companyAPI.tests(roadmap.id) });
  const [form, setForm] = useState({ category: 'technical', topic: '', area: 'quantitative', difficulty: 'medium', num_questions: 10, timed: true, due_date: '' });
  const [busy, setBusy] = useState(false);
  const create = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await companyAPI.createTest(roadmap.id, { ...form, topic: form.category === 'technical' ? form.topic : null,
        area: form.category === 'aptitude' ? form.area : null, num_questions: Number(form.num_questions), due_date: form.due_date || null });
      queryClient.invalidateQueries({ queryKey: key });
      queryClient.invalidateQueries({ queryKey: ['company-students', roadmap.id] });
      toast.success('Test ready. Students on this roadmap see it in their weekly plan.');
    } catch (err) {
      toast.error(errText(err, 'Could not make the test.'));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section>
      <h3 className="m-0 text-[16px] font-semibold">Your tests</h3>
      <p className="m-0 mt-1 text-[13px] text-ink-soft">Made once; every student gets the same questions, and sees the answers only after the test closes.</p>
      <form onSubmit={create} className="mt-2 border border-dashed border-rule p-3 grid gap-2 sm:grid-cols-6">
        <select className={`${input} sm:col-span-2`} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} aria-label="Kind">
          <option value="technical">Technical topic</option><option value="aptitude">Aptitude</option>
        </select>
        {form.category === 'technical'
          ? <input className={`${input} sm:col-span-4`} required maxLength={120} placeholder="Topic, e.g. SQL joins" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} />
          : <select className={`${input} sm:col-span-4`} value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} aria-label="Area">
              <option value="quantitative">Quantitative</option><option value="logical">Logical reasoning</option><option value="verbal">Verbal</option>
            </select>}
        <select className={input} value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value })} aria-label="Difficulty">
          <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
        </select>
        <label className="text-[13px] text-ink-soft flex items-center gap-1.5">Questions
          <input type="number" min={5} max={20} className={`${input} w-16`} value={form.num_questions} onChange={(e) => setForm({ ...form, num_questions: e.target.value })} />
        </label>
        <label className="text-[13px] text-ink-soft flex items-center gap-1.5"><input type="checkbox" checked={form.timed} onChange={() => setForm({ ...form, timed: !form.timed })} /> Timed</label>
        <label className="text-[13px] text-ink-soft flex items-center gap-1.5 sm:col-span-2">Due
          <input type="date" min={new Date().toISOString().slice(0, 10)} className={input} value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
        </label>
        <button type="submit" disabled={busy} className={`${btn} border-ink text-ink justify-center`}>{busy && <Loader2 size={12} className="animate-spin" />} {busy ? 'Making…' : 'Set test'}</button>
      </form>
      <ul className="m-0 mt-2 p-0 list-none border border-rule bg-paper divide-y divide-rule">
        {(data?.tests || []).map((t) => (
          <li key={t.id} className="px-4 py-3 text-[14px] flex flex-wrap items-center justify-between gap-2">
            <span><span className="font-semibold">{t.title}</span><span className="text-ink-soft"> · {t.questions} questions · {t.taken} of {t.members} done{t.average != null ? ` · avg ${t.average}` : ''} · {t.open ? 'open' : 'closed'}</span></span>
            {t.open && <button className={`${btn} border-rule text-ink-soft`} onClick={async () => {
              try { await companyAPI.closeTest(t.id); queryClient.invalidateQueries({ queryKey: key }); } catch (err) { toast.error(errText(err, 'Could not close.')); }
            }}>Close</button>}
          </li>
        ))}
        {!data?.tests?.length && <li className="px-4 py-3 text-[14px] text-ink-soft">No tests yet.</li>}
      </ul>
    </section>
  );
}

function Detail({ roadmap, onBack, onChange, onEdit }) {
  const act = async (fn, msg) => {
    try { onChange(await fn()); toast.success(msg); } catch (err) { toast.error(errText(err, 'Could not update.')); }
  };
  return (
    <div className="grid gap-6">
      <button className="inline-flex items-center gap-1.5 text-[13px] text-ink-soft bg-transparent border-0 cursor-pointer p-0 justify-self-start" onClick={onBack}><ArrowLeft size={14} /> All roadmaps</button>
      <section className="bg-paper border border-rule p-5">
        <p className="m-0 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">{STATUS[roadmap.status]} · {roadmap.weeks} weeks · {roadmap.members} following</p>
        <h2 className="font-display text-[26px] font-semibold text-oxblood m-0 mt-1">{roadmap.title}</h2>
        {roadmap.summary && <p className="m-0 mt-1 text-[14px] text-ink-soft">{roadmap.summary}</p>}
        {roadmap.review_note && <p className="m-0 mt-3 border-l-2 border-oxblood pl-3 text-[14px]">Delta's note: {roadmap.review_note}</p>}
        <ol className="m-0 mt-3 pl-5 text-[13.5px] grid gap-1">
          {roadmap.milestones.map((m) => <li key={m.id}><span className="text-ink">{m.title}</span> <span className="text-ink-soft">· {m.skill}</span></li>)}
        </ol>
        <div className="mt-4 flex flex-wrap gap-2">
          {['draft', 'rejected'].includes(roadmap.status) && <>
            <button className={`${btn} border-ink text-ink`} onClick={onEdit}>Edit</button>
            <button className={`${btn} border-oxblood bg-oxblood text-bone`} onClick={() => act(() => companyAPI.submit(roadmap.id), 'Sent to Delta for review.')}>Submit for review</button>
          </>}
          {roadmap.status === 'approved' && <button className={`${btn} border-rule text-ink-soft`} onClick={() => act(() => companyAPI.archive(roadmap.id), 'Archived. Students no longer get its tasks.')}>Archive</button>}
          <button className={`${btn} border-rule text-ink`} onClick={() => act(() => companyAPI.duplicate(roadmap.id), 'Copied into a new draft.')}>Duplicate</button>
        </div>
      </section>
      {roadmap.status === 'approved' && <><Students roadmap={roadmap} /><Tests roadmap={roadmap} /></>}
    </div>
  );
}

export function RecruiterRoadmaps({ recruiter }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['company-roadmaps'], queryFn: companyAPI.list });
  const [view, setView] = useState({ kind: 'list' });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['company-roadmaps'] });
  useEffect(() => { window.scrollTo?.(0, 0); }, [view.kind]);

  if (view.kind === 'build') {
    return <Builder existing={view.roadmap} onCancel={() => setView(view.roadmap ? { kind: 'detail', roadmap: view.roadmap } : { kind: 'list' })}
      onSaved={(r) => { refresh(); setView({ kind: 'detail', roadmap: r }); }} />;
  }
  if (view.kind === 'detail') {
    return <Detail roadmap={view.roadmap} onBack={() => setView({ kind: 'list' })} onEdit={() => setView({ kind: 'build', roadmap: view.roadmap })}
      onChange={(r) => { refresh(); setView({ kind: 'detail', roadmap: r }); }} />;
  }
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-[24px] font-semibold text-ink m-0">Roadmaps for {recruiter.company}</h2>
          <p className="m-0 mt-1 text-[14px] text-ink-soft max-w-[640px]">
            Tell students what you hire for. They follow your roadmap next to their own plan, and the ones who choose to share it with you show their progress, skill scores and your tests' results here.
            {recruiter.pool === 'campus' ? ' Shown to students of the colleges that linked you.' : ' Shown to students who aren\'t on a college seat.'}
          </p>
        </div>
        <button className={`${btn} border-oxblood bg-oxblood text-bone`} onClick={() => setView({ kind: 'build' })}><Plus size={13} /> New roadmap</button>
      </div>
      {isLoading ? <Loader2 className="w-6 h-6 animate-spin text-ink-soft" /> : (
        <ul className="m-0 p-0 list-none border border-rule bg-paper divide-y divide-rule">
          {(data?.roadmaps || []).map((r) => (
            <li key={r.id}>
              <button className="w-full text-left bg-transparent border-0 px-4 py-3 cursor-pointer flex flex-wrap items-center justify-between gap-2" onClick={() => setView({ kind: 'detail', roadmap: r })}>
                <span className="font-semibold text-ink text-[15px]">{r.title}</span>
                <span className="text-[13px] text-ink-soft">{STATUS[r.status]} · {r.skills.length} skills · {r.weeks} weeks · {r.members} following</span>
              </button>
            </li>
          ))}
          {!data?.roadmaps?.length && <li className="px-4 py-3 text-[14px] text-ink-soft">No roadmaps yet.</li>}
        </ul>
      )}
    </div>
  );
}

export function RoadmapReview() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['company-review'], queryFn: companyAPI.adminQueue });
  const [notes, setNotes] = useState({});
  const review = async (id, approve) => {
    try {
      await companyAPI.adminReview(id, approve, notes[id]);
      queryClient.invalidateQueries({ queryKey: ['company-review'] });
      toast.success(approve ? 'Approved. Students in that pool can now see it.' : 'Sent back with your note.');
    } catch (err) {
      toast.error(errText(err, 'Could not review.'));
    }
  };
  if (isLoading) return <Loader2 className="w-6 h-6 animate-spin text-ink-soft" />;
  if (!data?.roadmaps?.length) return <p className="text-ink-soft text-[14px]">No roadmaps waiting for review.</p>;
  return (
    <div className="grid gap-3">
      <p className="m-0 text-[13px] text-ink-soft">Check that steps are accurate, links work, and nothing asks students for personal data. Unknown skills use a generic learn / prove / test pattern: make sure they make sense.</p>
      {data.roadmaps.map((r) => (
        <article key={r.id} className="bg-paper border border-rule p-5">
          <p className="m-0 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">{r.company} · {r.recruiter_pool === 'campus' ? 'campus' : 'off-campus'} · {r.weeks} weeks</p>
          <h2 className="m-0 mt-1 text-[17px] font-semibold">{r.title}</h2>
          {r.summary && <p className="m-0 mt-1 text-[13.5px] text-ink-soft">{r.summary}</p>}
          <ol className="m-0 mt-2 pl-5 text-[13px] grid gap-1">
            {r.milestones.map((m) => (
              <li key={m.id}><span className="text-ink">{m.title}</span> <span className="text-ink-soft">· {m.skill} · {m.detail}{m.url ? ` · ${m.url}` : ''}{m.link ? ` · ${m.link}` : ''}</span></li>
            ))}
          </ol>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <input className={`${input} flex-1 min-w-[200px]`} placeholder="Note to the company (required to send back)" value={notes[r.id] || ''} onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })} aria-label="Review note" />
            <button className={`${btn} border-oxblood bg-oxblood text-bone`} onClick={() => review(r.id, true)}>Approve</button>
            <button className={`${btn} border-ink text-ink`} onClick={() => review(r.id, false)}>Send back</button>
          </div>
        </article>
      ))}
    </div>
  );
}
