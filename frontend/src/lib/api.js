import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import supabase from './supabaseClient';
import { DEV_AUTH } from './devAuth';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  // 90s default keeps headroom above the backend's 60s single-LLM-call bound,
  // so slow generations aren't aborted prematurely; the long weekly-cycle call
  // sets its own 300s override below.
  timeout: 90000,
});

// Inject the authenticated user's ID as X-User-Id and the JWT token in Authorization on every request.
// The backend uses these headers to enforce resource ownership (BOLA prevention).
api.interceptors.request.use((config) => {
  const userId = useAuthStore.getState().userId;
  const token = useAuthStore.getState().token;
  if (userId) {
    config.headers['X-User-Id'] = userId;
  }
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  // Local dev mode only: the backend's header auth carries no email, so pass it
  // (college staff invites are matched by email). Ignored unless ALLOW_HEADER_AUTH.
  const email = useAuthStore.getState().user?.email;
  if (DEV_AUTH && email) {
    config.headers['X-User-Email'] = email;
  }
  return config;
});

// Automatically handle expired or invalid JWT sessions.
// A 401 usually just means the access token expired before Supabase's auto
// refresh fired (background tab, laptop wake). Refresh once and retry the
// request; only log out if the refresh itself fails.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (DEV_AUTH && error.response && error.response.status === 401) {
      // Dev mode has no Supabase session to refresh: the backend isn't in header-auth mode.
      console.error('401 in local dev mode: start the backend with ALLOW_HEADER_AUTH=true.');
      return Promise.reject(error);
    }
    if (error.response && error.response.status === 401 && original && !original._retried) {
      original._retried = true;
      try {
        const { data, error: refreshError } = await supabase.auth.refreshSession();
        if (!refreshError && data?.session) {
          // onAuthStateChange in authStore updates the store + storage mirror.
          original.headers['Authorization'] = `Bearer ${data.session.access_token}`;
          original.headers['X-User-Id'] = data.session.user.id;
          return api(original);
        }
      } catch (_) {
        // fall through to logout
      }
      console.warn("Session expired and refresh failed, logging out...");
      useAuthStore.getState().logout();
      // Only redirect if not already on the login page to avoid redirect loops
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);


// ── Users API ──
export const usersAPI = {
  get: (userId) => api.get(`/users/${userId}`).then(r => r.data),
  getWithSkills: (userId) => api.get(`/users/${userId}/with-skills`).then(r => r.data),
  update: (userId, data) => api.put(`/users/${userId}`, data).then(r => r.data),
  getStats: (userId) => api.get(`/users/${userId}/stats`).then(r => r.data),
};

// ── Skills API ──
export const skillsAPI = {
  getAll: (userId) => api.get(`/skills/${userId}`).then(r => r.data),
  create: (data) => api.post('/skills', data).then(r => r.data),
  update: (skillId, data) => api.put(`/skills/${skillId}`, data).then(r => r.data),
  verify: (skillId, data) => api.post(`/skills/${skillId}/verify`, data).then(r => r.data),
};

// ── Briefs API ──
export const briefsAPI = {
  getLatest: (userId) => api.get(`/briefs/user/${userId}/latest`).then(r => r.data),
  generate: (userId) => api.post(`/briefs/generate/${userId}`).then(r => r.data),
  getCurrentScore: (userId) => api.get(`/briefs/scores/${userId}/current`).then(r => r.data),
  getScoreHistory: (userId, limit = 12) => api.get(`/briefs/scores/${userId}/history?limit=${limit}`).then(r => r.data),
  completeRecommendation: (recId, data) => api.post(`/briefs/recommendations/${recId}/complete`, data).then(r => r.data),
};

