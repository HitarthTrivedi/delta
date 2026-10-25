// A friend's invite link (/?ref=CODE) is remembered on this device until the
// person signs in; Today then asks whether to link up. Storage can be blocked
// (private mode): the invite is then simply not remembered.

const KEY = 'delta_ref';

export function rememberReferralFromUrl() {
  const ref = new URLSearchParams(window.location.search).get('ref');
  if (ref && /^[A-Za-z0-9]{4,16}$/.test(ref)) {
    try { localStorage.setItem(KEY, ref.toUpperCase()); } catch { /* not remembered */ }
  }
}

export function pendingReferral() {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

export function clearReferral() {
  try { localStorage.removeItem(KEY); } catch { /* nothing to clear */ }
}

export function inviteLink(code) {
  return `${window.location.origin}/?ref=${code}`;
}
