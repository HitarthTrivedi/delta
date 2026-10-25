import React, { useState } from 'react';
import { ThumbsUp, TrendingUp, Volume2, ChevronDown, ChevronUp, MessageSquare } from 'lucide-react';
import { preferredVoice } from '../../hooks/useInterviewerVoice';

const panel = { background: 'var(--paper)', border: '1px solid rgb(var(--ink-rgb) / 0.1)', borderRadius: 8 };
const muted = 'rgb(var(--ink-rgb) / 0.55)';

const VERDICT = {
  strong: { label: 'Strong performance', color: '#15803d' },
  ready: { label: 'Interview-ready', color: '#1d4ed8' },
  almost: { label: 'Almost there', color: '#b45309' },
  not_yet: { label: 'Building up', color: 'var(--ink-soft)' },
};
const RUBRIC_LABELS = { communication: 'Communication', technical_depth: 'Subject knowledge', problem_solving: 'Problem solving', clarity: 'Clarity' };
const DIFFICULTY = { entry: 'Entry level', intermediate: 'Intermediate', advanced: 'Advanced' };

function speakOnce(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const voice = preferredVoice(); // same voice the user chose for the interviewer
  if (voice) { u.voice = voice; u.lang = voice.lang; }
  window.speechSynthesis.speak(u);
}

/** Pair each interviewer question with the candidate's next answer. */
function pairTranscript(transcript) {
  const pairs = [];
  (transcript || []).forEach((t) => {
    if (t.role === 'interviewer') pairs.push({ question: t.content, answer: null });
    else if (pairs.length) pairs[pairs.length - 1].answer = t.content;
  });
  return pairs;
}

