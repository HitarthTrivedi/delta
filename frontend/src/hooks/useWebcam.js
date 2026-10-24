import { useCallback, useEffect, useRef, useState } from 'react';

// Live camera preview for the interview's self-view tile. The stream only
// ever goes to a local <video> element: nothing is recorded or uploaded.
export default function useWebcam() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [on, setOn] = useState(false);
  const [error, setError] = useState(null);
  const supported = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;

  const attach = useCallback(() => {
    if (videoRef.current && streamRef.current && videoRef.current.srcObject !== streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, []);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setOn(false);
  }, []);

  const start = useCallback(async () => {
    if (!supported) { setError('Camera not supported in this browser.'); return; }
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' }, audio: false });
      streamRef.current = stream;
      setOn(true);
      attach();
    } catch {
      setError('Camera access was blocked or no camera was found.');
      setOn(false);
    }
  }, [supported, attach]);

  // Attach once the camera is on (the <video> element mounts in that same render).
  useEffect(() => { if (on) attach(); }, [on, attach]);

  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), []);

  return { videoRef, on, error, supported, start, stop };
}
