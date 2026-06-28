import axios from 'axios';
import { useAuthStore } from '../store/authStore';

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

// Automatically handle expired or invalid JWT sessions
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.warn("Session expired or invalid, logging out...");
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
  getContext: (userId) => api.get(`/career-os/user/${userId}/context`).then(r => r.data),
  initialize: (userId, data) => api.post(`/career-os/user/${userId}/initialize`, data).then(r => r.data),
  runWeeklyCycle: (userId) => api.post(`/career-os/user/${userId}/weekly-cycle`, {}, { timeout: 300000 }).then(r => r.data),
  consolidateMemory: (userId) => api.post(`/career-os/user/${userId}/consolidate-memory`).then(r => r.data),
  logJourneyEvent: (userId, data) => api.post(`/career-os/user/${userId}/journey`, data).then(r => r.data),
  getTaskDetail: (userId, data) => api.post(`/career-os/user/${userId}/task-detail`, data, { timeout: 60000 }).then(r => r.data),
  getContextDocs: (userId) => api.get(`/career-os/user/${userId}/context-docs`).then(r => r.data),
  updateContextDocs: (userId, data) => api.put(`/career-os/user/${userId}/context-docs`, data).then(r => r.data),
  updateWeeklyTasks: (userId, tasks) => api.put(`/career-os/user/${userId}/weekly-tasks`, { tasks }).then(r => r.data),
};

// ── Ingestion API ──
export const ingestionAPI = {
  start: (userId, journeyType) => api.post('/ingestion/start', { user_id: userId, journey_type: journeyType }).then(r => r.data),
  submitAnswer: (userId, sessionId, answer) => api.post('/ingestion/answer', { user_id: userId, session_id: sessionId, answer }).then(r => r.data),
  ingestResume: (userId, sessionId, resumeText) => api.post('/ingestion/resume', { user_id: userId, session_id: sessionId, resume_text: resumeText }).then(r => r.data),
  getState: (userId) => api.get(`/ingestion/state/${userId}`).then(r => r.data),
  getProfile: (userId) => api.get(`/ingestion/profile/${userId}`).then(r => r.data),
  updateProfile: (userId, updates) => api.put(`/ingestion/profile/${userId}`, updates).then(r => r.data),
  bridge: (userId, rawText, source) => api.post('/ingestion/bridge', { user_id: userId, raw_text: rawText, source }).then(r => r.data),
  forceComplete: (userId) => api.post(`/ingestion/complete/${userId}`).then(r => r.data),
  resetProfile: (userId) => api.post(`/ingestion/reset/${userId}`).then(r => r.data),
};

export default api;
