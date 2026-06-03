export function normalizeTask(action, index = 0) {
  return {
    ...action,
    id: String(action.id || action.node_id || action.skill || action.title || action.label || `task-${index}`),
    title: action.title || action.label || action.skill || `Task ${index + 1}`,
    detail: action.description || action.detail || action.proof || action.action || action.why_now || '',
    type: action.type || 'project',
    source: action.source || action.platform || '',
    url: action.url || action.resource_url || '',
  };
}

export function getCurrentActions(context, fallbackActions = []) {
  const primary = context?.roadmap?.weekly_focus?.primary_actions || [];
  const source = primary.length ? primary : fallbackActions;
  return source.map((action, index) => normalizeTask(action, index));
}

function cleanTitle(value) {
  return String(value || '')
    .replace(/^Completed Agent 2 task:\s*/i, '')
    .replace(/^Reopened Agent 2 task:\s*/i, '')
    .replace(/^Agent 2 task:\s*/i, '')
    .trim();
}

function isAfterWeekStart(event, currentWeekStartedAt) {
  if (!currentWeekStartedAt) return true;
  if (!event.created_at) return true;
  return new Date(event.created_at).getTime() >= new Date(currentWeekStartedAt).getTime();
}

export function getTaskProgress(context, fallbackActions = []) {
  const actions = getCurrentActions(context, fallbackActions);
  const journey = context?.journey_until_today || [];
  const currentWeekStartedAt = context?.current_week_started_at || null;
  const taskState = {};
  const taskTitles = {};
  const orderedEvents = [...journey]
    .filter(event => isAfterWeekStart(event, currentWeekStartedAt))
    .sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));

  orderedEvents.forEach(event => {
    const type = String(event.event_type || '');
    if (!['weekly_task_completed', 'weekly_task_reopened', 'weekly_task_skipped'].includes(type)) return;
    const evidence = event.evidence || {};
    const id = String(evidence.id || evidence.node_id || evidence.skill || evidence.title || event.id);
    taskState[id] = type;
    taskTitles[id] = cleanTitle(evidence.title || event.summary || id);
  });

  const done = [];
  const left = [];
  const changed = [];
  const skipped = [];
  const checkedByIndex = {};
  const skippedByIndex = {};

  actions.forEach((action, index) => {
    const isDone = taskState[action.id] === 'weekly_task_completed';
    const wasReopened = taskState[action.id] === 'weekly_task_reopened';
    const wasSkipped = taskState[action.id] === 'weekly_task_skipped';
    checkedByIndex[index] = isDone;
    skippedByIndex[index] = wasSkipped;
    if (isDone) {
      done.push(action);
    } else if (wasSkipped) {
      skipped.push({ ...action, detail: 'You chose to skip this task for now.' });
    } else {
      left.push(action);
      if (wasReopened) {
        changed.push({ ...action, detail: 'This was marked done before, then changed back to not done.' });
      }
    }
  });

  return {
    actions,
    checkedByIndex,
    done,
    left,
    changed,
    skipped,
    totalCurrent: actions.length,
    currentWeekStartedAt,
    taskTitles,
    skippedByIndex,
  };
}
