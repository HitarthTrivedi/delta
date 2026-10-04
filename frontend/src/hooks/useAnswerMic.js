import { useCallback, useEffect, useRef, useState } from 'react';

// Speech-to-text for interview answers (Chrome / Edge). Keeps listening
// through the browser's automatic stops until stop() is called, and can fire
// onSilence after the speaker pauses for `silenceMs`.
const SR = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export default function useAnswerMic({ silenceMs = 3000, onSilence } = {}) {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  const [silenceLeft, setSilenceLeft] = useState(null); // seconds until auto-send, or null

  const recRef = useRef(null);
  const wantRef = useRef(false);
  const finalRef = useRef('');
  const lastHeardRef = useRef(0);
  const onSilenceRef = useRef(onSilence);
  const tickRef = useRef(null);
  onSilenceRef.current = onSilence;

  const clearTick = () => {
    clearInterval(tickRef.current);
    tickRef.current = null;
    setSilenceLeft(null);
  };

  const stop = useCallback(() => {
    wantRef.current = false;
    clearTick();
    try { recRef.current?.stop(); } catch { /* already stopped */ }
    setListening(false);
  }, []);

  const start = useCallback((initial = '') => {
    if (!SR) return;
    setError(null);
    finalRef.current = initial ? `${initial.trim()} ` : '';
    setTranscript(initial);
    wantRef.current = true;

    const begin = () => {
      const rec = new SR();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = navigator.language && navigator.language.startsWith('en') ? navigator.language : 'en-US';
      rec.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const chunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalRef.current += `${chunk.trim()} `;
          else interim += chunk;
        }
        lastHeardRef.current = Date.now();
        setTranscript(`${finalRef.current}${interim}`.trim());
      };
      rec.onerror = (e) => {
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
          wantRef.current = false;
          setError('Microphone access was blocked. Allow it in the browser, or type your answer.');
        } else if (e.error === 'audio-capture') {
          wantRef.current = false;
          setError('No microphone found. You can type your answer instead.');
        }
      };
      rec.onend = () => {
        // Chrome ends recognition after pauses; keep going while wanted.
        if (wantRef.current) {
          try { begin(); } catch { setListening(false); }
        } else {
          setListening(false);
        }
      };
      recRef.current = rec;
      rec.start();
    };

    try {
      begin();
      setListening(true);
      lastHeardRef.current = 0;
    } catch {
      setListening(false);
    }

    clearInterval(tickRef.current);
    tickRef.current = setInterval(() => {
      if (!onSilenceRef.current || !lastHeardRef.current || !finalRef.current.trim()) {
        setSilenceLeft(null);
        return;
      }
      const left = silenceMs - (Date.now() - lastHeardRef.current);
      if (left <= 0) {
        const text = finalRef.current.trim();
        lastHeardRef.current = 0;
        setSilenceLeft(null);
        onSilenceRef.current(text);
      } else {
        setSilenceLeft(Math.ceil(left / 1000));
      }
    }, 250);
  }, [silenceMs]);

  useEffect(() => () => {
    wantRef.current = false;
    clearInterval(tickRef.current);
    try { recRef.current?.stop(); } catch { /* ignore */ }
  }, []);

  return { supported: !!SR, listening, transcript, setTranscript, error, silenceLeft, start, stop };
}
