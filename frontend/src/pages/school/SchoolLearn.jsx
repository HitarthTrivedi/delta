import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2, ArrowLeft, Lock, BookOpen, Check, X, ExternalLink, Star } from 'lucide-react';
import { toast } from 'sonner';
import { schoolAPI } from '../../lib/api';
import { exitChildMode } from '../../lib/childMode';
import { useAuthStore } from '../../store/authStore';

const btn = 'inline-flex items-center justify-center gap-2 px-5 py-3 border font-mono text-xs uppercase tracking-[0.12em] transition-colors';
const btnPrimary = 'bg-oxblood text-bone border-oxblood cursor-pointer hover:bg-ink hover:border-ink';
const btnOff = 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed';

const md = {
  h2: ({ children }) => <h2 className="font-display text-[26px] font-semibold text-oxblood mt-8 mb-3">{children}</h2>,
  h3: ({ children }) => <h3 className="text-[18px] font-semibold text-ink mt-6 mb-2">{children}</h3>,
  p: ({ children }) => <p className="text-[17px] leading-[1.8] text-ink m-0 mb-4">{children}</p>,
  ul: ({ children }) => <ul className="text-[17px] leading-[1.8] text-ink pl-6 m-0 mb-4">{children}</ul>,
  ol: ({ children }) => <ol className="text-[17px] leading-[1.8] text-ink pl-6 m-0 mb-4">{children}</ol>,
  strong: ({ children }) => <strong className="text-oxblood">{children}</strong>,
  code: ({ children }) => <code className="bg-accent-surface px-1.5 py-0.5 text-[15px]">{children}</code>,
  table: ({ children }) => <div className="overflow-x-auto mb-4"><table className="border-collapse text-[15px]">{children}</table></div>,
  th: ({ children }) => <th className="border border-rule px-3 py-1.5 bg-accent-surface text-left">{children}</th>,
  td: ({ children }) => <td className="border border-rule px-3 py-1.5">{children}</td>,
  a: ({ children }) => <span>{children}</span>, // no outbound links inside lessons
};

