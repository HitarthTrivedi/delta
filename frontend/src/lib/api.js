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
  getContext: (userId) => api.get(`/career-os/user/${userId}/context`, { timeout: 300000 }).then(r => r.data),
  initialize: (userId, data) => api.post(`/career-os/user/${userId}/initialize`, data).then(r => r.data),
  runWeeklyCycle: (userId) => api.post(`/career-os/user/${userId}/weekly-cycle`, {}, { timeout: 300000 }).then(r => r.data),
  consolidateMemory: (userId) => api.post(`/career-os/user/${userId}/consolidate-memory`).then(r => r.data),
  logJourneyEvent: (userId, data) => api.post(`/career-os/user/${userId}/journey`, data).then(r => r.data),
  getTaskDetail: (userId, data) => api.post(`/career-os/user/${userId}/task-detail`, data, { timeout: 60000 }).then(r => r.data),
  getContextDocs: (userId) => api.get(`/career-os/user/${userId}/context-docs`).then(r => r.data),
  updateContextDocs: (userId, data) => api.put(`/career-os/user/${userId}/context-docs`, data).then(r => r.data),
  updateWeeklyTasks: (userId, tasks) => api.put(`/career-os/user/${userId}/weekly-tasks`, { tasks }).then(r => r.data),
  setPlanStyle: (userId, planStyle, daySchedule) => api.put(`/career-os/user/${userId}/plan-style`, { plan_style: planStyle, day_schedule: daySchedule }, { timeout: 120000 }).then(r => r.data),
  getDayPlan: (userId) => api.get(`/career-os/user/${userId}/day-plan`, { timeout: 120000 }).then(r => r.data),
  saveDayPlan: (userId, dayPlan) => api.put(`/career-os/user/${userId}/day-plan`, { day_plan: dayPlan }).then(r => r.data),
  advanceExpiredWeek: (userId, carriedTaskIds) => api.post(`/career-os/user/${userId}/advance-expired-week`, { carried_task_ids: carriedTaskIds }, { timeout: 300000 }).then(r => r.data),
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
  submit: (userId, sessionId, language, code) => api.post(`/sandbox/coding/${userId}/sessions/${sessionId}/submit`, { language, code }, { timeout: 60000 }).then(r => r.data),
  getSessions: (userId) => api.get(`/sandbox/coding/${userId}/sessions`).then(r => r.data),
};

// ── Mock Interview Sandbox API ──
export const sandboxInterviewAPI = {
  // opts: { role_type, target_role, difficulty, num_questions }
  start: (userId, opts) => api.post(`/sandbox/interview/${userId}/start`, opts, { timeout: 60000 }).then(r => r.data),
  respond: (userId, sessionId, answer) => api.post(`/sandbox/interview/${userId}/sessions/${sessionId}/respond`, { answer }, { timeout: 60000 }).then(r => r.data),
  finish: (userId, sessionId) => api.post(`/sandbox/interview/${userId}/sessions/${sessionId}/finish`, {}, { timeout: 60000 }).then(r => r.data),
  getSessions: (userId) => api.get(`/sandbox/interview/${userId}/sessions`).then(r => r.data),
  getSession: (userId, sessionId) => api.get(`/sandbox/interview/${userId}/sessions/${sessionId}`).then(r => r.data),
};

// ── Technical Theory Test Sandbox API ──
export const sandboxTheoryAPI = {
  // opts: { topic, num_questions, difficulty, category, area, timed }
  start: (userId, opts) => api.post(`/sandbox/theory/${userId}/start`, opts, { timeout: 90000 }).then(r => r.data),
  submit: (userId, sessionId, answers) => api.post(`/sandbox/theory/${userId}/sessions/${sessionId}/submit`, { answers }, { timeout: 30000 }).then(r => r.data),
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
  getConsent: (userId) => api.get(`/privacy/${userId}/consent`).then(r => r.data),
  setConsent: (userId, payload) => api.post(`/privacy/${userId}/consent`, payload).then(r => r.data),
  getProfileViews: (userId) => api.get(`/privacy/${userId}/profile-views`).then(r => r.data),
  exportData: (userId) => api.get(`/privacy/${userId}/export`, { timeout: 60000 }).then(r => r.data),
  deleteAccount: (userId) => api.delete(`/privacy/${userId}`, { data: { confirm: 'DELETE' }, timeout: 60000 }).then(r => r.data),
};

// ── Recruiter portal API (identity comes from the auth token, no user id in path) ──
export const recruiterAPI = {
  me: () => api.get('/recruiter/me').then(r => r.data),
  register: (payload) => api.post('/recruiter/register', payload).then(r => r.data),
  savePreferences: (prefs) => api.put('/recruiter/preferences', prefs).then(r => r.data),
  search: (prefs) => api.post('/recruiter/search', prefs).then(r => r.data),
  candidate: (studentId) => api.get(`/recruiter/candidates/${studentId}`).then(r => r.data),
  deleteAccount: () => api.delete('/recruiter/me').then(r => r.data),
  adminList: (status = 'pending') => api.get('/recruiter/admin/recruiters', { params: { status } }).then(r => r.data),
  adminReview: (recruiterId, approve) => api.post(`/recruiter/admin/recruiters/${recruiterId}/review`, { approve }).then(r => r.data),
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
