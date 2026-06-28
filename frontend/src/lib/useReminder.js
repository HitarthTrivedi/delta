import { useEffect } from 'react';
import { toast } from 'sonner';

const REMINDER_KEY = 'delta_last_reminded';

export function useReminder(actions, checked) {
  useEffect(() => {
    if (!actions?.length) return;

    const pendingCount = actions.filter((_, i) => !checked[i]).length;
    if (pendingCount === 0) return;

    const today = new Date().toDateString();
    if (localStorage.getItem(REMINDER_KEY) === today) return;

    // Delay so the page finishes loading before the notification fires
    const timer = setTimeout(() => {
      const msg = pendingCount === 1
        ? '1 task still pending this week'
        : `${pendingCount} tasks still pending this week`;

      toast.info(msg, {
        description: 'Stay on track — small weekly progress compounds fast.',
        duration: 7000,
      });

      // Browser notification (only if already granted — don't prompt unprompted)
      if ('Notification' in window && Notification.permission === 'granted') {
        try {
          new Notification('Delta — Weekly Reminder', {
            body: `You have ${msg}. Keep the streak going.`,
            icon: '/favicon.ico',
          });
        } catch (_) {}
      }

      localStorage.setItem(REMINDER_KEY, today);
    }, 2000);

    return () => clearTimeout(timer);
  }, [actions, checked]);
}

// Call this once on a user gesture (e.g., clicking "Enable reminders") to request permission
export async function requestNotificationPermission() {
  if (!('Notification' in window)) return 'unsupported';
  if (Notification.permission === 'granted') return 'granted';
  if (Notification.permission === 'denied') return 'denied';
  return Notification.requestPermission();
}
