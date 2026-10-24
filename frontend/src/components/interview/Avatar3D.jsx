import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { TalkingHead } from '@met4citizen/talkinghead';
// Imported directly: TalkingHead's own lip-sync loader uses a runtime-computed
// import() that the bundler can't follow, so the English module is registered by hand.
import { LipsyncEn } from '@met4citizen/talkinghead/modules/lipsync-en.mjs';
import { sandboxInterviewAPI } from '../../lib/api';

// The interviewer's 3D face. Model: "Aria", built with MPFB from CC0 MakeHuman
// assets in a business suit (see tools/avatar/), Meshopt-compressed to ~2.3 MB.
// Voice + word timings come from our backend (Google Cloud TTS); TalkingHead turns
// the words into mouth shapes (visemes) in time with the audio.
const AVATAR_URL = '/avatars/interviewer.glb';

function b64ToArrayBuffer(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

/**
 * Props: userId, voice (TTS voice name), audioCtx (shared AudioContext, resumed
 * by the page on a click so audio may play), fallback (shown until the model
 * is ready), onError(err).
 * Ref API: whenReady(ms), speak(text) -> Promise (rejects if the voice fails, so
 * the caller can fall back), stop(), setState(state).
 */
const Avatar3D = forwardRef(function Avatar3D({ userId, voice, audioCtx, fallback, onError }, ref) {
  const nodeRef = useRef(null);
  const headRef = useRef(null);
  const pendingRef = useRef(null); // resolve() of the utterance in progress
  const runRef = useRef(0);
  const readyRef = useRef(null);
  if (!readyRef.current) {
    let resolve;
    const promise = new Promise((r) => { resolve = r; });
    readyRef.current = { promise, resolve };
  }
  const [ready, setReady] = useState(false);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  useEffect(() => {
    let cancelled = false;
    let head;
    try {
      head = new TalkingHead(nodeRef.current, {
        audioCtx,
        lipsyncModules: [],
        lipsyncLang: 'en',
        cameraView: 'upper',
        cameraRotateEnable: false,
        modelFPS: 30,
        avatarMood: 'neutral',
        avatarIdleEyeContact: 0.6,
        avatarSpeakingEyeContact: 0.85,
      });
      head.lipsync.en = new LipsyncEn();
      headRef.current = head;
    } catch (err) {
      onErrorRef.current?.(err);
      return undefined;
    }
    head.showAvatar({ url: AVATAR_URL, body: 'F', avatarMood: 'neutral', lipsyncLang: 'en' })
      .then(() => {
        if (cancelled) return;
        setReady(true);
        readyRef.current.resolve();
      })
      .catch((err) => { if (!cancelled) onErrorRef.current?.(err); });
    return () => {
      cancelled = true;
      pendingRef.current?.();
      try { head.stopSpeaking(); head.dispose(); } catch { /* already gone */ }
      headRef.current = null;
    };
  }, [audioCtx]);

  useImperativeHandle(ref, () => {
    const api = {
      whenReady(ms) {
        return Promise.race([
          readyRef.current.promise,
          new Promise((_, reject) => setTimeout(() => reject(new Error('avatar load timed out')), ms)),
        ]);
      },
      stop() {
        runRef.current += 1;
        try { headRef.current?.stopSpeaking(); } catch { /* ignore */ }
        pendingRef.current?.();
        pendingRef.current = null;
      },
      setState(state) {
        const head = headRef.current;
        if (!head?.armature) return;
        try {
          if (state === 'listening') head.makeEyeContact(8000);
          else if (state === 'thinking') {
            // A brief glance away while "thinking", like a person would.
            const r = nodeRef.current.getBoundingClientRect();
            head.lookAt(r.left + r.width * 0.25, r.top + r.height * 0.15, 1200);
          }
        } catch { /* cosmetic only */ }
      },
      async speak(text) {
        const head = headRef.current;
        if (!head?.armature) throw new Error('avatar not ready');
        api.stop();
        const run = runRef.current;
        const { audio, words, wtimes } = await sandboxInterviewAPI.tts(userId, text, voice);
        if (run !== runRef.current) return; // interrupted while fetching
        const buffer = await head.audioCtx.decodeAudioData(b64ToArrayBuffer(audio));
        if (run !== runRef.current) return;
        const total = buffer.duration * 1000;
        const wdurations = wtimes.map((t, i) => Math.max(60, (i + 1 < wtimes.length ? wtimes[i + 1] : total - 150) - t));
        await new Promise((resolve) => {
          pendingRef.current = resolve;
          head.speakAudio({ audio: buffer, words, wtimes, wdurations }, { lipsyncLang: 'en' });
          head.speakMarker(() => { if (pendingRef.current === resolve) pendingRef.current = null; resolve(); });
        });
      },
    };
    return api;
  }, [userId, voice]);

  return (
    <>
      {!ready && fallback}
      <div
        ref={nodeRef}
        role="img"
        aria-label="Aria, your AI interviewer"
        style={{ position: 'absolute', inset: 0, opacity: ready ? 1 : 0, transition: 'opacity 400ms ease' }}
      />
    </>
  );
});

export default Avatar3D;
