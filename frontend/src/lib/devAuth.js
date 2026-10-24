// Local dev mode: sign in without Supabase (development only).
// ONLY active when REACT_APP_DEV_AUTH=true (set in frontend/.env.development.local,
// which `npm start` reads but production builds never do) AND the app is
// served from localhost. The backend must run with ALLOW_HEADER_AUTH=true.
// There is no password check: never enable this anywhere but your own machine.
const LOCAL_HOSTS = ['localhost', '127.0.0.1', '[::1]'];
const KEY = 'delta_dev_user';

export const DEV_AUTH = process.env.REACT_APP_DEV_AUTH === 'true'
  && typeof window !== 'undefined'
  && LOCAL_HOSTS.includes(window.location.hostname);

/** Same email → same account every time, so seeded test data persists across logins. */
export function devUserFromEmail(email, name) {
  const clean = String(email || '').trim().toLowerCase();
  const slug = clean.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'demo';
  return { id: `dev-${slug}`, email: clean, user_metadata: { full_name: name || clean.split('@')[0] } };
}

export function loadDevUser() {
  try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; }
}

export function saveDevUser(user) {
  try { localStorage.setItem(KEY, JSON.stringify(user)); } catch { /* storage blocked */ }
}

export function clearDevUser() {
  try { localStorage.removeItem(KEY); } catch { /* storage blocked */ }
}
