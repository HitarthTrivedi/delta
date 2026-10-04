import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2, ArrowLeft, Sparkles, Save, Check, X, Plus, Trash2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { schoolAPI } from '../../lib/api';

const GRADES = [6, 7, 8, 9, 10];
const SUBJECTS = [{ key: 'maths', label: 'Mathematics' }, { key: 'science', label: 'Science' }];
const STATUS_STYLE = {
  approved: 'text-oxblood border-oxblood',
  draft: 'text-ink border-ink',
  rejected: 'text-ink-soft border-rule line-through',
  missing: 'text-ink-soft border-rule border-dashed',
};
const btn = 'inline-flex items-center justify-center gap-2 px-4 py-2.5 border font-mono text-[11px] uppercase tracking-[0.12em] transition-colors';
const inputClass = 'w-full bg-paper border border-rule px-3 py-2 text-ink text-sm outline-none focus:border-oxblood box-border';

/** Reviewers (CONTENT_REVIEWER_EMAILS / ADMIN_EMAILS): draft, edit and approve School lessons. */
export default function SchoolReview() {
  const [allowed, setAllowed] = useState(null);
  const [grade, setGrade] = useState(6);
  const [subject, setSubject] = useState('maths');
  const [book, setBook] = useState(null);
  const [selected, setSelected] = useState(null); // chapter_no

  useEffect(() => { schoolAPI.reviewerMe().then((r) => setAllowed(r.is_reviewer)).catch(() => setAllowed(false)); }, []);

  const loadBook = () => {
    setBook(null);
    schoolAPI.reviewChapters(grade, subject).then(setBook).catch(() => toast.error('Could not load chapters.'));
  };
  useEffect(() => { if (allowed) { setSelected(null); loadBook(); } }, [allowed, grade, subject]); // eslint-disable-line

  if (allowed === null) return <div className="min-h-screen bg-bone flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div>;
  if (!allowed) {
    return (
      <main className="min-h-screen bg-bone text-ink px-4 pt-24">
        <p className="max-w-[600px] mx-auto text-ink-soft">Only content reviewers can open this page. Reviewers are set with CONTENT_REVIEWER_EMAILS or ADMIN_EMAILS on the server.</p>
      </main>
    );
  }

  const chapter = book?.chapters.find((c) => c.chapter_no === selected);

  return (
    <main className="min-h-screen bg-bone text-ink px-4 pt-24 pb-16">
      <div className="max-w-[1180px] mx-auto">
        <Link to="/school" className="inline-flex items-center gap-1.5 text-[13px] text-ink-soft no-underline hover:text-oxblood mb-5"><ArrowLeft size={14} /> Delta for School</Link>
        <h1 className="font-display text-[clamp(2rem,5vw,2.6rem)] font-semibold text-oxblood m-0 mb-2">Lesson review</h1>
        <p className="text-ink-soft text-[14px] leading-relaxed m-0 mb-6 max-w-[760px]">
          Children only see <strong>approved</strong> lessons. Check each AI draft against the NCERT textbook for accuracy, age-appropriateness
          and syllabus scope, fix what's wrong, then approve. Any edit sends a lesson back to draft.
        </p>

        <div className="flex gap-3 flex-wrap mb-5">
          <select value={grade} onChange={(e) => setGrade(Number(e.target.value))} className={`${inputClass} w-auto`} aria-label="Class">
            {GRADES.map((g) => <option key={g} value={g}>Class {g}</option>)}
          </select>
          <select value={subject} onChange={(e) => setSubject(e.target.value)} className={`${inputClass} w-auto`} aria-label="Subject">
            {SUBJECTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>

        {book?.verify_chapter_list && (
          <p className="flex items-start gap-2 text-[13px] text-ink bg-accent-surface border border-rule p-3 mb-5 max-w-[760px]">
            <AlertTriangle size={15} className="text-oxblood shrink-0 mt-0.5" />
            This class uses the new NCERT book ({book.textbook}). Check the chapter titles below against the printed book before approving lessons.
            Fix any differences in <code>backend/app/services/school_curriculum.py</code>.
          </p>
        )}

        {!book ? <Loader2 className="w-6 h-6 animate-spin text-ink-soft" /> : (
          <div className="grid lg:grid-cols-[300px_1fr] gap-6 items-start">
            <ul className="m-0 p-0 list-none grid gap-1.5">
              {book.chapters.map((c) => (
                <li key={c.chapter_no}>
                  <button
                    onClick={() => setSelected(c.chapter_no)}
                    className={`w-full text-left p-3 border bg-paper cursor-pointer flex justify-between gap-2 ${selected === c.chapter_no ? 'border-oxblood' : 'border-rule hover:border-ink-soft'}`}
                  >
                    <span className="text-[13.5px] text-ink">{c.chapter_no}. {c.title}</span>
                    <span className={`font-mono text-[10px] uppercase tracking-[0.1em] px-1.5 py-0.5 border h-fit shrink-0 ${STATUS_STYLE[c.status]}`}>{c.status}</span>
                  </button>
                </li>
              ))}
            </ul>
            <div>
              {chapter ? (
                <Editor key={`${grade}-${subject}-${chapter.chapter_no}`} grade={grade} subject={subject} chapter={chapter} onChanged={loadBook} />
              ) : (
                <p className="text-ink-soft text-[14px]">Pick a chapter.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

function Editor({ grade, subject, chapter, onChanged }) {
  const [lesson, setLesson] = useState(null);
  const [content, setContent] = useState('');
  const [quiz, setQuiz] = useState([]);
  const [preview, setPreview] = useState(false);
  const [busy, setBusy] = useState('');
  const [dirty, setDirty] = useState(false);

  const apply = (l) => { setLesson(l); setContent(l.content || ''); setQuiz(l.quiz || []); setDirty(false); };

  useEffect(() => {
    if (chapter.lesson_id) schoolAPI.reviewGet(chapter.lesson_id).then(apply).catch(() => toast.error('Could not load lesson.'));
  }, [chapter.lesson_id]);

  const run = async (name, fn, okMsg) => {
    setBusy(name);
    try {
      const l = await fn();
      apply(l);
      onChanged();
      if (okMsg) toast.success(okMsg);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Something went wrong.');
    } finally {
      setBusy('');
    }
  };

  const generate = () => run('gen', () => schoolAPI.reviewGenerate(grade, subject, chapter.chapter_no), 'Draft generated. Review it carefully.');
  const save = () => run('save', () => schoolAPI.reviewSave(lesson.id, content, quiz), 'Saved as draft.');
  const approve = () => run('approve', () => schoolAPI.reviewApprove(lesson.id), 'Approved. Children can now see this lesson.');
  const reject = () => run('reject', () => schoolAPI.reviewReject(lesson.id), 'Rejected.');

  const editQ = (i, patch) => { setQuiz((qs) => qs.map((q, k) => (k === i ? { ...q, ...patch } : q))); setDirty(true); };

  if (!chapter.lesson_id && !lesson) {
    return (
      <div className="bg-paper border border-rule p-6">
        <h2 className="m-0 font-display text-[22px] text-ink mb-2">{chapter.chapter_no}. {chapter.title}</h2>
        <p className="text-ink-soft text-[14px] m-0 mb-4">No lesson yet. Generate an AI draft, then review and edit it before approving.</p>
        <button onClick={generate} disabled={busy === 'gen'} className={`${btn} bg-oxblood text-bone border-oxblood cursor-pointer`}>
          {busy === 'gen' ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} {busy === 'gen' ? 'Writing draft…' : 'Generate draft'}
        </button>
      </div>
    );
  }
  if (!lesson) return <Loader2 className="w-6 h-6 animate-spin text-ink-soft" />;

  return (
    <div className="bg-paper border border-rule p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
        <div>
          <h2 className="m-0 font-display text-[22px] text-ink">{chapter.chapter_no}. {lesson.chapter_title}</h2>
          <p className="m-0 text-[12px] text-ink-soft mt-1">
            Status: <strong className="text-ink">{lesson.status}</strong>
            {lesson.reviewed_by && ` · by ${lesson.reviewed_by}`}{dirty && ' · unsaved changes'}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {lesson.status !== 'approved' && (
            <button onClick={generate} disabled={!!busy} className={`${btn} bg-transparent text-ink border-rule cursor-pointer`}>
              {busy === 'gen' ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} Regenerate
            </button>
          )}
          <button onClick={save} disabled={!dirty || !!busy} className={`${btn} ${dirty ? 'bg-transparent text-ink border-ink cursor-pointer' : 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'}`}>
            {busy === 'save' ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Save
          </button>
          <button onClick={reject} disabled={!!busy || lesson.status === 'rejected'} className={`${btn} bg-transparent text-ink border-ink cursor-pointer`}>
            <X size={13} /> Reject
          </button>
          <button onClick={approve} disabled={dirty || !!busy || lesson.status === 'approved'} className={`${btn} ${!dirty && lesson.status !== 'approved' ? 'bg-oxblood text-bone border-oxblood cursor-pointer' : 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'}`}>
            {busy === 'approve' ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Approve
          </button>
        </div>
      </div>

      <div className="flex gap-4 border-b border-rule mb-3">
        {['Edit', 'Preview'].map((t) => (
          <button key={t} onClick={() => setPreview(t === 'Preview')} className={`pb-2 bg-transparent border-0 border-b-2 cursor-pointer font-mono text-[11px] uppercase tracking-[0.12em] ${preview === (t === 'Preview') ? 'text-oxblood border-oxblood' : 'text-ink-soft border-transparent'}`}>{t}</button>
        ))}
      </div>
      {preview ? (
        <div className="prose-sm max-w-none text-ink text-[15px] leading-relaxed [&_h2]:font-display [&_h2]:text-[22px] [&_h2]:text-oxblood [&_h2]:mt-5 [&_ul]:pl-5">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      ) : (
        <textarea
          value={content}
          onChange={(e) => { setContent(e.target.value); setDirty(true); }}
          rows={22}
          aria-label="Lesson markdown"
          className={`${inputClass} font-mono text-[13px] leading-relaxed resize-y`}
        />
      )}

      <h3 className="font-display text-[20px] text-ink mt-7 mb-3">Quiz</h3>
      <div className="grid gap-4">
        {quiz.map((q, i) => (
          <div key={i} className="border border-rule p-4">
            <div className="flex gap-2 mb-2">
              <input value={q.question} onChange={(e) => editQ(i, { question: e.target.value })} className={inputClass} aria-label={`Question ${i + 1}`} />
              <button onClick={() => { setQuiz((qs) => qs.filter((_, k) => k !== i)); setDirty(true); }} aria-label="Remove question" className="px-2 border border-rule bg-transparent text-ink-soft cursor-pointer hover:text-oxblood"><Trash2 size={14} /></button>
            </div>
            <div className="grid sm:grid-cols-2 gap-2">
              {q.options.map((opt, j) => (
                <label key={j} className="flex items-center gap-2">
                  <input type="radio" name={`ans-${i}`} checked={q.answer_index === j} onChange={() => editQ(i, { answer_index: j })} className="accent-[var(--oxblood)]" aria-label={`Option ${j + 1} is correct`} />
                  <input value={opt} onChange={(e) => editQ(i, { options: q.options.map((o, k) => (k === j ? e.target.value : o)) })} className={inputClass} aria-label={`Option ${j + 1}`} />
                </label>
              ))}
            </div>
            <input value={q.explanation || ''} onChange={(e) => editQ(i, { explanation: e.target.value })} placeholder="Explanation shown after answering" className={`${inputClass} mt-2`} aria-label="Explanation" />
          </div>
        ))}
      </div>
      <button
        onClick={() => { setQuiz((qs) => [...qs, { question: '', options: ['', '', '', ''], answer_index: 0, explanation: '' }]); setDirty(true); }}
        className={`${btn} mt-3 bg-transparent text-ink border-rule cursor-pointer`}
      >
        <Plus size={13} /> Add question
      </button>
    </div>
  );
}
