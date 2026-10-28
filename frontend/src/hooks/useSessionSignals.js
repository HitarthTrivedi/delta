import { useCallback, useEffect, useRef } from 'react';

// What the browser sees while a practice session is open: how often the tab
// was hidden and how much was pasted. Sent with the result, so the learner sees
// the same note a recruiter would. These are signals, not proof.
// `sessionKey` is the open session's id (null when none): counting restarts per session.
export default function useSessionSignals(sessionKey) {
  const counts = useRef({ tab_switches: 0, pastes: 0, pasted_chars: 0 });

  useEffect(() => {
    if (!sessionKey) return undefined;
    counts.current = { tab_switches: 0, pastes: 0, pasted_chars: 0 };
    const onVisibility = () => {
      if (document.hidden) counts.current.tab_switches = Math.min(999, counts.current.tab_switches + 1);
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [sessionKey]);

  const notePaste = useCallback((text) => {
    counts.current.pastes = Math.min(999, counts.current.pastes + 1);
    counts.current.pasted_chars = Math.min(1000000, counts.current.pasted_chars + (text || '').length);
  }, []);

  const snapshot = useCallback(() => ({ ...counts.current }), []);

  return { notePaste, snapshot };
}
