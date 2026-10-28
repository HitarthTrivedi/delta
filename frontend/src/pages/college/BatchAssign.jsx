import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { collegeAPI, templatesAPI } from '../../lib/api';
import { ExportButton, btn, day, errText, input } from './shared';

// What the college sets for a batch: one roadmap everyone follows, and tests
// everyone takes (same questions; answers hidden from students until it closes).

const twoWeeksOut = () => new Date(Date.now() + 14 * 864e5).toISOString().slice(0, 10);

export function BatchRoadmap({ cid, batchId, canEdit }) {
  const queryClient = useQueryClient();
  const { data: batches } = useQuery({ queryKey: ['college-batches', cid], queryFn: () => collegeAPI.batches(cid) });
  const { data: catalog } = useQuery({ queryKey: ['roadmap-catalog'], queryFn: templatesAPI.catalog, enabled: canEdit });
  const [choice, setChoice] = useState('');
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState(false);
  const current = (batches?.batches || []).find((b) => b.id === batchId)?.template;

  const save = async (templateId) => {
    setBusy(true);
    try {
      await collegeAPI.setBatchTemplate(cid, batchId, templateId, templateId ? target : null);
      queryClient.invalidateQueries({ queryKey: ['college-batches', cid] });
      toast.success(templateId ? 'Roadmap set. Every student in this batch now follows it.' : 'Students can now choose their own plan again.');
    } catch (err) {
      toast.error(errText(err, 'Could not save.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="border border-rule bg-paper p-4">
      <h2 className="m-0 text-[15px] font-semibold">Roadmap for this batch</h2>
      <p className="m-0 mt-1 text-[13px] text-ink-soft">
        {current
          ? <>Everyone follows <span className="text-ink font-semibold">{current.title}</span> ({current.following} students)
              {current.target_date ? `, target ${day(current.target_date)}` : ''}. It still adapts to each student, and they can't switch it off while they're in this batch.</>
          : 'No roadmap set: each student follows their own plan.'}
      </p>
      {canEdit && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select className={input} value={choice} onChange={(e) => setChoice(e.target.value)} aria-label="Roadmap">
            <option value="">Choose a roadmap…</option>
            {(catalog?.catalog || []).map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
          <label className="text-[13px] text-ink-soft flex items-center gap-2">Target (optional)
            <input type="date" min={twoWeeksOut()} className={input} value={target} onChange={(e) => setTarget(e.target.value)} />
          </label>
          <button className={`${btn} border-ink text-ink`} disabled={!choice || busy} onClick={() => save(choice)}>
            {busy && <Loader2 size={12} className="animate-spin" />} Set for the batch
          </button>
          {current && <button className={`${btn} border-rule text-ink-soft`} disabled={busy} onClick={() => save(null)}>Stop setting it</button>}
        </div>
      )}
    </section>
  );
}

function Results({ cid, test }) {
  const { data, isLoading } = useQuery({ queryKey: ['college-test-results', test.id], queryFn: () => collegeAPI.testResults(cid, test.id) });
  if (isLoading) return <Loader2 size={14} className="animate-spin text-ink-soft" />;
  if (!data) return null;
  return (
    <div className="mt-3">
      <div className="overflow-x-auto border border-rule">
        <table className="w-full text-[13px] border-collapse">
          <thead>
            <tr className="text-left text-ink-soft font-mono text-[10.5px] uppercase tracking-[0.1em]">
              <th className="px-3 py-2 font-normal">Student</th><th className="px-3 py-2 font-normal">Status</th>
              <th className="px-3 py-2 font-normal">Score</th><th className="px-3 py-2 font-normal">How it was taken</th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s) => (
              <tr key={s.user_id} className="border-t border-rule">
                <td className="px-3 py-2">{s.name}{s.roll_no && <span className="text-ink-soft"> · {s.roll_no}</span>}</td>
                <td className="px-3 py-2 text-ink-soft">{s.status}</td>
                <td className="px-3 py-2 tabular-nums">{s.score ?? '—'}</td>
                <td className="px-3 py-2 text-ink-soft">{s.notes.length ? s.notes.join(' · ') : (s.status === 'done' ? 'no notes' : '')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-2"><ExportButton cid={cid} kind="test_results" params={{ assignment_id: test.id }}>Results CSV</ExportButton></div>
    </div>
  );
}

export function BatchTests({ cid, batchId, canEdit }) {
  const queryClient = useQueryClient();
  const key = ['college-batch-tests', cid, batchId];
  const { data } = useQuery({ queryKey: key, queryFn: () => collegeAPI.batchTests(cid, batchId) });
  const [form, setForm] = useState({ category: 'technical', topic: '', area: 'quantitative', difficulty: 'medium', num_questions: 10, timed: true, due_date: '' });
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState('');

  const create = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await collegeAPI.createTest(cid, batchId, {
        ...form, topic: form.category === 'technical' ? form.topic : null, area: form.category === 'aptitude' ? form.area : null,
        num_questions: Number(form.num_questions), due_date: form.due_date || null,
      });
      queryClient.invalidateQueries({ queryKey: key });
      setForm({ ...form, topic: '' });
      toast.success('Test ready. It shows on each student\'s Today page and weekly plan.');
    } catch (err) {
      toast.error(errText(err, 'Could not make the test.'));
    } finally {
      setBusy(false);
    }
  };

  const close = async (id) => {
    try { await collegeAPI.closeTest(cid, id); queryClient.invalidateQueries({ queryKey: key }); toast.success('Test closed. Students can now review the answers.'); } catch (err) { toast.error(errText(err, 'Could not close.')); }
  };

  return (
    <section>
      <h2 className="m-0 text-[15px] font-semibold">Tests for this batch</h2>
      <p className="m-0 mt-1 text-[13px] text-ink-soft">Everyone gets the same questions. Students see their score straight away, and the answers once the test closes.</p>
      {canEdit && (
        <form onSubmit={create} className="mt-3 border border-dashed border-rule p-3 grid gap-2 sm:grid-cols-6">
          <select className={`${input} sm:col-span-2`} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} aria-label="Kind">
            <option value="technical">Technical topic</option><option value="aptitude">Aptitude</option>
          </select>
          {form.category === 'technical'
            ? <input className={`${input} sm:col-span-4`} required maxLength={120} placeholder="Topic, e.g. DBMS, Java OOP, Data Structures" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} />
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
          <button type="submit" disabled={busy} className={`${btn} border-ink text-ink justify-center`}>
            {busy && <Loader2 size={12} className="animate-spin" />} {busy ? 'Making…' : 'Set test'}
          </button>
        </form>
      )}
      <ul className="m-0 mt-3 p-0 list-none border border-rule bg-paper divide-y divide-rule">
        {(data?.tests || []).map((t) => (
          <li key={t.id} className="px-4 py-3 text-[14px]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="min-w-0">
                <span className="font-semibold text-ink">{t.title}</span>
                <span className="text-ink-soft"> · {t.questions} questions · {t.taken} of {t.members} done{t.average != null ? ` · avg ${t.average}` : ''} · {t.open ? (t.due_date ? `due ${day(t.due_date)}` : 'open') : 'closed'}</span>
              </span>
              <span className="flex gap-2">
                <button className={`${btn} border-rule text-ink`} aria-expanded={open === t.id} onClick={() => setOpen(open === t.id ? '' : t.id)}>Results</button>
                {canEdit && t.open && <button className={`${btn} border-rule text-ink-soft`} onClick={() => close(t.id)}>Close</button>}
              </span>
            </div>
            {open === t.id && <Results cid={cid} test={t} />}
          </li>
        ))}
        {!data?.tests?.length && <li className="px-4 py-3 text-[14px] text-ink-soft">No tests set yet.</li>}
      </ul>
    </section>
  );
}
