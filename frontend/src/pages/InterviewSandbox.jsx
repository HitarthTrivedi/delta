import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Mic, MicOff, Volume2, VolumeX, Send, Loader2, Briefcase,
  ThumbsUp, ThumbsDown, ArrowRight, RotateCcw,
} from 'lucide-react';
import { toast } from 'sonner';
import { sandboxInterviewAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: '#050505',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
};

const ROLE_TYPES = [
  { key: 'technical', label: 'Technical', desc: 'Coding & CS fundamentals' },
  { key: 'behavioral', label: 'Behavioral', desc: 'Past experience, teamwork, conflict' },
  { key: 'system_design', label: 'System Design', desc: 'Architecture & trade-offs' },
];

const SpeechRecognitionAPI =
  typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null;
const SUPPORTS_RECOGNITION = !!SpeechRecognitionAPI;
const SUPPORTS_SYNTHESIS = typeof window !== 'undefined' && 'speechSynthesis' in window;

export default function InterviewSandbox() {
  const userId = useAuthStore((state) => state.userId);

  const [stage, setStage] = useState('setup'); // setup | interview | feedback
  const [roleType, setRoleType] = useState('technical');
  const [starting, setStarting] = useState(false);

  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState('');
  const [questionNumber, setQuestionNumber] = useState(1);
  const [transcriptLog, setTranscriptLog] = useState([]); // [{question, answer}]
  const [answer, setAnswer] = useState('');
  const [sending, setSending] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const [muted, setMuted] = useState(false);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  // Speak the current question aloud whenever it changes (unless muted).
  useEffect(() => {
    if (stage !== 'interview' || !question || muted || !SUPPORTS_SYNTHESIS) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(question);
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
    return () => window.speechSynthesis.cancel();
  }, [question, stage, muted]);

  // Clean up recognition + speech on unmount.
  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      if (SUPPORTS_SYNTHESIS) window.speechSynthesis.cancel();
    };
  }, []);

  const startInterview = async () => {
    setStarting(true);
    try {
      const data = await sandboxInterviewAPI.start(userId, roleType);
      setSessionId(data.session_id);
      setQuestion(data.question);
      setQuestionNumber(data.question_number || 1);
      setTranscriptLog([]);
      setAnswer('');
      setStage('interview');
    } catch (err) {
      console.error(err);
      toast.error('Could not start the interview. Try again.');
    } finally {
      setStarting(false);
    }
  };

  const toggleListening = () => {
    if (!SUPPORTS_RECOGNITION) return;
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    let finalText = '';
    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const chunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += chunk + ' ';
        else interim += chunk;
      }
      setAnswer((finalText + interim).trim());
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  };

  const submitAnswer = async () => {
    const text = answer.trim();
    if (!text || sending) return;
    recognitionRef.current?.stop();
    setSending(true);
    try {
      const data = await sandboxInterviewAPI.respond(userId, sessionId, text);
      setTranscriptLog((prev) => [...prev, { question, answer: text }]);
      setAnswer('');
      if (data.done || !data.question) {
        await doFinish();
      } else {
        setQuestion(data.question);
        setQuestionNumber(data.question_number);
      }
    } catch (err) {
      console.error(err);
      toast.error('Could not send your answer. Try again.');
    } finally {
      setSending(false);
    }
  };

  const doFinish = useCallback(async () => {
    setFinishing(true);
    try {
      const data = await sandboxInterviewAPI.finish(userId, sessionId);
      setFeedback(data.feedback);
      setStage('feedback');
    } catch (err) {
      console.error(err);
      toast.error('Could not generate your feedback report. Try again.');
    } finally {
      setFinishing(false);
    }
  }, [userId, sessionId]);

  const startOver = () => {
    setStage('setup');
    setSessionId(null);
    setQuestion('');
    setFeedback(null);
    setTranscriptLog([]);
    setAnswer('');
  };

  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>

        {stage === 'setup' && (
          <>
            <header style={{ marginBottom: 28 }}>
              <p style={{ color: 'rgba(255,255,255,0.46)', fontSize: 13, fontWeight: 650, margin: '0 0 10px', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <Briefcase size={15} style={{ color: '#f472b6' }} /> Mock Interview
              </p>
              <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.2rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0 }}>
                Rehearse it before it counts.
              </h1>
              <p style={{ margin: '14px 0 0', color: 'rgba(255,255,255,0.5)', fontSize: 15, lineHeight: 1.55 }}>
                An AI interviewer asks questions tailored to your profile. Answer by speaking or typing, then get a structured feedback report.
              </p>
            </header>

            <section style={{ ...panelStyle, padding: 22 }}>
              <h2 style={{ margin: '0 0 14px', fontSize: 16 }}>Choose interview type</h2>
              <div style={{ display: 'grid', gap: 10, marginBottom: 20 }}>
                {ROLE_TYPES.map((rt) => (
                  <button
                    key={rt.key}
                    onClick={() => setRoleType(rt.key)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                      background: roleType === rt.key ? 'rgba(255,255,255,0.1)' : '#0a0a0a',
                      border: `1px solid ${roleType === rt.key ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.1)'}`,
                      borderRadius: 8, padding: '14px 16px', color: '#fff', textAlign: 'left', cursor: 'pointer',
                    }}
                  >
                    <span>
                      <span style={{ display: 'block', fontSize: 15, fontWeight: 700 }}>{rt.label}</span>
                      <span style={{ display: 'block', color: 'rgba(255,255,255,0.45)', fontSize: 13, marginTop: 2 }}>{rt.desc}</span>
                    </span>
                    {roleType === rt.key && <ArrowRight size={16} />}
                  </button>
                ))}
              </div>

              {!SUPPORTS_RECOGNITION && (
                <p style={{ margin: '0 0 16px', color: 'rgba(255,255,255,0.4)', fontSize: 12, lineHeight: 1.5 }}>
                  Voice input isn't supported in this browser — you can still type your answers. (Chrome or Edge enable the mic.)
                </p>
              )}

              <button
                onClick={startInterview}
                disabled={starting}
                style={{
                  width: '100%', background: '#fff', color: '#000', border: 'none', borderRadius: 8,
                  padding: 14, fontWeight: 700, fontSize: 15, cursor: starting ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >
                {starting ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <ArrowRight size={16} />}
                Start interview
              </button>
            </section>
          </>
        )}

        {stage === 'interview' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, fontWeight: 600 }}>Question {questionNumber}</span>
              {SUPPORTS_SYNTHESIS && (
                <button
                  onClick={() => setMuted((m) => !m)}
                  title={muted ? 'Unmute questions' : 'Mute questions'}
                  style={{ background: 'none', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 8, padding: 8, color: 'rgba(255,255,255,0.6)', cursor: 'pointer', display: 'flex' }}
                >
                  {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                </button>
              )}
            </div>

            <section style={{ ...panelStyle, padding: 24, marginBottom: 16 }}>
              <p style={{ margin: 0, fontSize: 18, lineHeight: 1.5, fontWeight: 600 }}>{question}</p>
            </section>

            <section style={{ ...panelStyle, padding: 18 }}>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder={SUPPORTS_RECOGNITION ? 'Speak using the mic, or type your answer here...' : 'Type your answer here...'}
                rows={5}
                style={{
                  width: '100%', background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8,
                  padding: 14, color: '#fff', fontSize: 14, lineHeight: 1.55, resize: 'vertical', outline: 'none', boxSizing: 'border-box',
                }}
              />
              <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
                {SUPPORTS_RECOGNITION && (
                  <button
                    onClick={toggleListening}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 7,
                      background: listening ? 'rgba(248,113,113,0.15)' : 'rgba(255,255,255,0.07)',
                      border: `1px solid ${listening ? 'rgba(248,113,113,0.4)' : 'rgba(255,255,255,0.14)'}`,
                      borderRadius: 8, padding: '10px 16px', color: listening ? '#f87171' : '#fff',
                      fontSize: 13, fontWeight: 600, cursor: 'pointer',
                    }}
                  >
                    {listening ? <MicOff size={14} /> : <Mic size={14} />}
                    {listening ? 'Stop listening' : 'Speak answer'}
                  </button>
                )}
                <div style={{ flex: 1 }} />
                <button
                  onClick={submitAnswer}
                  disabled={!answer.trim() || sending || finishing}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    background: answer.trim() && !sending ? '#fff' : 'rgba(255,255,255,0.12)',
                    color: '#000', border: 'none', borderRadius: 8, padding: '10px 20px',
                    fontWeight: 700, fontSize: 14, cursor: answer.trim() && !sending ? 'pointer' : 'not-allowed',
                  }}
                >
                  {sending || finishing ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={14} />}
                  {finishing ? 'Wrapping up...' : 'Submit answer'}
                </button>
              </div>
            </section>

            {transcriptLog.length > 0 && (
              <details style={{ marginTop: 16 }}>
                <summary style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, cursor: 'pointer' }}>
                  View earlier answers ({transcriptLog.length})
                </summary>
                <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
                  {transcriptLog.map((t, i) => (
                    <div key={i} style={{ ...panelStyle, padding: 14 }}>
                      <p style={{ margin: '0 0 6px', color: 'rgba(255,255,255,0.5)', fontSize: 12.5 }}>{t.question}</p>
                      <p style={{ margin: 0, color: '#fff', fontSize: 13.5, lineHeight: 1.5 }}>{t.answer}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </>
        )}

        {stage === 'feedback' && feedback && (
          <>
            <header style={{ marginBottom: 24, textAlign: 'center' }}>
              <p style={{ color: 'rgba(255,255,255,0.46)', fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>Interview complete</p>
              <div style={{
                width: 96, height: 96, borderRadius: '50%', margin: '0 auto 14px',
                background: 'rgba(255,255,255,0.06)', border: '2px solid rgba(255,255,255,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ fontSize: 32, fontWeight: 800 }}>{feedback.overall_score}</span>
              </div>
              <p style={{ margin: 0, color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>out of 100</p>
            </header>

            {feedback.strengths?.length > 0 && (
              <section style={{ ...panelStyle, padding: 20, marginBottom: 14 }}>
                <h2 style={{ margin: '0 0 12px', fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 7, color: '#4ade80' }}>
                  <ThumbsUp size={14} /> Strengths
                </h2>
                <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 6 }}>
                  {feedback.strengths.map((s, i) => (
                    <li key={i} style={{ color: 'rgba(255,255,255,0.75)', fontSize: 13.5, lineHeight: 1.5 }}>{s}</li>
                  ))}
                </ul>
              </section>
            )}

            {feedback.improvements?.length > 0 && (
              <section style={{ ...panelStyle, padding: 20, marginBottom: 14 }}>
                <h2 style={{ margin: '0 0 12px', fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 7, color: '#fbbf24' }}>
                  <ThumbsDown size={14} /> Room to improve
                </h2>
                <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 6 }}>
                  {feedback.improvements.map((s, i) => (
                    <li key={i} style={{ color: 'rgba(255,255,255,0.75)', fontSize: 13.5, lineHeight: 1.5 }}>{s}</li>
                  ))}
                </ul>
              </section>
            )}

            {feedback.per_question_feedback?.length > 0 && (
              <section style={{ ...panelStyle, padding: 20, marginBottom: 20 }}>
                <h2 style={{ margin: '0 0 14px', fontSize: 14, color: 'rgba(255,255,255,0.6)' }}>Per-question notes</h2>
                <div style={{ display: 'grid', gap: 12 }}>
                  {feedback.per_question_feedback.map((q, i) => (
                    <div key={i}>
                      <p style={{ margin: '0 0 4px', color: 'rgba(255,255,255,0.85)', fontSize: 13.5, fontWeight: 600 }}>{q.question}</p>
                      <p style={{ margin: 0, color: 'rgba(255,255,255,0.5)', fontSize: 13, lineHeight: 1.5 }}>{q.feedback}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <button
              onClick={startOver}
              style={{
                width: '100%', background: '#fff', color: '#000', border: 'none', borderRadius: 8,
                padding: 14, fontWeight: 700, fontSize: 15, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              <RotateCcw size={16} /> Practice again
            </button>
          </>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </main>
  );
}