/** Child mode: the child's own learning screen. Leaving it needs the parent's PIN. */
export default function SchoolLearn() {
  const { childId } = useParams();
  const userId = useAuthStore((s) => s.userId);
  const navigate = useNavigate();
  const [home, setHome] = useState(null);
  const [open, setOpen] = useState(null); // { subject, chapter_no }
  const [pinOpen, setPinOpen] = useState(false);

  const loadHome = useCallback(() => {
    schoolAPI.childHome(userId, childId).then(setHome).catch(() => {
      // Profile gone (deleted elsewhere): release the lock.
      exitChildMode();
      navigate('/school', { replace: true });
    });
  }, [userId, childId, navigate]);
  useEffect(loadHome, [loadHome]);
  // Stable, so the open lesson doesn't refetch (and reset answers) on re-render.
  const closeLesson = useCallback(() => { setOpen(null); loadHome(); }, [loadHome]);

  if (!home) {
    return <div className="min-h-screen bg-bone flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div>;
  }

  return (
    <div className="min-h-screen bg-bone text-ink">
      <header className="border-b border-rule bg-paper">
        <div className="max-w-[900px] mx-auto px-4 h-16 flex items-center justify-between gap-3">
          <div>
            <p className="m-0 font-display text-[22px] font-semibold text-oxblood leading-none">Hi {home.first_name}!</p>
            <p className="m-0 text-[12px] text-ink-soft mt-1">Class {home.grade} · Delta for School</p>
          </div>
          <button onClick={() => setPinOpen(true)} className="inline-flex items-center gap-1.5 px-3 py-2 border border-rule text-ink-soft bg-transparent text-[12px] cursor-pointer hover:text-oxblood hover:border-oxblood">
            <Lock size={13} /> Grown-ups
          </button>
        </div>
      </header>

      <main className="max-w-[900px] mx-auto px-4 py-8">
        {open ? (
          <Lesson
            childId={childId}
            subject={open.subject}
            chapterNo={open.chapter_no}
            onBack={closeLesson}
          />
        ) : (
          <div className="grid gap-8">
            {home.subjects.map((s) => (
              <section key={s.subject}>
                <h2 className="font-display text-[28px] font-semibold text-ink m-0 mb-1">{s.label}</h2>
                <p className="text-[13px] text-ink-soft m-0 mb-4">NCERT · {s.textbook}</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  {s.chapters.map((ch) => (
                    <button
                      key={ch.chapter_no}
                      disabled={!ch.available}
                      onClick={() => setOpen({ subject: s.subject, chapter_no: ch.chapter_no })}
                      className={`text-left p-4 border flex items-start gap-3 ${ch.available ? 'bg-paper border-rule cursor-pointer hover:border-oxblood' : 'bg-transparent border-rule border-dashed cursor-not-allowed'}`}
                    >
                      <span className={`font-display text-[22px] leading-none w-7 shrink-0 ${ch.available ? 'text-oxblood' : 'text-ink-soft'}`}>{ch.chapter_no}</span>
                      <span className="flex-1 min-w-0">
                        <span className={`block text-[15px] font-semibold ${ch.available ? 'text-ink' : 'text-ink-soft'}`}>{ch.title}</span>
                        <span className="block text-[12px] text-ink-soft mt-1">
                          {!ch.available ? 'Coming soon' : ch.best_score != null ? `Best score ${ch.best_score}%` : 'Not started'}
                        </span>
                      </span>
                      {ch.best_score === 100 && <Star size={16} className="text-oxblood shrink-0" aria-label="Perfect score" />}
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </main>

      {pinOpen && <PinDialog childId={childId} onClose={() => setPinOpen(false)} />}
    </div>
  );
}

function Lesson({ childId, subject, chapterNo, onBack }) {
  const userId = useAuthStore((s) => s.userId);
  const [lesson, setLesson] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    schoolAPI.lesson(userId, childId, subject, chapterNo)
      .then((l) => { setLesson(l); setAnswers(new Array(l.quiz.length).fill(null)); })
      .catch(() => { toast.error("This chapter isn't ready yet."); onBack(); });
  }, [userId, childId, subject, chapterNo, onBack]);

  const submit = async () => {
    setSubmitting(true);
    try {
      setResult(await schoolAPI.submitQuiz(userId, childId, subject, chapterNo, answers));
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    } catch {
      toast.error('Could not check your answers. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!lesson) return <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div>;
  const allAnswered = answers.every((a) => a !== null);

  return (
    <article>
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-[14px] text-ink-soft bg-transparent border-0 p-0 cursor-pointer hover:text-oxblood mb-6">
        <ArrowLeft size={15} /> All chapters
      </button>
      <p className="kicker mb-2">{lesson.subject_label} · Chapter {lesson.chapter_no}</p>
      <h1 className="font-display text-[clamp(2rem,5vw,2.8rem)] font-semibold text-ink leading-tight m-0 mb-2">{lesson.chapter_title}</h1>
      <a href={lesson.textbook_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[13px] text-oxblood no-underline hover:underline mb-6">
        Read it in your NCERT book: {lesson.textbook} <ExternalLink size={12} />
      </a>

      <div className="bg-paper border border-rule p-5 sm:p-8 mb-8">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{lesson.content}</ReactMarkdown>
      </div>

      <section>
        <h2 className="font-display text-[28px] font-semibold text-oxblood m-0 mb-1 flex items-center gap-2"><BookOpen size={20} /> Check what you learned</h2>
        <p className="text-[14px] text-ink-soft m-0 mb-5">{lesson.quiz.length} questions. Take your time. You can try again as many times as you like.</p>
        <ol className="m-0 p-0 list-none grid gap-5">
          {lesson.quiz.map((q, i) => {
            const r = result?.questions?.[i];
            return (
              <li key={i} className="bg-paper border border-rule p-5">
                <p className="m-0 mb-3 text-[16px] font-semibold text-ink">{i + 1}. {q.question}</p>
                <div className="grid gap-2" role="radiogroup" aria-label={`Question ${i + 1}`}>
                  {q.options.map((opt, j) => {
                    const chosen = answers[i] === j;
                    const isRight = r && r.answer_index === j;
                    const isWrongPick = r && chosen && !r.correct;
                    return (
                      <label key={j} className={`flex items-center gap-3 p-3 border text-[15px] ${result ? 'cursor-default' : 'cursor-pointer'} ${isRight ? 'border-oxblood bg-accent-surface' : isWrongPick ? 'border-ink' : chosen ? 'border-oxblood' : 'border-rule'}`}>
                        <input
                          type="radio"
                          name={`q${i}`}
                          checked={chosen}
                          disabled={!!result}
                          onChange={() => setAnswers((a) => a.map((v, k) => (k === i ? j : v)))}
                          className="w-4 h-4 accent-[var(--oxblood)]"
                        />
                        <span className="flex-1">{opt}</span>
                        {isRight && <Check size={16} className="text-oxblood" aria-label="Correct answer" />}
                        {isWrongPick && <X size={16} className="text-ink" aria-label="Your answer" />}
                      </label>
                    );
                  })}
                </div>
                {r?.explanation && <p className="m-0 mt-3 text-[14px] text-ink-soft">{r.explanation}</p>}
              </li>
            );
          })}
        </ol>

        {result ? (
          <div className="mt-6 bg-paper border border-oxblood p-6 text-center">
            <p className="m-0 font-display text-[44px] font-semibold text-oxblood leading-none">{result.score}%</p>
            <p className="m-0 mt-2 text-[15px] text-ink">
              {result.correct} of {result.total} right.{' '}
              {result.score === 100 ? 'Perfect!' : result.score >= 60 ? 'Well done!' : 'Read the lesson again and have another go.'}
            </p>
            <div className="flex gap-3 justify-center mt-5 flex-wrap">
              <button onClick={() => { setResult(null); setAnswers(new Array(lesson.quiz.length).fill(null)); }} className={`${btn} border-ink text-ink bg-transparent cursor-pointer`}>Try again</button>
              <button onClick={onBack} className={`${btn} ${btnPrimary}`}>Next chapter</button>
            </div>
          </div>
        ) : (
          <button onClick={submit} disabled={!allAnswered || submitting} className={`${btn} mt-6 w-full ${allAnswered && !submitting ? btnPrimary : btnOff}`}>
            {submitting && <Loader2 size={15} className="animate-spin" />} Check my answers
          </button>
        )}
      </section>
    </article>
  );
}

function PinDialog({ childId, onClose }) {
  const userId = useAuthStore((s) => s.userId);
  const navigate = useNavigate();
  const [pin, setPin] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await schoolAPI.verifyPin(userId, childId, pin);
      exitChildMode();
      navigate('/school', { replace: true });
    } catch (err) {
      toast.error(err?.response?.status === 429 ? 'Too many tries. Wait a minute.' : 'That PIN is not right.');
      setPin('');
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" role="dialog" aria-modal="true" aria-label="Enter parent PIN">
      <div className="absolute inset-0 bg-ink/50" onClick={onClose} />
      <form onSubmit={submit} className="relative bg-bone border border-rule p-6 w-full max-w-[340px]">
        <h2 className="m-0 font-display text-[22px] font-semibold text-ink mb-1">Grown-ups only</h2>
        <p className="m-0 text-[13px] text-ink-soft mb-4">Enter the parent PIN to leave.</p>
        <input
          autoFocus
          type="password"
          inputMode="numeric"
          maxLength={6}
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
          aria-label="Parent PIN"
          className="w-full bg-paper border border-rule px-3.5 py-3 text-ink text-[20px] tracking-[0.4em] text-center outline-none focus:border-oxblood box-border mb-4"
        />
        <div className="flex gap-2">
          <button type="button" onClick={onClose} className="flex-1 py-2.5 border border-rule bg-transparent text-ink-soft cursor-pointer text-[13px]">Cancel</button>
          <button type="submit" disabled={pin.length < 4 || busy} className={`flex-1 py-2.5 border text-[13px] ${pin.length >= 4 && !busy ? 'bg-oxblood text-bone border-oxblood cursor-pointer' : 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'}`}>
            {busy ? <Loader2 size={14} className="animate-spin inline" /> : 'Unlock'}
          </button>
        </div>
      </form>
    </div>
  );
}