// ── Chat API ──
export const chatAPI = {
  send: (data) => api.post('/chat/message', data, { timeout: 180000 }).then(r => r.data),
  getHistory: (userId) => api.get(`/chat/history/${userId}`).then(r => r.data),
  startOnboarding: (data) => api.post('/chat/onboarding/start', data).then(r => r.data),
  finalizeOnboarding: (data) => api.post('/chat/onboarding/finalize', data).then(r => r.data),

  // SSE streaming for the general assistant chat. Calls onToken(text) as the
  // reply streams, onDone(payload) at the end, onError(err) on hard failure.
  // The action-capable Agent 2 path emits a `fallback` event, which this helper
  // transparently routes to the structured /chat/message endpoint.
  streamMessage: async ({ user_id, message }, { onToken, onDone, onError } = {}) => {
    const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
    const userId = useAuthStore.getState().userId;
    const token = useAuthStore.getState().token;
    const headers = { 'Content-Type': 'application/json' };
    if (userId) headers['X-User-Id'] = userId;
    if (token) headers['Authorization'] = `Bearer ${token}`;

    let resp;
    try {
      resp = await fetch(`${baseURL}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ user_id, message }),
      });
    } catch (err) {
      return onError && onError(err);
    }
    if (!resp.ok || !resp.body) {
      return onError && onError(new Error(`stream HTTP ${resp.status}`));
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let doneData = null;
    let fellBack = false;

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let sep;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          let evt = 'message';
          let dataStr = '';
          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) evt = line.slice(6).trim();
            else if (line.startsWith('data:')) dataStr += line.slice(5).trim();
          }
          if (!dataStr) continue;
          let payload;
          try { payload = JSON.parse(dataStr); } catch { continue; }
          if (evt === 'fallback') fellBack = true;
          else if (evt === 'done') doneData = payload;
          else if (payload.delta && onToken) onToken(payload.delta);
        }
      }
    } catch (err) {
      return onError && onError(err);
    }

    if (fellBack) {
      try {
        const res = await api.post('/chat/message', { user_id, message }).then(r => r.data);
        return onDone && onDone(res);
      } catch (err) {
        return onError && onError(err);
      }
    }
    return onDone && onDone(doneData || {});
  },
};

// ── Resume API ──
export const resumeAPI = {
  // Get current resume or null
  get: (userId) => api.get(`/resume/${userId}`).then(r => r.data),
  // Generate resume from Delta profile
  generate: (userId) => api.post(`/resume/${userId}/generate`).then(r => r.data),
  // Upload existing PDF/DOCX
  upload: (userId, formData) => api.post(`/resume/${userId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data),
  // Fetch bi-weekly suggestions
  getSuggestions: (userId) => api.get(`/resume/${userId}/suggestions`).then(r => r.data),
  // Apply accepted/rejected suggestions
  applySuggestions: (userId, data) => api.post(`/resume/${userId}/apply-suggestions`, data).then(r => r.data),
  // Download .docx binary (returns blob)
  download: (userId) => api.get(`/resume/${userId}/download`, { responseType: 'blob' }).then(r => r.data),
  // ATS optimize in-place
  atsOptimize: (userId) => api.post(`/resume/${userId}/ats-optimize`).then(r => r.data),
};

// ── Calendar API ──
export const calendarAPI = {
  getEvents: (userId) => api.get(`/calendar/events?user_id=${userId}`).then(r => r.data),
  getSources: () => api.get('/calendar/sources').then(r => r.data),
};

// ── Dossier API ──
export const dossierAPI = {
  getWeekly: (userId) => api.get(`/dossier/weekly/${userId}`).then(r => r.data),
};

export const careerOSAPI = {
  getSystemStatus: () => api.get('/career-os/system-status').then(r => r.data),
  getDomainPacks: () => api.get('/career-os/domain-packs').then(r => r.data),
  getDomainPack: (domainId) => api.get(`/career-os/domain-packs/${domainId}`).then(r => r.data),
  // Planning a week runs as a background job (see lib/backgroundJobs.js), so these return quickly.
  getContext: (userId) => api.get(`/career-os/user/${userId}/context`).then(r => r.data),
  initialize: (userId, data) => api.post(`/career-os/user/${userId}/initialize`, data).then(r => r.data),
  runWeeklyCycle: (userId) => api.post(`/career-os/user/${userId}/weekly-cycle`, {}).then(r => r.data),
  consolidateMemory: (userId) => api.post(`/career-os/user/${userId}/consolidate-memory`).then(r => r.data),
  logJourneyEvent: (userId, data) => api.post(`/career-os/user/${userId}/journey`, data).then(r => r.data),
  getTaskDetail: (userId, data) => api.post(`/career-os/user/${userId}/task-detail`, data, { timeout: 60000 }).then(r => r.data),
  getContextDocs: (userId) => api.get(`/career-os/user/${userId}/context-docs`).then(r => r.data),
  updateContextDocs: (userId, data) => api.put(`/career-os/user/${userId}/context-docs`, data).then(r => r.data),
  updateWeeklyTasks: (userId, tasks) => api.put(`/career-os/user/${userId}/weekly-tasks`, { tasks }).then(r => r.data),
  setPlanStyle: (userId, planStyle, daySchedule) => api.put(`/career-os/user/${userId}/plan-style`, { plan_style: planStyle, day_schedule: daySchedule }, { timeout: 120000 }).then(r => r.data),
  getDayPlan: (userId) => api.get(`/career-os/user/${userId}/day-plan`, { timeout: 120000 }).then(r => r.data),
  saveDayPlan: (userId, dayPlan) => api.put(`/career-os/user/${userId}/day-plan`, { day_plan: dayPlan }).then(r => r.data),
  advanceExpiredWeek: (userId, carriedTaskIds) => api.post(`/career-os/user/${userId}/advance-expired-week`, { carried_task_ids: carriedTaskIds }).then(r => r.data),
};

// ── Opportunities API (AI-matched jobs & internships) ──
export const opportunitiesAPI = {
  get: (userId) => api.get(`/opportunities/${userId}`).then(r => r.data),
  updatePreferences: (userId, prefs) => api.put(`/opportunities/${userId}/preferences`, prefs).then(r => r.data),
  // AI generation can take several seconds — allow a generous timeout.
  generate: (userId) => api.post(`/opportunities/${userId}/generate`, {}, { timeout: 120000 }).then(r => r.data),
};

// ── Achievements API (trophy cabinet) ──
export const achievementsAPI = {
  list: (userId) => api.get(`/achievements/${userId}`).then(r => r.data),
  create: (userId, data) => api.post(`/achievements/${userId}`, data).then(r => r.data),
  remove: (userId, achievementId) => api.delete(`/achievements/${userId}/${achievementId}`).then(r => r.data),
};

// ── Coding Sandbox API ──
export const sandboxCodingAPI = {
  getProblems: (userId) => api.get(`/sandbox/coding/${userId}/problems`).then(r => r.data),
  startProblem: (userId, topic, problemId) => api.post(`/sandbox/coding/${userId}/problems/start`, { topic, problem_id: problemId }, { timeout: 60000 }).then(r => r.data),
  run: (userId, sessionId, language, code, stdin = '') => api.post(`/sandbox/coding/${userId}/sessions/${sessionId}/run`, { language, code, stdin }, { timeout: 30000 }).then(r => r.data),
  submit: (userId, sessionId, language, code, integrity) => api.post(`/sandbox/coding/${userId}/sessions/${sessionId}/submit`, { language, code, integrity }, { timeout: 60000 }).then(r => r.data),
  getSessions: (userId) => api.get(`/sandbox/coding/${userId}/sessions`).then(r => r.data),
};

// ── Mock Interview Sandbox API ──
export const sandboxInterviewAPI = {
  // opts: { role_type, target_role, difficulty, num_questions }
  start: (userId, opts) => api.post(`/sandbox/interview/${userId}/start`, opts, { timeout: 60000 }).then(r => r.data),
  respond: (userId, sessionId, answer) => api.post(`/sandbox/interview/${userId}/sessions/${sessionId}/respond`, { answer }, { timeout: 60000 }).then(r => r.data),
  // The report is one long LLM call on the backend (up to 120s + one retry): don't give up first.
  finish: (userId, sessionId, integrity) => api.post(`/sandbox/interview/${userId}/sessions/${sessionId}/finish`, { integrity }, { timeout: 150000 }).then(r => r.data),
  avatar: (userId) => api.get(`/sandbox/interview/${userId}/avatar`).then(r => r.data),
  tts: (userId, text, voice) => api.post(`/sandbox/interview/${userId}/tts`, { text, voice }, { timeout: 20000 }).then(r => r.data),
  getSessions: (userId) => api.get(`/sandbox/interview/${userId}/sessions`).then(r => r.data),
  getSession: (userId, sessionId) => api.get(`/sandbox/interview/${userId}/sessions/${sessionId}`).then(r => r.data),
};

// ── Technical Theory Test Sandbox API ──
// ── Daily habit: streak, XP, goal, break mode, reminders ──
export const backgroundJobsAPI = {
  get: (jobId) => api.get(`/background-jobs/${jobId}`).then(r => r.data),
};

export const engagementAPI = {
  // tz: the browser's timezone, used the first time to set up the account.
  get: (userId, tz) => api.get(`/engagement/${userId}`, { params: tz ? { tz } : {} }).then(r => r.data),
  update: (userId, data) => api.put(`/engagement/${userId}`, data).then(r => r.data),
  startBreak: (userId, days) => api.post(`/engagement/${userId}/break`, { days }).then(r => r.data),
  endBreak: (userId) => api.delete(`/engagement/${userId}/break`).then(r => r.data),
  setReminders: (userId, enabled, channel) => api.put(`/engagement/${userId}/reminders`, { enabled, channel }).then(r => r.data),
  pushKey: () => api.get('/engagement/push/public-key').then(r => r.data),
  addPush: (userId, subscription) => api.post(`/engagement/${userId}/push`, subscription).then(r => r.data),
  removePush: (userId, endpoint) => api.delete(`/engagement/${userId}/push`, { data: { endpoint } }).then(r => r.data),
  unsubscribe: (u, t) => api.post('/engagement/unsubscribe', { u, t }).then(r => r.data),
  badges: (userId) => api.get(`/engagement/${userId}/badges`).then(r => r.data),
  usage: (userId) => api.get(`/engagement/usage/${userId}`).then(r => r.data),
  adminAiUsage: () => api.get('/engagement/admin/ai-usage').then(r => r.data),
  league: (userId) => api.get(`/engagement/${userId}/league`).then(r => r.data),
  setLeague: (userId, enabled) => api.put(`/engagement/${userId}/league`, { enabled }).then(r => r.data),
  shareBadge: (userId, key) => api.post(`/engagement/${userId}/badges/${key}/share`).then(r => r.data),
  unshareBadge: (userId, key) => api.delete(`/engagement/${userId}/badges/${key}/share`).then(r => r.data),
  referrals: (userId) => api.get(`/engagement/${userId}/referrals`).then(r => r.data),
  referralPreview: (userId, code) => api.get(`/engagement/${userId}/referrals/preview/${encodeURIComponent(code)}`).then(r => r.data),
  claimReferral: (userId, code) => api.post(`/engagement/${userId}/referrals/claim`, { code }).then(r => r.data),
};

// ── Job match: paste a job ad -> gaps -> tasks ──
// ── Predefined role roadmaps (no AI; a college may assign one) ──
export const templatesAPI = {
  catalog: () => api.get('/templates').then(r => r.data),
  mine: (userId) => api.get(`/templates/user/${userId}`).then(r => r.data),
  outline: (templateId) => api.get(`/templates/${templateId}`).then(r => r.data),
  start: (userId, template_id, target_date) => api.post(`/templates/user/${userId}/start`, { template_id, target_date: target_date || null }).then(r => r.data),
  stop: (userId) => api.post(`/templates/user/${userId}/stop`).then(r => r.data),
};

export const jobsAPI = {
  list: (userId) => api.get(`/jobs/${userId}`).then(r => r.data),
  // The first read of a new ad calls the model: allow time.
  analyse: (userId, text) => api.post(`/jobs/${userId}/analyse`, { text }, { timeout: 90000 }).then(r => r.data),
  get: (userId, id) => api.get(`/jobs/${userId}/${id}`).then(r => r.data),
  addToWeek: (userId, id, skills) => api.post(`/jobs/${userId}/${id}/add-to-week`, { skills }).then(r => r.data),
  plan: (userId, id, on) => api.post(`/jobs/${userId}/${id}/plan`, { on }).then(r => r.data),
  remove: (userId, id) => api.delete(`/jobs/${userId}/${id}`).then(r => r.data),
};

// ── Public, no-login pages ──
export const publicAPI = {
  badge: (token) => api.get(`/public/badges/${encodeURIComponent(token)}`).then(r => r.data),
  parentConsent: (token) => api.get(`/public/parent-consent/${encodeURIComponent(token)}`).then(r => r.data),
  parentRespond: (token, grant, isGuardian) => api.post(`/public/parent-consent/${encodeURIComponent(token)}`, { grant, is_guardian: isGuardian }).then(r => r.data),
};

// ── Study circles (opt-in private groups) ──
export const circlesAPI = {
  list: (userId) => api.get(`/circles/${userId}`).then(r => r.data),
  create: (userId, name) => api.post(`/circles/${userId}`, { name }).then(r => r.data),
  preview: (userId, code) => api.get(`/circles/${userId}/preview/${encodeURIComponent(code)}`).then(r => r.data),
  join: (userId, code) => api.post(`/circles/${userId}/join`, { code }).then(r => r.data),
  leave: (userId, circleId) => api.delete(`/circles/${userId}/${circleId}`).then(r => r.data),
  removeMember: (userId, circleId, memberId) => api.delete(`/circles/${userId}/${circleId}/members/${memberId}`).then(r => r.data),
  newCode: (userId, circleId) => api.post(`/circles/${userId}/${circleId}/new-code`).then(r => r.data),
};

// ── Quick 5: the daily 5-question spaced review ──
export const quickPracticeAPI = {
  // The first set for a new topic may be written by the model: allow time.
  get: (userId) => api.get(`/practice/quick/${userId}`, { timeout: 90000 }).then(r => r.data),
  answer: (userId, itemId, choice) => api.post(`/practice/quick/${userId}/answer`, { item_id: itemId, choice }).then(r => r.data),
};

export const sandboxTheoryAPI = {
  // opts: { topic, num_questions, difficulty, category, area, timed }
  start: (userId, opts) => api.post(`/sandbox/theory/${userId}/start`, opts, { timeout: 90000 }).then(r => r.data),
  submit: (userId, sessionId, answers, integrity) => api.post(`/sandbox/theory/${userId}/sessions/${sessionId}/submit`, { answers, integrity }, { timeout: 30000 }).then(r => r.data),
  getSessions: (userId) => api.get(`/sandbox/theory/${userId}/sessions`).then(r => r.data),
  getSession: (userId, sessionId) => api.get(`/sandbox/theory/${userId}/sessions/${sessionId}`).then(r => r.data),
  suggestions: (userId) => api.get(`/sandbox/theory/${userId}/suggestions`).then(r => r.data),
};

// ── Test Center readiness report ──
export const sandboxReportAPI = {
  get: (userId) => api.get(`/sandbox/report/${userId}`).then(r => r.data),
};

// ── Privacy / DPDP API (student's own consent + data rights) ──
export const privacyAPI = {
  minorStart: (userId, payload) => api.post(`/privacy/${userId}/minor-start`, payload).then(r => r.data),
  resendParentConsent: (userId) => api.post(`/privacy/${userId}/parent-consent/resend`).then(r => r.data),
  getConsent: (userId) => api.get(`/privacy/${userId}/consent`).then(r => r.data),
  setConsent: (userId, payload) => api.post(`/privacy/${userId}/consent`, payload).then(r => r.data),
  getProfileViews: (userId) => api.get(`/privacy/${userId}/profile-views`).then(r => r.data),
  exportData: (userId) => api.get(`/privacy/${userId}/export`, { timeout: 60000 }).then(r => r.data),
  deleteAccount: (userId) => api.delete(`/privacy/${userId}`, { data: { confirm: 'DELETE' }, timeout: 60000 }).then(r => r.data),
};

// ── Recruiter portal API (identity comes from the auth token, no user id in path) ──
// ── Company roadmaps: recruiters build them, Delta admins review, students follow ──
export const companyAPI = {
  draftFromSkills: (skills, weeks) => api.post('/company/drafts/skills', { skills, weeks }).then(r => r.data),
  // The first read of a new ad calls the model: allow time.
  draftFromText: (text, weeks) => api.post('/company/drafts/text', { text, weeks }, { timeout: 90000 }).then(r => r.data),
  list: () => api.get('/company/roadmaps').then(r => r.data),
  create: (payload) => api.post('/company/roadmaps', payload).then(r => r.data),
  get: (id) => api.get(`/company/roadmaps/${id}`).then(r => r.data),
  update: (id, payload) => api.patch(`/company/roadmaps/${id}`, payload).then(r => r.data),
  submit: (id) => api.post(`/company/roadmaps/${id}/submit`).then(r => r.data),
  archive: (id) => api.post(`/company/roadmaps/${id}/archive`).then(r => r.data),
  duplicate: (id) => api.post(`/company/roadmaps/${id}/duplicate`).then(r => r.data),
  students: (id) => api.get(`/company/roadmaps/${id}/students`).then(r => r.data),
  studentsCsv: (id) => api.get(`/company/roadmaps/${id}/students.csv`, { responseType: 'blob' }).then(r => r.data),
  tests: (id) => api.get(`/company/roadmaps/${id}/tests`).then(r => r.data),
  // Making a test calls the model once: allow time.
  createTest: (id, payload) => api.post(`/company/roadmaps/${id}/tests`, payload, { timeout: 120000 }).then(r => r.data),
  closeTest: (testId) => api.post(`/company/tests/${testId}/close`).then(r => r.data),
  adminQueue: () => api.get('/company/admin/roadmaps').then(r => r.data),
  adminReview: (id, approve, note) => api.post(`/company/admin/roadmaps/${id}/review`, { approve, note: note || null }).then(r => r.data),
  visible: (userId) => api.get(`/company/student/${userId}/roadmaps`).then(r => r.data),
  join: (userId, roadmapId) => api.post(`/company/student/${userId}/roadmaps/${roadmapId}/join`).then(r => r.data),
  leave: (userId, roadmapId) => api.post(`/company/student/${userId}/roadmaps/${roadmapId}/leave`).then(r => r.data),
  studentTests: (userId) => api.get(`/company/student/${userId}/tests`).then(r => r.data),
};

export const recruiterAPI = {
  me: () => api.get('/recruiter/me').then(r => r.data),
  register: (payload) => api.post('/recruiter/register', payload).then(r => r.data),
  savePreferences: (prefs) => api.put('/recruiter/preferences', prefs).then(r => r.data),
  search: (prefs) => api.post('/recruiter/search', prefs).then(r => r.data),
  candidate: (studentId) => api.get(`/recruiter/candidates/${studentId}`).then(r => r.data),
  deleteAccount: () => api.delete('/recruiter/me').then(r => r.data),
  adminList: (status = 'pending') => api.get('/recruiter/admin/recruiters', { params: { status } }).then(r => r.data),
  adminReview: (recruiterId, approve, pool) => api.post(`/recruiter/admin/recruiters/${recruiterId}/review`, { approve, pool }).then(r => r.data),
};

// ── Delta for College: platform admin, college staff, and the student side ──
export const collegeAPI = {
  // platform admin (ADMIN_EMAILS)
  adminList: () => api.get('/college/admin/colleges').then(r => r.data),
  adminCreate: (payload) => api.post('/college/admin/colleges', payload).then(r => r.data),
  adminUpdate: (id, payload) => api.patch(`/college/admin/colleges/${id}`, payload).then(r => r.data),
  // staff
  me: () => api.get('/college/me').then(r => r.data),
  accept: (policy_version) => api.post('/college/me/accept', { policy_version }).then(r => r.data),
  get: (cid) => api.get(`/college/${cid}`).then(r => r.data),
  team: (cid) => api.get(`/college/${cid}/admins`).then(r => r.data),
  invite: (cid, email, role) => api.post(`/college/${cid}/admins`, { email, role }).then(r => r.data),
  removeStaff: (cid, id) => api.delete(`/college/${cid}/admins/${id}`).then(r => r.data),
  batches: (cid) => api.get(`/college/${cid}/batches`).then(r => r.data),
  createBatch: (cid, payload) => api.post(`/college/${cid}/batches`, payload).then(r => r.data),
  updateBatch: (cid, bid, payload) => api.patch(`/college/${cid}/batches/${bid}`, payload).then(r => r.data),
  rotateCode: (cid, bid) => api.post(`/college/${cid}/batches/${bid}/join-code`).then(r => r.data),
  importRoster: (cid, payload) => api.post(`/college/${cid}/roster`, payload, { timeout: 120000 }).then(r => r.data),
  members: (cid, params) => api.get(`/college/${cid}/members`, { params }).then(r => r.data),
  approve: (cid, mid) => api.post(`/college/${cid}/members/${mid}/approve`).then(r => r.data),
  removeMember: (cid, mid) => api.delete(`/college/${cid}/members/${mid}`).then(r => r.data),
  recruiters: (cid) => api.get(`/college/${cid}/recruiters`).then(r => r.data),
  linkRecruiter: (cid, email) => api.post(`/college/${cid}/recruiters`, { email }).then(r => r.data),
  revokeRecruiter: (cid, id) => api.delete(`/college/${cid}/recruiters/${id}`).then(r => r.data),
  overview: (cid) => api.get(`/college/${cid}/overview`).then(r => r.data),
  setBatchTemplate: (cid, bid, template_id, target_date) => api.put(`/college/${cid}/batches/${bid}/template`, { template_id, target_date: target_date || null }).then(r => r.data),
  batchTests: (cid, bid) => api.get(`/college/${cid}/batches/${bid}/tests`).then(r => r.data),
  // Making a test calls the model once: allow time.
  createTest: (cid, bid, payload) => api.post(`/college/${cid}/batches/${bid}/tests`, payload, { timeout: 120000 }).then(r => r.data),
  closeTest: (cid, aid) => api.post(`/college/${cid}/tests/${aid}/close`).then(r => r.data),
  testResults: (cid, aid) => api.get(`/college/${cid}/tests/${aid}/results`).then(r => r.data),
  studentTests: (userId) => api.get(`/college/student/${userId}/tests`).then(r => r.data),
  batchDashboard: (cid, bid) => api.get(`/college/${cid}/batches/${bid}/dashboard`).then(r => r.data),
  student: (cid, userId) => api.get(`/college/${cid}/students/${userId}`).then(r => r.data),
  exportCsv: (cid, kind, params) => api.get(`/college/${cid}/exports/${kind}.csv`, { params, responseType: 'blob', timeout: 120000 }).then(r => r.data),
  // students
  studentState: (userId) => api.get(`/college/student/${userId}`).then(r => r.data),
  preview: (code) => api.get(`/college/join/${encodeURIComponent(code)}/preview`).then(r => r.data),
  join: (userId, payload) => api.post(`/college/student/${userId}/join`, payload).then(r => r.data),
  leave: (userId) => api.post(`/college/student/${userId}/leave`).then(r => r.data),
};

// ── Delta for School API (children live under the parent's account) ──
export const schoolAPI = {
  listChildren: (userId) => api.get(`/school/${userId}/children`).then(r => r.data),
  addChild: (userId, payload) => api.post(`/school/${userId}/children`, payload).then(r => r.data),
  removeChild: (userId, childId) => api.delete(`/school/${userId}/children/${childId}`).then(r => r.data),
  verifyPin: (userId, childId, pin) => api.post(`/school/${userId}/children/${childId}/verify-pin`, { pin }).then(r => r.data),
  childHome: (userId, childId) => api.get(`/school/${userId}/children/${childId}`).then(r => r.data),
  lesson: (userId, childId, subject, chapterNo) => api.get(`/school/${userId}/children/${childId}/lessons/${subject}/${chapterNo}`).then(r => r.data),
  submitQuiz: (userId, childId, subject, chapterNo, answers) => api.post(`/school/${userId}/children/${childId}/lessons/${subject}/${chapterNo}/submit`, { answers }).then(r => r.data),
  reviewerMe: () => api.get('/school/review/me').then(r => r.data),
  reviewChapters: (grade, subject) => api.get(`/school/review/${grade}/${subject}`).then(r => r.data),
  reviewGenerate: (grade, subject, chapterNo) => api.post(`/school/review/${grade}/${subject}/${chapterNo}/generate`, {}, { timeout: 120000 }).then(r => r.data),
  reviewGet: (lessonId) => api.get(`/school/review/lessons/${lessonId}`).then(r => r.data),
  reviewSave: (lessonId, content, quiz) => api.put(`/school/review/lessons/${lessonId}`, { content, quiz }).then(r => r.data),
  reviewApprove: (lessonId) => api.post(`/school/review/lessons/${lessonId}/approve`).then(r => r.data),
  reviewReject: (lessonId) => api.post(`/school/review/lessons/${lessonId}/reject`).then(r => r.data),
};

// ── Ingestion API ──
export const ingestionAPI = {
  start: (userId, journeyType) => api.post('/ingestion/start', { user_id: userId, journey_type: journeyType }).then(r => r.data),
  submitAnswer: (userId, sessionId, answer) => api.post('/ingestion/answer', { user_id: userId, session_id: sessionId, answer }).then(r => r.data),
  editAnswer: (userId, sessionId, round, answer) => api.post('/ingestion/edit-answer', { user_id: userId, session_id: sessionId, round, answer }).then(r => r.data),
  ingestResume: (userId, sessionId, resumeText) => api.post('/ingestion/resume', { user_id: userId, session_id: sessionId, resume_text: resumeText }).then(r => r.data),
  getState: (userId) => api.get(`/ingestion/state/${userId}`).then(r => r.data),
  getProfile: (userId) => api.get(`/ingestion/profile/${userId}`).then(r => r.data),
  updateProfile: (userId, updates) => api.put(`/ingestion/profile/${userId}`, updates).then(r => r.data),
  bridge: (userId, rawText, source) => api.post('/ingestion/bridge', { user_id: userId, raw_text: rawText, source }).then(r => r.data),
  forceComplete: (userId) => api.post(`/ingestion/complete/${userId}`).then(r => r.data),
  resetProfile: (userId) => api.post(`/ingestion/reset/${userId}`).then(r => r.data),
};

export default api;
