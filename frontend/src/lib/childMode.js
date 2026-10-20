// Child mode for Delta for School: while on, the app is locked to the child's
// learning page until the parent's PIN is entered. Stored per browser, and
// only honoured for the parent account that turned it on.
const KEY = 'delta_child_mode';

export function getChildMode(userId) {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || 'null');
    return value && value.parentId === userId ? value.childId : null;
  } catch {
    return null;
  }
}

export function enterChildMode(userId, childId) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ parentId: userId, childId }));
  } catch {
    // Storage blocked: child mode then lasts only for this page view.
  }
}

export function exitChildMode() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
