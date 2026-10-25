import { engagementAPI } from './api';

// Browser push for opt-in study reminders. Permission is only ever asked from
// a click (never on page load), and the service worker only shows reminders.

export function pushSupported() {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
}

function urlBase64ToUint8Array(base64) {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const raw = window.atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

/** Ask permission and register this browser. Throws with a readable message. */
export async function enablePush(userId) {
  if (!pushSupported()) throw new Error("This browser can't show reminders. Email reminders still work.");
  const { key } = await engagementAPI.pushKey();
  if (!key) throw new Error('Browser reminders are not set up on the server yet. Email reminders still work.');
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') throw new Error('Notifications are blocked for this site. You can allow them in your browser settings.');
  const reg = await navigator.serviceWorker.register('/sw.js');
  await navigator.serviceWorker.ready;
  const sub = (await reg.pushManager.getSubscription())
    || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(key) });
  await engagementAPI.addPush(userId, sub.toJSON());
}

export async function disablePush(userId) {
  if (!pushSupported()) return;
  const reg = await navigator.serviceWorker.getRegistration('/sw.js');
  const sub = reg && await reg.pushManager.getSubscription();
  if (sub) {
    await engagementAPI.removePush(userId, sub.endpoint).catch(() => {});
    await sub.unsubscribe().catch(() => {});
  }
}
