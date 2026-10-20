import { useCallback, useEffect, useRef, useState } from 'react';

// The AI interviewer's voice: browser speech synthesis, with a "mouth level"
// (0..1) the avatar reads every frame to lip-sync.
const SUPPORTED = typeof window !== 'undefined' && 'speechSynthesis' in window;
const PREF_KEY = 'delta_interviewer_voice';

// Higher is better: natural/neural voices first, then Google, then English variants.
function rankVoice(v) {
  if (!/^en/i.test(v.lang)) return -1;
  let score = 0;
  if (/natural|neural|online/i.test(v.name)) score += 60;
  if (/google/i.test(v.name)) score += 40;
  if (/aria|jenny|neerja|sonia|libby|female|samantha|zira/i.test(v.name)) score += 15;
  if (/en[-_](IN|GB|US)/i.test(v.lang)) score += 10;
  if (v.localService) score += 2; // local voices fire word-boundary events (better lip-sync)
  return score;
}

function readPref() {
  try { return localStorage.getItem(PREF_KEY); } catch { return null; }
}

// Chrome stops long utterances after ~15 s, so speak sentence by sentence.
function splitSentences(text) {
  const parts = (text || '').match(/[^.!?]+[.!?]*\s*/g) || [];
  return parts.map((p) => p.trim()).filter(Boolean);
}

export default function useInterviewerVoice() {
  const [voices, setVoices] = useState([]);
  const [voiceURI, setVoiceURIState] = useState(readPref);
  const [speaking, setSpeaking] = useState(false);
  const levelRef = useRef(0);
  const pulseRef = useRef(0);
  const speakingRef = useRef(false);
  const runIdRef = useRef(0);
  const rafRef = useRef(null);

  useEffect(() => {
    if (!SUPPORTED) return undefined;
    const load = () => {
      const list = window.speechSynthesis.getVoices().filter((v) => rankVoice(v) >= 0);
      list.sort((a, b) => rankVoice(b) - rankVoice(a));
      setVoices(list);
    };
    load();
    window.speechSynthesis.addEventListener('voiceschanged', load);
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', load);
      window.speechSynthesis.cancel();
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const voice = voices.find((v) => v.voiceURI === voiceURI) || voices[0] || null;

  const setVoiceURI = useCallback((uri) => {
    setVoiceURIState(uri);
    try { localStorage.setItem(PREF_KEY, uri); } catch { /* ignore */ }
  }, []);

  // Mouth level: word-boundary pulses (when the voice reports them) plus a
  // soft syllable-rate oscillation so the mouth still moves with voices that don't.
  const animate = useCallback(() => {
    const t = performance.now() / 1000;
    if (speakingRef.current) {
      const syllables = 0.35 + 0.3 * Math.abs(Math.sin(t * 11)) * (0.6 + 0.4 * Math.sin(t * 3.7));
      pulseRef.current *= 0.86;
      levelRef.current = Math.min(1, Math.max(syllables, pulseRef.current));
    } else {
      levelRef.current *= 0.75;
    }
    rafRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [animate]);

  const cancel = useCallback(() => {
    runIdRef.current += 1;
    if (SUPPORTED) window.speechSynthesis.cancel();
    speakingRef.current = false;
    setSpeaking(false);
  }, []);

  /** Speak text; resolves when finished (or cancelled). */
  const speak = useCallback((text, { rate = 1 } = {}) => {
    if (!SUPPORTED || !text) return Promise.resolve();
    window.speechSynthesis.cancel();
    const runId = ++runIdRef.current;
    const sentences = splitSentences(text);
    speakingRef.current = true;
    setSpeaking(true);

    const sayOne = (sentence) => new Promise((resolve) => {
      if (runId !== runIdRef.current) { resolve(); return; }
      const u = new SpeechSynthesisUtterance(sentence);
      if (voice) { u.voice = voice; u.lang = voice.lang; }
      u.rate = rate;
      u.pitch = 1;
      u.onboundary = () => { pulseRef.current = 1; };
      // Safety net: some engines occasionally never fire onend.
      const timer = setTimeout(resolve, 2500 + sentence.length * 90);
      const done = () => { clearTimeout(timer); resolve(); };
      u.onend = done;
      u.onerror = done;
      window.speechSynthesis.speak(u);
    });

    return sentences.reduce((p, s) => p.then(() => sayOne(s)), Promise.resolve()).then(() => {
      if (runId === runIdRef.current) {
        speakingRef.current = false;
        setSpeaking(false);
      }
    });
  }, [voice]);

  const getLevel = useCallback(() => levelRef.current, []);

  return { supported: SUPPORTED, voices, voice, setVoiceURI, speak, cancel, speaking, getLevel };
}