export default function InterviewReport({ feedback, transcript, settings }) {
  const [showTranscript, setShowTranscript] = useState(false);
  if (!feedback) return null;

  const verdict = VERDICT[feedback.verdict] || null;
  // Older reports used per_question_feedback and had no rubric.
  const perQuestion = feedback.per_question || (feedback.per_question_feedback || []).map((q) => ({ ...q, score: null }));
  const pairs = pairTranscript(transcript);
  const answerFor = (question) => pairs.find((p) => p.question === question)?.answer;
  const score = feedback.overall_score ?? 0;

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <section style={{ ...panel, padding: 24, display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', width: 116, height: 116, flexShrink: 0 }}>
          <svg viewBox="0 0 36 36" width="116" height="116" aria-hidden="true">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgb(var(--ink-rgb) / 0.1)" strokeWidth="3" />
            <circle cx="18" cy="18" r="15.9" fill="none" stroke={verdict?.color || '#be185d'} strokeWidth="3"
              strokeDasharray={`${score} ${100 - score}`} strokeDashoffset="25" strokeLinecap="round" />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: 32, fontWeight: 800, lineHeight: 1 }}>{score}</span>
            <span style={{ fontSize: 11, color: muted }}>out of 100</span>
          </div>
        </div>
        <div style={{ flex: 1, minWidth: 220 }}>
          {verdict && (
            <span style={{ display: 'inline-block', fontSize: 12, fontWeight: 700, color: verdict.color, border: `1px solid ${verdict.color}66`, borderRadius: 999, padding: '3px 10px', marginBottom: 10 }}>
              {verdict.label}
            </span>
          )}
          {settings && (
            <p style={{ margin: '0 0 8px', color: muted, fontSize: 12.5 }}>
              {settings.target_role} · {DIFFICULTY[settings.difficulty] || settings.difficulty} · {settings.num_questions} questions
            </p>
          )}
          {feedback.summary && <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: 'rgb(var(--ink-rgb) / 0.85)' }}>{feedback.summary}</p>}
        </div>
      </section>

      {feedback.rubric && (
        <section style={{ ...panel, padding: 20 }}>
          <h2 style={{ margin: '0 0 14px', fontSize: 14, color: muted }}>Skill areas</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            {Object.entries(RUBRIC_LABELS).map(([key, label]) => {
              const item = feedback.rubric[key];
              if (!item) return null;
              return (
                <div key={key}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13.5, marginBottom: 6 }}>
                    <span style={{ fontWeight: 600 }}>{label}</span>
                    <span style={{ color: muted }}>{item.score}/10</span>
                  </div>
                  <div style={{ height: 6, borderRadius: 3, background: 'rgb(var(--ink-rgb) / 0.08)' }}>
                    <div style={{ width: `${item.score * 10}%`, height: '100%', borderRadius: 3, background: item.score >= 7 ? '#15803d' : item.score >= 5 ? '#b45309' : '#b45309' }} />
                  </div>
                  {item.comment && <p style={{ margin: '6px 0 0', fontSize: 12.5, color: muted, lineHeight: 1.5 }}>{item.comment}</p>}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
        {feedback.strengths?.length > 0 && (
          <section style={{ ...panel, padding: 20 }}>
            <h2 style={{ margin: '0 0 12px', fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 7, color: '#15803d' }}><ThumbsUp size={14} /> What went well</h2>
            <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 6 }}>
              {feedback.strengths.map((s, i) => <li key={i} style={{ color: 'rgb(var(--ink-rgb) / 0.78)', fontSize: 13.5, lineHeight: 1.5 }}>{s}</li>)}
            </ul>
          </section>
        )}
        {feedback.improvements?.length > 0 && (
          <section style={{ ...panel, padding: 20 }}>
            <h2 style={{ margin: '0 0 12px', fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 7, color: '#b45309' }}><TrendingUp size={14} /> To improve</h2>
            <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 6 }}>
              {feedback.improvements.map((s, i) => <li key={i} style={{ color: 'rgb(var(--ink-rgb) / 0.78)', fontSize: 13.5, lineHeight: 1.5 }}>{s}</li>)}
            </ul>
          </section>
        )}
      </div>

      {perQuestion.length > 0 && (
        <section style={{ ...panel, padding: 20 }}>
          <h2 style={{ margin: '0 0 14px', fontSize: 14, color: muted }}>Question by question</h2>
          <div style={{ display: 'grid', gap: 12 }}>
            {perQuestion.map((q, i) => <QuestionCard key={i} index={i} q={q} answer={answerFor(q.question) || q.answer_excerpt} />)}
          </div>
        </section>
      )}

      {pairs.length > 0 && (
        <section style={{ ...panel, padding: 20 }}>
          <button
            onClick={() => setShowTranscript((v) => !v)}
            style={{ background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, fontWeight: 600 }}
          >
            <MessageSquare size={15} /> Full transcript {showTranscript ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
          {showTranscript && (
            <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
              {(transcript || []).map((t, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', justifyContent: t.role === 'interviewer' ? 'flex-start' : 'flex-end' }}>
                  <div style={{
                    maxWidth: '80%', padding: '10px 14px', borderRadius: 10, fontSize: 13.5, lineHeight: 1.55,
                    background: t.role === 'interviewer' ? 'rgba(190,24,93,0.1)' : 'rgb(var(--ink-rgb) / 0.07)',
                    border: `1px solid ${t.role === 'interviewer' ? 'rgba(190,24,93,0.25)' : 'rgb(var(--ink-rgb) / 0.1)'}`,
                  }}>
                    <span style={{ display: 'block', fontSize: 11, color: muted, marginBottom: 3 }}>{t.role === 'interviewer' ? 'Aria' : 'You'}</span>
                    {t.content}
                  </div>
                  {t.role === 'interviewer' && (
                    <button onClick={() => speakOnce(t.content)} aria-label="Play this question" title="Play"
                      style={{ background: 'none', border: '1px solid rgb(var(--ink-rgb) / 0.15)', borderRadius: 6, padding: 6, color: muted, cursor: 'pointer', display: 'flex' }}>
                      <Volume2 size={13} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function QuestionCard({ index, q, answer }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ border: '1px solid rgb(var(--ink-rgb) / 0.08)', borderRadius: 8, padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <p style={{ margin: 0, fontSize: 14, fontWeight: 600, lineHeight: 1.5 }}>{index + 1}. {q.question}</p>
        {q.score != null && (
          <span style={{ flexShrink: 0, fontSize: 13, fontWeight: 700, color: q.score >= 7 ? '#15803d' : q.score >= 5 ? '#b45309' : '#b45309' }}>{q.score}/10</span>
        )}
      </div>
      {answer && <p style={{ margin: '8px 0 0', fontSize: 13, color: 'rgb(var(--ink-rgb) / 0.6)', lineHeight: 1.5, fontStyle: 'italic' }}>“{answer}”</p>}
      {q.feedback && <p style={{ margin: '8px 0 0', fontSize: 13.5, color: 'rgb(var(--ink-rgb) / 0.82)', lineHeight: 1.55 }}>{q.feedback}</p>}
      {q.model_answer && (
        <>
          <button onClick={() => setOpen((v) => !v)} style={{ marginTop: 10, background: 'none', border: 'none', padding: 0, color: '#be185d', cursor: 'pointer', fontSize: 12.5, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            {open ? 'Hide' : 'See'} a strong answer {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          {open && <p style={{ margin: '8px 0 0', padding: 12, borderRadius: 6, background: 'rgba(190,24,93,0.07)', fontSize: 13, color: 'rgb(var(--ink-rgb) / 0.8)', lineHeight: 1.6 }}>{q.model_answer}</p>}
        </>
      )}
    </div>
  );
}
