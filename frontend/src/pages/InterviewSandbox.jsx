import React, { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Mic, MicOff, Video, VideoOff, Volume2, VolumeX, Captions, CaptionsOff, Send, Loader2,
  PhoneOff, ArrowRight, RotateCcw, LayoutDashboard, Keyboard,
} from 'lucide-react';
import { toast } from 'sonner';
import { sandboxInterviewAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';
import { useUserWithSkills } from '../hooks/useUser';
import { useSandboxReport } from '../hooks/useSandboxReport';
import useInterviewerVoice from '../hooks/useInterviewerVoice';
import useAnswerMic from '../hooks/useAnswerMic';
import useWebcam from '../hooks/useWebcam';
import InterviewerAvatar from '../components/interview/InterviewerAvatar';
import InterviewReport from '../components/interview/InterviewReport';

// three.js + the 3D model only load when the 3D interviewer is actually used.
const Avatar3D = lazy(() => import('../components/interview/Avatar3D'));

const panel = { background: '#050505', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 };
const muted = 'rgba(255,255,255,0.5)';

const ROLE_TYPE_KEYS = ['technical', 'behavioral', 'case', 'system_design'];
const TECH_FIELDS = ['cs_ai', 'data'];

// Interview rounds adapt to the student's field: "Technical" + system design for
// software/data, "Role knowledge" for everyone else; case rounds for all.
function buildRoleTypes(field) {
  const tech = field && TECH_FIELDS.includes(field.id);
  return [
    tech
      ? { key: 'technical', label: 'Technical', desc: 'CS fundamentals, coding concepts, your projects' }
      : { key: 'technical', label: 'Role knowledge', desc: `Core knowledge and practice of ${field?.label || 'your field'}` },
    { key: 'behavioral', label: 'Behavioral / HR', desc: 'Teamwork, conflict, ownership, "tell me about a time"' },
    { key: 'case', label: 'Case / Scenario', desc: 'A realistic situation from your field to reason through' },
    ...(tech ? [{ key: 'system_design', label: 'System Design', desc: 'Architecture, scaling and trade-offs' }] : []),
  ];
}
const DIFFICULTIES = [
  { key: 'entry', label: 'Entry level' },
  { key: 'intermediate', label: 'Intermediate' },
  { key: 'advanced', label: 'Advanced' },
];
const QUESTION_COUNTS = [3, 5, 8];
const ACKS = ['Thanks.', 'Got it.', 'Okay, thank you.', 'Alright.', 'Thanks for that.'];
const STATE_LABEL = { joining: 'Joining…', speaking: 'Speaking…', listening: 'Listening…', thinking: 'Thinking…', finishing: 'Preparing your report…', idle: 'Ready' };

const LAST_SETTINGS_KEY = 'delta_interview_last';

function hasWebGL2() {
  try {
    return !!(window.WebGL2RenderingContext && document.createElement('canvas').getContext('webgl2'));
  } catch {
    return false;
  }
}

// One AudioContext for every 3D avatar instance. Browsers only let audio play
// after a click, so the page resumes it from click handlers ("Join", "Hear Aria").
let sharedAudioCtx;
function audioContext() {
  if (sharedAudioCtx === undefined) {
    const AC = window.AudioContext || window.webkitAudioContext;
    sharedAudioCtx = AC ? new AC() : null;
  }
  return sharedAudioCtx;
}
function unlockAudio() {
  audioContext()?.resume?.().catch(() => {});
}

function readLastSettings() {
  try { return JSON.parse(localStorage.getItem(LAST_SETTINGS_KEY)) || null; } catch { return null; }
}

function fmt(sec) {
  const m = Math.floor(sec / 60);
  return `${String(m).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
}

function Segmented({ options, value, onChange, label }) {
  return (
    <div role="radiogroup" aria-label={label} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {options.map((o) => (
        <button
          key={o.key}
          role="radio"
          aria-checked={value === o.key}
          onClick={() => onChange(o.key)}
          style={{
            padding: '9px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer', color: '#fff',
            background: value === o.key ? 'rgba(255,255,255,0.12)' : '#0a0a0a',
            border: `1px solid ${value === o.key ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.1)'}`,
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export default function InterviewSandbox() {
  const userId = useAuthStore((state) => state.userId);
  const { data: user } = useUserWithSkills(userId);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  const voice = useInterviewerVoice();
  const cam = useWebcam();

  // ── interviewer engine: 3D lip-synced avatar when the backend has a TTS key
  // and the browser has WebGL2; otherwise (or after any 3D failure) the 2D Aria
  // with the browser's own voice.
  const avatarRef = useRef(null);
  const [avatarCfg, setAvatarCfg] = useState(null);
  const [avatar3d, setAvatar3d] = useState('off'); // off | on | failed
  const [speaking3d, setSpeaking3d] = useState(false);
  const use3d = avatar3d === 'on';
  const use3dRef = useRef(false);
  use3dRef.current = use3d;

  // ── setup
  const [stage, setStage] = useState('setup'); // setup | call | report
  const [roleType, setRoleType] = useState(ROLE_TYPE_KEYS.includes(params.get('type')) ? params.get('type') : 'technical');
  const { data: sandboxReport } = useSandboxReport(userId);
  const field = useMemo(() => (sandboxReport ? { id: sandboxReport.field, label: sandboxReport.field_label } : null), [sandboxReport]);
  const roleTypes = useMemo(() => buildRoleTypes(field), [field]);
  const [targetRole, setTargetRole] = useState('');
  const [difficulty, setDifficulty] = useState('entry');
  const [numQuestions, setNumQuestions] = useState(5);
  const [wantCamera, setWantCamera] = useState(true);
  const [autoSend, setAutoSend] = useState(true);
  const [starting, setStarting] = useState(false);

  // ── call
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState('');
  const [qNum, setQNum] = useState(1);
  const [total, setTotal] = useState(5);
  const [phase, setPhase] = useState('idle'); // speaking | listening | thinking | finishing | finish_error
  const [answer, setAnswer] = useState('');
  const [answered, setAnswered] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [captions, setCaptions] = useState(true);
  const [mutedVoice, setMutedVoice] = useState(false);

  // ── report
  const [report, setReport] = useState(null);

  const submitRef = useRef(null);
  const activeRef = useRef(false);
  const submittingRef = useRef(false); // blocks a second send while one is in flight
  const quickStartedRef = useRef(false);
  const mic = useAnswerMic({
    silenceMs: 3000,
    onSilence: autoSend ? (text) => submitRef.current?.(text) : undefined,
  });
  const voiceMode = mic.supported;

  useEffect(() => {
    if (!targetRole && user?.target_role) setTargetRole(user.target_role);
  }, [user, targetRole]);

  useEffect(() => {
    if (!userId) return;
    sandboxInterviewAPI.avatar(userId).then((cfg) => {
      setAvatarCfg(cfg);
      if (cfg?.tts && hasWebGL2()) setAvatar3d((s) => (s === 'off' ? 'on' : s));
    }).catch(() => {});
  }, [userId]);

  // Live transcript flows into the answer box while the mic is on.
  useEffect(() => {
    if (mic.listening) setAnswer(mic.transcript);
  }, [mic.transcript, mic.listening]);

  // Call timer
  useEffect(() => {
    if (stage !== 'call') return undefined;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [stage]);

  // Leaving the page ends speech, mic and camera.
  useEffect(() => () => { activeRef.current = false; }, []);

  /** Speak as the interviewer (3D voice when available, else the browser's). */
  const say = useCallback(async (text) => {
    if (use3dRef.current && avatarRef.current) {
      setSpeaking3d(true);
      try {
        await avatarRef.current.whenReady(6000);
        await avatarRef.current.speak(text);
        return;
      } catch {
        setAvatar3d('failed'); // the rest of this visit uses the 2D interviewer
      } finally {
        setSpeaking3d(false);
      }
    }
    await voice.speak(text);
  }, [voice]);

  const hush = useCallback(() => {
    avatarRef.current?.stop();
    voice.cancel();
  }, [voice]);

  const askQuestion = useCallback(async (text) => {
    setQuestion(text);
    setAnswer('');
    setPhase('speaking');
    if (!mutedVoice) await say(text);
    else await new Promise((r) => setTimeout(r, 400));
    if (!activeRef.current) return;
    submittingRef.current = false;
    setPhase('listening');
    if (voiceMode) mic.start('');
  }, [mutedVoice, say, voiceMode, mic]);

  const startInterview = useCallback(async (override) => {
    const opts = override || { role_type: roleType, target_role: targetRole, difficulty, num_questions: numQuestions };
    unlockAudio();
    setStarting(true);
    // Join the call right away: the 3D interviewer loads while the first question is written.
    activeRef.current = true;
    submittingRef.current = false;
    setStage('call');
    setPhase('joining');
    setQuestion('');
    setAnswer('');
    setTotal(opts.num_questions || numQuestions);
    setQNum(1);
    setAnswered(0);
    setElapsed(0);
    setReport(null);
    if (wantCamera) cam.start();
    try {
      const data = await sandboxInterviewAPI.start(userId, opts);
      if (!activeRef.current) return; // left while joining
      try { localStorage.setItem(LAST_SETTINGS_KEY, JSON.stringify(opts)); } catch { /* ignore */ }
      setSessionId(data.session_id);
      setQNum(data.question_number || 1);
      setTotal(data.total_questions || opts.num_questions || numQuestions);
      askQuestion(data.question);
    } catch (err) {
      activeRef.current = false;
      cam.stop();
      setStage('setup');
      toast.error(err?.response?.data?.detail || 'Could not start the interview. Try again.');
    } finally {
      setStarting(false);
    }
  }, [roleType, targetRole, difficulty, numQuestions, wantCamera, cam, userId, askQuestion]);

  // One-click start from the Test Center (?quick=1): last settings, or sensible defaults.
  useEffect(() => {
    if (!userId || params.get('quick') !== '1' || quickStartedRef.current) return;
    quickStartedRef.current = true;
    setParams({}, { replace: true });
    const last = readLastSettings();
    const type = ROLE_TYPE_KEYS.includes(params.get('type')) ? params.get('type') : null;
    const opts = last || { role_type: 'technical', target_role: '', difficulty: 'entry', num_questions: 5 };
    if (type) opts.role_type = type;
    setRoleType(opts.role_type);
    if (opts.target_role) setTargetRole(opts.target_role);
    setDifficulty(opts.difficulty || 'entry');
    setNumQuestions(opts.num_questions || 5);
    startInterview(opts);
  }, [userId, params, setParams, startInterview]);

  const finish = useCallback(async () => {
    mic.stop();
    setPhase('finishing');
    if (!mutedVoice) say("Thank you, that's the end of our interview. Give me a moment to put together your feedback.");
    try {
      const data = await sandboxInterviewAPI.finish(userId, sessionId);
      activeRef.current = false;
      hush();
      cam.stop();
      setReport({ feedback: data.feedback, transcript: data.transcript, settings: data.settings });
      setStage('report');
    } catch (err) {
      setPhase('finish_error');
      toast.error(err?.response?.data?.detail || 'Could not generate your report. Try again.');
    }
  }, [mic, mutedVoice, say, hush, userId, sessionId, cam]);

  const submitAnswer = useCallback(async (raw) => {
    const text = (raw ?? answer).trim();
    // The auto-send timer and the Send button can fire together; only the first counts.
    if (!text || phase !== 'listening' || submittingRef.current) return;
    submittingRef.current = true;
    mic.stop();
    setPhase('thinking');
    setAnswer(text);
    if (!mutedVoice) say(ACKS[Math.floor(Math.random() * ACKS.length)]);
    try {
      const data = await sandboxInterviewAPI.respond(userId, sessionId, text);
      setAnswered((n) => n + 1);
      if (data.done || !data.question) {
        await finish();
      } else {
        setQNum(data.question_number);
        if (data.total_questions) setTotal(data.total_questions);
        askQuestion(data.question);
      }
    } catch (err) {
      toast.error('Could not send your answer. Try again.');
      submittingRef.current = false;
      setPhase('listening');
    }
  }, [answer, phase, mic, mutedVoice, say, userId, sessionId, finish, askQuestion]);
  submitRef.current = submitAnswer;

  const endCall = () => {
    if (phase === 'thinking' || phase === 'finishing') return;
    if (answered > 0 || answer.trim()) {
      if (answer.trim() && phase === 'listening') { submitAnswer(answer); return; }
      finish();
      return;
    }
    activeRef.current = false;
    hush();
    mic.stop();
    cam.stop();
    setStage('setup');
  };

  const toggleMic = () => {
    if (mic.listening) mic.stop();
    else if (phase === 'listening') mic.start(answer);
  };

  const toggleCamera = () => (cam.on ? cam.stop() : cam.start());

  const avatarState = phase === 'speaking' || voice.speaking || speaking3d ? 'speaking'
    : phase === 'listening' ? 'listening'
      : phase === 'thinking' || phase === 'finishing' ? 'thinking' : 'idle';

  useEffect(() => { avatarRef.current?.setState(avatarState); }, [avatarState]);

  // The interviewer's face: 3D when available, with the 2D Aria shown while it
  // loads and used instead if it fails.
  const renderInterviewer = (svg) => (use3d ? (
    <Suspense fallback={svg}>
      <Avatar3D
        ref={avatarRef}
        userId={userId}
        voice={avatarCfg?.voice}
        audioCtx={audioContext()}
        fallback={svg}
        onError={() => setAvatar3d('failed')}
      />
    </Suspense>
  ) : svg);

  // ─────────────────────────────── Setup ───────────────────────────────
  if (stage === 'setup') {
    return (
      <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
        <div style={{ maxWidth: 980, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 28, alignItems: 'start' }}>
          <div>
            <p style={{ color: muted, fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>AI Mock Interview</p>
            <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3rem)', lineHeight: 1.08, margin: 0 }}>Face a real interview before the real one.</h1>
            <p style={{ margin: '14px 0 24px', color: muted, fontSize: 15, lineHeight: 1.6 }}>
              Aria, your AI interviewer, asks questions out loud on a video call, follows up on what you say, and scores you like a hiring panel would.
              Answer by speaking or typing.
            </p>
            <div style={{ position: 'relative', height: 280, borderRadius: 12, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', background: use3d ? 'radial-gradient(circle at 50% 40%, #191726 0%, #050505 75%)' : 'transparent' }}>
              {renderInterviewer(<InterviewerAvatar state={voice.speaking ? 'speaking' : 'idle'} getLevel={voice.getLevel} size={220} />)}
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 14, flexWrap: 'wrap' }}>
              <button
                onClick={() => { unlockAudio(); say(`Hi${user?.name ? ` ${user.name.split(' ')[0]}` : ''}, I'm Aria. I'll be interviewing you today. Ready when you are.`); }}
                disabled={!use3d && !voice.supported}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, padding: '8px 14px', color: '#fff', fontSize: 13, cursor: 'pointer' }}
              >
                <Volume2 size={14} /> Hear Aria
              </button>
              {!use3d && voice.voices.length > 1 && (
                <select
                  value={voice.voice?.voiceURI || ''}
                  onChange={(e) => voice.setVoiceURI(e.target.value)}
                  aria-label="Interviewer voice"
                  style={{ background: '#0a0a0a', color: '#fff', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, padding: '8px 10px', fontSize: 13, maxWidth: 240 }}
                >
                  {voice.voices.map((v) => <option key={v.voiceURI} value={v.voiceURI}>{v.name} ({v.lang})</option>)}
                </select>
              )}
            </div>
          </div>

          <section style={{ ...panel, padding: 22, display: 'grid', gap: 20 }}>
            <div>
              <h2 style={{ margin: '0 0 10px', fontSize: 14, color: muted }}>Interview type</h2>
              <div style={{ display: 'grid', gap: 8 }}>
                {roleTypes.map((rt) => (
                  <button
                    key={rt.key}
                    onClick={() => setRoleType(rt.key)}
                    aria-pressed={roleType === rt.key}
                    style={{
                      textAlign: 'left', padding: '12px 14px', borderRadius: 8, cursor: 'pointer', color: '#fff',
                      background: roleType === rt.key ? 'rgba(255,255,255,0.1)' : '#0a0a0a',
                      border: `1px solid ${roleType === rt.key ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.1)'}`,
                    }}
                  >
                    <span style={{ display: 'block', fontWeight: 700, fontSize: 14.5 }}>{rt.label}</span>
                    <span style={{ display: 'block', color: muted, fontSize: 12.5, marginTop: 2 }}>{rt.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="iv-role" style={{ display: 'block', margin: '0 0 8px', fontSize: 14, color: muted }}>Role you're interviewing for</label>
              <input
                id="iv-role"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Staff Nurse, Financial Analyst, Backend Engineer"
                maxLength={120}
                style={{ width: '100%', boxSizing: 'border-box', background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: 12, color: '#fff', fontSize: 14, outline: 'none' }}
              />
            </div>

            <div>
              <h2 style={{ margin: '0 0 8px', fontSize: 14, color: muted }}>Level</h2>
              <Segmented options={DIFFICULTIES} value={difficulty} onChange={setDifficulty} label="Difficulty" />
            </div>

            <div>
              <h2 style={{ margin: '0 0 8px', fontSize: 14, color: muted }}>Questions</h2>
              <Segmented options={QUESTION_COUNTS.map((n) => ({ key: n, label: `${n} questions` }))} value={numQuestions} onChange={setNumQuestions} label="Number of questions" />
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13.5, cursor: 'pointer' }}>
                <input type="checkbox" checked={wantCamera} onChange={() => setWantCamera((v) => !v)} />
                Show my camera (preview only, never recorded or uploaded)
              </label>
              {voiceMode && (
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13.5, cursor: 'pointer' }}>
                  <input type="checkbox" checked={autoSend} onChange={() => setAutoSend((v) => !v)} />
                  Send my answer automatically when I stop talking for 3 seconds
                </label>
              )}
              {!voiceMode && (
                <p style={{ margin: 0, color: muted, fontSize: 12.5, lineHeight: 1.5 }}>
                  Voice answers need Chrome or Edge. You can still type your answers here.
                </p>
              )}
            </div>

            <button
              onClick={() => startInterview()}
              disabled={starting}
              style={{
                width: '100%', background: '#fff', color: '#000', border: 'none', borderRadius: 8, padding: 14,
                fontWeight: 800, fontSize: 15, cursor: starting ? 'wait' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              {starting ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <ArrowRight size={16} />}
              {starting ? 'Aria is joining…' : 'Join the interview'}
            </button>
          </section>
        </div>
        <style>{'@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }'}</style>
      </main>
    );
  }

  // ─────────────────────────────── Report ───────────────────────────────
  if (stage === 'report' && report) {
    return (
      <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
        <div style={{ maxWidth: 860, margin: '0 auto' }}>
          <p style={{ color: muted, fontSize: 13, fontWeight: 650, margin: '0 0 10px' }}>Interview complete · {fmt(elapsed)}</p>
          <h1 style={{ fontSize: 'clamp(1.8rem, 4vw, 2.6rem)', margin: '0 0 20px' }}>Your interview report</h1>
          <InterviewReport feedback={report.feedback} transcript={report.transcript} settings={report.settings} />
          <div style={{ display: 'flex', gap: 12, marginTop: 20, flexWrap: 'wrap' }}>
            <button onClick={() => { setStage('setup'); setReport(null); }} style={{ flex: 1, minWidth: 200, background: '#fff', color: '#000', border: 'none', borderRadius: 8, padding: 14, fontWeight: 700, fontSize: 15, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <RotateCcw size={16} /> Practice again
            </button>
            <button onClick={() => navigate('/practice')} style={{ flex: 1, minWidth: 200, background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, padding: 14, fontWeight: 700, fontSize: 15, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <LayoutDashboard size={16} /> Back to Test Center
            </button>
          </div>
        </div>
      </main>
    );
  }

  // ─────────────────────────────── Call ───────────────────────────────
  const canSend = phase === 'listening' && answer.trim().length > 0;
  return (
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '4.75rem 1rem 1.5rem' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', display: 'grid', gap: 12 }}>
        {/* top bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', boxShadow: '0 0 0 4px rgba(239,68,68,0.2)' }} aria-hidden="true" />
            <span style={{ fontWeight: 700 }}>{roleTypes.find((r) => r.key === roleType)?.label || 'Mock'} interview</span>
            <span style={{ color: muted }}>· {targetRole || 'General'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 13 }}>
            <span style={{ color: muted }}>Question <strong style={{ color: '#fff' }}>{qNum}</strong> of {total}</span>
            <span style={{ fontVariantNumeric: 'tabular-nums', color: muted }} aria-label="Elapsed time">{fmt(elapsed)}</span>
          </div>
        </div>

        {/* video tiles */}
        <div className="iv-tiles">
          <section style={{ ...panel, minHeight: 380, position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(circle at 50% 40%, #191726 0%, #050505 75%)' }}>
            {renderInterviewer(<InterviewerAvatar state={avatarState} getLevel={voice.getLevel} size={250} />)}
            <span style={{ position: 'absolute', top: 14, left: 14, fontSize: 12, fontWeight: 700, background: 'rgba(0,0,0,0.55)', padding: '5px 10px', borderRadius: 6 }}>
              Aria · AI Interviewer
            </span>
            <span style={{ position: 'absolute', top: 14, right: 14, fontSize: 12, color: avatarState === 'listening' ? '#4ade80' : avatarState === 'speaking' ? '#f472b6' : muted, background: 'rgba(0,0,0,0.55)', padding: '5px 10px', borderRadius: 6 }}>
              {phase === 'finish_error' ? 'Report failed' : STATE_LABEL[phase] || STATE_LABEL[avatarState]}
            </span>
            {captions && question && (
              <p aria-live="polite" style={{ position: 'absolute', left: 16, right: 16, bottom: 14, margin: 0, textAlign: 'center', fontSize: 'clamp(15px, 2vw, 18px)', lineHeight: 1.5, background: 'rgba(0,0,0,0.72)', padding: '10px 14px', borderRadius: 8 }}>
                {question}
              </p>
            )}
          </section>

          <section style={{ ...panel, minHeight: 220, position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0b0b0f' }}>
            {cam.on ? (
              <video ref={cam.videoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)', position: 'absolute', inset: 0 }} />
            ) : (
              <div style={{ width: 84, height: 84, borderRadius: '50%', background: 'rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, fontWeight: 800 }}>
                {(user?.name || 'You')[0].toUpperCase()}
              </div>
            )}
            <span style={{ position: 'absolute', bottom: 12, left: 12, fontSize: 12, fontWeight: 700, background: 'rgba(0,0,0,0.55)', padding: '5px 10px', borderRadius: 6, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              {mic.listening ? <Mic size={12} style={{ color: '#4ade80' }} /> : <MicOff size={12} style={{ color: muted }} />} You
            </span>
            {cam.error && <span style={{ position: 'absolute', top: 12, left: 12, right: 12, fontSize: 11.5, color: muted }}>{cam.error}</span>}
          </section>
        </div>

        {/* answer panel */}
        <section style={{ ...panel, padding: 14 }}>
          {phase === 'finishing' || phase === 'finish_error' ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: 18, flexWrap: 'wrap' }}>
              {phase === 'finishing' ? (
                <><Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> <span>Aria is writing your report: scores, feedback and model answers…</span></>
              ) : (
                <>
                  <span style={{ color: muted }}>The report couldn't be generated.</span>
                  <button onClick={finish} style={{ background: '#fff', color: '#000', border: 'none', borderRadius: 8, padding: '10px 18px', fontWeight: 700, cursor: 'pointer' }}>Try again</button>
                </>
              )}
            </div>
          ) : (
            <>
              <label htmlFor="iv-answer" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: muted, marginBottom: 8, gap: 10, flexWrap: 'wrap' }}>
                <span>
                  {phase === 'joining' ? 'Aria is joining the call…' : phase === 'speaking' ? 'Aria is asking…' : phase === 'thinking' ? 'Aria is thinking about your answer…'
                    : mic.listening ? 'Listening. Speak your answer (you can also edit the text).' : 'Type your answer, or press the mic to speak.'}
                </span>
                {mic.silenceLeft != null && autoSend && <span style={{ color: '#4ade80' }}>Sending in {mic.silenceLeft}s… keep talking to continue</span>}
              </label>
              <textarea
                id="iv-answer"
                value={answer}
                onChange={(e) => { if (mic.listening) mic.stop(); setAnswer(e.target.value); }}
                onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitAnswer(); }}
                disabled={phase !== 'listening'}
                rows={3}
                placeholder={phase === 'listening' ? 'Your answer…' : ''}
                style={{ width: '100%', boxSizing: 'border-box', background: '#0a0a0a', border: `1px solid ${mic.listening ? 'rgba(74,222,128,0.45)' : 'rgba(255,255,255,0.12)'}`, borderRadius: 8, padding: 12, color: '#fff', fontSize: 15, lineHeight: 1.55, resize: 'vertical', outline: 'none' }}
              />
              {mic.error && <p style={{ margin: '8px 0 0', fontSize: 12.5, color: '#fbbf24' }}>{mic.error}</p>}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                {voiceMode && (
                  <button
                    onClick={toggleMic}
                    disabled={phase !== 'listening'}
                    aria-pressed={mic.listening}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 7, borderRadius: 999, padding: '10px 16px', fontSize: 13, fontWeight: 700, cursor: phase === 'listening' ? 'pointer' : 'not-allowed',
                      background: mic.listening ? 'rgba(74,222,128,0.15)' : 'rgba(255,255,255,0.08)', color: mic.listening ? '#4ade80' : '#fff',
                      border: `1px solid ${mic.listening ? 'rgba(74,222,128,0.5)' : 'rgba(255,255,255,0.15)'}`,
                    }}
                  >
                    {mic.listening ? <Mic size={15} /> : <MicOff size={15} />} {mic.listening ? 'Mic on' : 'Mic off'}
                  </button>
                )}
                {!voiceMode && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: muted, fontSize: 12.5 }}><Keyboard size={14} /> Typing mode</span>}
                <IconToggle on={captions} onClick={() => setCaptions((v) => !v)} onIcon={Captions} offIcon={CaptionsOff} label="Captions" />
                <IconToggle on={!mutedVoice} onClick={() => { if (!mutedVoice) hush(); setMutedVoice((v) => !v); }} onIcon={Volume2} offIcon={VolumeX} label="Interviewer voice" />
                <IconToggle on={cam.on} onClick={toggleCamera} onIcon={Video} offIcon={VideoOff} label="Camera" />
                <div style={{ flex: 1 }} />
                <button
                  onClick={endCall}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 7, background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.4)', borderRadius: 999, padding: '10px 16px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
                >
                  <PhoneOff size={15} /> {answered > 0 ? 'End & get report' : 'Leave'}
                </button>
                <button
                  onClick={() => submitAnswer()}
                  disabled={!canSend}
                  title="Send answer (Ctrl+Enter)"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 7, background: canSend ? '#fff' : 'rgba(255,255,255,0.12)', color: '#000', border: 'none', borderRadius: 999, padding: '10px 20px', fontSize: 14, fontWeight: 800, cursor: canSend ? 'pointer' : 'not-allowed' }}
                >
                  {phase === 'thinking' ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={15} />} Send answer
                </button>
              </div>
            </>
          )}
        </section>
      </div>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .iv-tiles { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 12px; }
        @media (max-width: 760px) { .iv-tiles { grid-template-columns: minmax(0, 1fr); } }
      `}</style>
    </main>
  );
}

function IconToggle({ on, onClick, onIcon: OnIcon, offIcon: OffIcon, label }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      aria-label={label}
      title={label}
      style={{ width: 40, height: 40, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', background: on ? 'rgba(255,255,255,0.08)' : 'rgba(239,68,68,0.15)', color: on ? '#fff' : '#f87171', border: `1px solid ${on ? 'rgba(255,255,255,0.15)' : 'rgba(239,68,68,0.4)'}` }}
    >
      {on ? <OnIcon size={16} /> : <OffIcon size={16} />}
    </button>
  );
}
