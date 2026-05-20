# Delta 2.0 Recovery Specification

> **CONTEXT**: During a git operation, all files created by the AI agent were lost from disk.
> The base project files (package.json, tailwind.config.js, index.css, node_modules, shadcn ui components, delta.db) survived.
> This document provides full code and detailed specs to recreate everything.

---

## Architecture Overview

**Delta** is a career intelligence platform for Indian students post-12th grade.
- **Backend**: FastAPI + SQLAlchemy + SQLite (`delta.db` already exists with seeded data)
- **Frontend**: React 18 + Tailwind CSS + Framer Motion + Lucide React icons + React Hot Toast + Zustand + React Query + React Router v6
- **Theme**: Cyberpunk dark UI with glassmorphism, HUD-style typography, emerald/purple/cyan accents

## Database Schema (already in delta.db)

```sql
-- Users table
users(id TEXT PK, email TEXT, name TEXT, current_role TEXT, years_experience INT,
      target_role TEXT, hours_per_week INT, learning_style TEXT, created_at, updated_at)

-- Skill nodes (user's capabilities)
skill_nodes(id TEXT PK, user_id TEXT FK, name TEXT, category TEXT, proficiency INT 1-10,
            evidence_type TEXT [claimed|resume|github|certification|verified],
            evidence_weight FLOAT, evidence_url TEXT, last_updated, created_at)

-- Delta scores (weekly computed career score 0-100)
delta_scores(id TEXT PK, user_id TEXT FK, score FLOAT, score_date DATE,
             skill_snapshot JSON, market_snapshot_id TEXT, created_at)

-- Weekly briefs (AI-generated weekly growth plans)
weekly_briefs(id TEXT PK, user_id TEXT FK, week_start DATE,
              delta_score_start FLOAT, delta_score_end FLOAT,
              recommendations JSON, email_sent_at, created_at)

-- Recommendations (individual action items from briefs)
recommendations(id TEXT PK, brief_id TEXT FK, user_id TEXT FK, skill TEXT,
                resource_title TEXT, resource_url TEXT, resource_type TEXT,
                estimated_hours FLOAT, market_signal_text TEXT,
                projected_delta_impact FLOAT, evidence_collection_path TEXT,
                status TEXT [pending|in_progress|completed], completed_at,
                evidence_type TEXT, evidence_url TEXT, user_rating INT,
                was_relevant BOOL, created_at)

-- Market snapshots (external market demand data)
market_snapshots(id TEXT PK, user_id TEXT FK, target_role TEXT, snapshot_date DATE,
                 top_demanded_skills JSON, emerging_skills JSON, raw_data JSON,
                 confidence_score FLOAT, created_at)

-- Personalization profiles
personalization_profiles(id TEXT PK, user_id TEXT FK, raw_intake JSON,
                         structured_profile JSON, ai_questions_asked JSON,
                         last_updated, created_at)
```

**Seeded guest user**: `id = '00000000-0000-0000-0000-000000000000'`, name = "Guest Pro", target_role = "AI Developer / Software Engineer"

---

## File Tree (ALL files to recreate)

```
delta/
├── docker-compose.yml
├── backend/
│   ├── .gitignore
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── seed_guest.py
│   ├── check_db.py
│   ├── app/
│   │   ├── __init__.py (empty)
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py (imports all models)
│   │   │   ├── user.py
│   │   │   ├── skill_node.py
│   │   │   ├── delta_score.py
│   │   │   ├── weekly_brief.py
│   │   │   ├── recommendation.py
│   │   │   ├── market_snapshot.py
│   │   │   └── personalization.py
│   │   ├── routers/
│   │   │   ├── users.py
│   │   │   ├── skills.py
│   │   │   ├── briefs.py
│   │   │   ├── chat.py
│   │   │   └── resume.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── skill.py
│   │   │   ├── brief.py
│   │   │   ├── delta.py
│   │   │   ├── market.py
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── brief_generator.py
│   │   │   ├── delta_score.py
│   │   │   ├── email_service.py
│   │   │   ├── market_pulse.py
│   │   │   ├── onboarding_pipeline.py
│   │   │   ├── resume_parser.py
│   │   │   └── search_service.py
│   │   └── tasks/
│   │       ├── celery_app.py
│   │       ├── weekly_brief.py
│   │       └── weekly_pulse.py
│   ├── migrations/
│   │   ├── README
│   │   ├── env.py
│   │   └── script.py.mako
│   └── tests/
│       ├── test_ai_service.py
│       └── test_market_pulse.py
├── frontend/src/
│   ├── components/
│   │   ├── PekkaRunner.jsx          ★ FULL CODE BELOW
│   │   ├── RoadmapTree.jsx          ★ FULL CODE BELOW
│   │   ├── EvidenceModal.jsx
│   │   ├── Dashboard/
│   │   │   ├── Dashboard.jsx        ★ FULL CODE BELOW
│   │   │   ├── DashboardConnected.jsx
│   │   │   ├── DeltaScoreCard.jsx
│   │   │   ├── DeltaScoreChart.jsx
│   │   │   ├── SkillRadar.jsx
│   │   │   ├── WeeklyBriefCard.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── CareerChat.jsx
│   │   ├── Onboarding/
│   │   │   ├── CareerChat.jsx
│   │   │   ├── ResumeDragDrop.jsx
│   │   │   ├── SkillConfirmation.jsx
│   │   │   └── OnboardingComplete.jsx
│   │   └── ui/
│   │       ├── GlassPanel.jsx
│   │       ├── Navbar.jsx
│   │       └── AnimatedNumber.jsx
│   ├── hooks/
│   │   ├── useChat.js
│   │   ├── useScore.js
│   │   └── useUser.js
│   ├── lib/
│   │   └── api.js
│   ├── store/
│   │   ├── authStore.js
│   │   └── deltaStore.js
│   └── pages/
│       ├── Landing.jsx
│       ├── Portfolio.jsx
│       ├── Calendar.jsx
│       └── FeaturePages.jsx
```

Also need to UPDATE (not recreate) these existing files:
- `frontend/src/App.js` — Add React Router with routes for all pages
- `frontend/src/index.css` — Add cyberpunk theme utilities, glassmorphism, HUD styles
- `frontend/tailwind.config.js` — Add custom colors (primary-500 = indigo), font config
- `frontend/package.json` — Add dependencies: framer-motion, react-router-dom, zustand, @tanstack/react-query, react-hot-toast, axios, recharts

---

## KEY DEPENDENCY ADDITIONS (for package.json)

```json
{
  "dependencies": {
    "framer-motion": "^11.0.0",
    "react-router-dom": "^6.0.0",
    "zustand": "^4.5.0",
    "@tanstack/react-query": "^5.0.0",
    "react-hot-toast": "^2.4.0",
    "axios": "^1.6.0",
    "recharts": "^2.12.0"
  }
}
```

---

## FULL CODE: frontend/src/components/ui/GlassPanel.jsx

```jsx
import React from 'react';
import { motion } from 'framer-motion';

export default function GlassPanel({ children, className = '', hover = true, ...props }) {
  return (
    <motion.div
      className={`rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6 ${className}`}
      whileHover={hover ? { borderColor: 'rgba(255,255,255,0.1)', scale: 1.002 } : {}}
      transition={{ duration: 0.3 }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
```

---

## FULL CODE: frontend/src/components/ui/Navbar.jsx

```jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Zap, LayoutDashboard, BookOpen, FileText, TrendingUp,
  CalendarDays, FolderOpen, User, Bell
} from 'lucide-react';

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Career AI', path: '/chat', icon: Zap },
  { label: 'Ledger', path: '/ledger', icon: BookOpen },
  { label: 'Briefs', path: '/briefs', icon: FileText },
  { label: 'Pulse', path: '/pulse', icon: TrendingUp },
  { label: 'Calendar', path: '/calendar', icon: CalendarDays },
  { label: 'Dossier', path: '/portfolio', icon: FolderOpen },
  { label: 'Profile', path: '/profile', icon: User },
];

export default function Navbar({ user }) {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-2 text-white font-black italic text-xl uppercase tracking-tighter">
          <Zap className="text-primary-400 fill-primary-400/30" size={20} />
          DELTA
        </Link>

        <div className="flex items-center gap-1">
          {navItems.map(({ label, path, icon: Icon }) => {
            const isActive = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                className={`relative px-3 py-2 rounded-lg text-[10px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5 transition-all duration-300 ${
                  isActive
                    ? 'text-white bg-primary-500/10 border border-primary-500/20'
                    : 'text-slate-500 hover:text-slate-300 border border-transparent'
                }`}
              >
                <Icon size={12} />
                {label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500">
              {user?.name || 'Guest'}
            </p>
            <p className="text-[8px] font-mono text-primary-400 uppercase">
              {user?.target_role || 'No Target Set'}
            </p>
          </div>
          <button className="relative p-2 rounded-lg bg-white/5 border border-white/5 text-slate-400 hover:text-white transition-colors">
            <Bell size={14} />
          </button>
          <div className="w-8 h-8 rounded-full bg-primary-500/20 border border-primary-500/30 flex items-center justify-center text-primary-400 text-xs font-bold">
            {(user?.name || 'G')[0]}
          </div>
        </div>
      </div>
    </nav>
  );
}
```

---

## FULL CODE: frontend/src/store/authStore.js

```js
import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  userId: '00000000-0000-0000-0000-000000000000',
  setUserId: (id) => set({ userId: id }),
}));
```

---

## FULL CODE: frontend/src/lib/api.js

```js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
});

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
  send: (data) => api.post('/chat/message', data).then(r => r.data),
  getHistory: (userId) => api.get(`/chat/history/${userId}`).then(r => r.data),
};

// ── Resume API ──
export const resumeAPI = {
  upload: (formData) => api.post('/resume/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data),
};

export default api;
```

---

## FULL CODE: frontend/src/hooks/useUser.js

```js
import { useQuery } from '@tanstack/react-query';
import { usersAPI } from '../lib/api';

export function useUserWithSkills(userId) {
  return useQuery({
    queryKey: ['user', userId],
    queryFn: () => usersAPI.getWithSkills(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useUserStats(userId) {
  return useQuery({
    queryKey: ['userStats', userId],
    queryFn: () => usersAPI.getStats(userId),
    enabled: !!userId,
    staleTime: 30000,
    select: (data) => ({
      role_alignment: data.role_alignment || 0,
      evidence_density: data.evidence_density || 0,
      market_pulse: data.market_pulse || 'N/A',
      gaps: data.gaps || [],
    }),
  });
}
```

---

## FULL CODE: frontend/src/hooks/useScore.js

```js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { briefsAPI } from '../lib/api';

export function useCurrentScore(userId) {
  return useQuery({
    queryKey: ['currentScore', userId],
    queryFn: () => briefsAPI.getCurrentScore(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useScoreHistory(userId) {
  return useQuery({
    queryKey: ['scoreHistory', userId],
    queryFn: () => briefsAPI.getScoreHistory(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useLatestBrief(userId) {
  return useQuery({
    queryKey: ['latestBrief', userId],
    queryFn: () => briefsAPI.getLatest(userId),
    enabled: !!userId,
    staleTime: 30000,
  });
}

export function useCompleteRecommendation(userId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ recId, evidenceUrl, evidenceType }) =>
      briefsAPI.completeRecommendation(recId, {
        evidence_url: evidenceUrl,
        evidence_type: evidenceType,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['latestBrief', userId] });
      queryClient.invalidateQueries({ queryKey: ['currentScore', userId] });
      queryClient.invalidateQueries({ queryKey: ['scoreHistory', userId] });
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      queryClient.invalidateQueries({ queryKey: ['userStats', userId] });
    },
  });
}
```

---

## DETAILED SPECS FOR REMAINING FILES

### Backend: app/main.py
FastAPI app with CORS middleware (allow all origins for dev). Include routers: users, skills, briefs, chat, resume. On startup, run `Base.metadata.create_all()` and seed the guest user if not exists. Import from local models/routers/database modules.

### Backend: app/config.py
Pydantic BaseSettings class with DATABASE_URL (default: sqlite:///./delta.db), GEMINI_API_KEY (from env), and CORS_ORIGINS.

### Backend: app/database.py
SQLAlchemy setup with `create_engine(DATABASE_URL, connect_args={"check_same_thread": False})`, `SessionLocal`, and `Base = declarative_base()`. Include `get_db()` dependency generator.

### Backend: app/models/*.py
SQLAlchemy models matching the database schema above. Each model in its own file. `__init__.py` imports all models so `Base.metadata` knows about them.

### Backend: app/routers/users.py
CRUD endpoints: GET `/users/{user_id}`, GET `/users/{user_id}/with-skills` (eager load skills), PUT `/users/{user_id}`, GET `/users/{user_id}/stats` (computes role_alignment, evidence_density, market_pulse, gaps from market_snapshot vs user skills).

### Backend: app/routers/skills.py
CRUD for skill nodes: GET `/skills/{user_id}`, POST `/skills`, PUT `/skills/{skill_id}`, POST `/skills/{skill_id}/verify`.

### Backend: app/routers/briefs.py
GET `/briefs/user/{user_id}/latest` (latest brief with recommendations populated), POST `/briefs/generate/{user_id}` (creates a new brief with 3 recommendations), GET `/briefs/scores/{user_id}/current`, GET `/briefs/scores/{user_id}/history`, POST `/briefs/recommendations/{rec_id}/complete`.

### Backend: app/routers/chat.py
POST `/chat/message` (accepts {user_id, message}, returns AI response), GET `/chat/history/{user_id}`.

### Backend: app/schemas/*.py
Pydantic v2 models for request/response serialization matching the DB models.

### Backend: app/services/ai_service.py
Wrapper around Google Gemini API (using `google.generativeai`). Has `generate_response(prompt)` function. Falls back to a mock response if no API key.

### Backend: app/services/brief_generator.py
Generates weekly briefs: fetches user skills, market snapshot, computes gaps, creates 3 recommendations with resources. Uses AI service for recommendation text.

### Backend: app/services/delta_score.py
Computes delta score (0-100) based on: skill count, evidence weights, market alignment, evidence diversity.

### Backend: seed_guest.py
Script that creates the guest user, 5 skill nodes (Python proficiency=8 github, React proficiency=6 resume, FastAPI proficiency=7 github, SQL proficiency=5 claimed, Docker proficiency=3 claimed), a market snapshot with top_demanded_skills=["LLMs","Docker","System Design","Kubernetes","MLOps"], a delta score of 42.5, and a weekly brief with 3 recommendations.

### Frontend: Dashboard/DashboardConnected.jsx
Wrapper that uses hooks (useUserWithSkills, useCurrentScore, useScoreHistory, useLatestBrief, useUserStats) and passes data to Dashboard component. Shows loading spinner while data loads.

### Frontend: Dashboard/DeltaScoreCard.jsx
Large card showing current delta score as an animated number (0-100), sparkline chart of score history using Recharts, and delta change indicator.

### Frontend: Dashboard/SkillRadar.jsx
SVG-based radar/spider chart showing user's skills by category with proficiency levels.

### Frontend: Dashboard/WeeklyBriefCard.jsx
Card for each recommendation showing: skill name, resource_title, resource_url, resource_type badge, estimated_hours, market_signal_text, projected_delta_impact, and a "Verify & Complete" button that calls onComplete prop.

### Frontend: EvidenceModal.jsx
Modal (AnimatePresence + motion.div) with form: evidence_url input, evidence_type select (github/certification/resume/portfolio), submit button. Calls onVerify prop with form data.

### Frontend: pages/Landing.jsx
Premium landing page with hero section, features grid, how it works, and CTA. Links to /dashboard and /chat.

### Frontend: pages/Calendar.jsx
Opportunities calendar showing upcoming events from Kaggle, Codeforces, LeetCode, Unstop, hackathons. Uses a grid layout with date cards.

### Frontend: pages/Portfolio.jsx
Portfolio/dossier page showing user's journey log, completed recommendations, evidence items, and overall progress.

### Frontend: pages/FeaturePages.jsx
Placeholder pages for /ledger, /briefs, /pulse, /profile routes. Each shows a GlassPanel with the page title and "coming soon" or basic content.

### Frontend: App.js (UPDATE existing)
Add BrowserRouter, Routes for: / (Landing), /dashboard (DashboardConnected), /chat (CareerChat from Onboarding), /ledger, /briefs, /pulse, /calendar, /portfolio, /profile (from FeaturePages). Wrap with QueryClientProvider and Toaster.

### Frontend: index.css (UPDATE existing)
Add custom utilities: `.bg-grid-pattern` (subtle dot grid), `.scan-line` (animated scanline), `.mesh-gradient-1`, `.mesh-gradient-emerald`, `.hud-badge` (tiny pill badge style), `.scrollbar-hide`.

### Frontend: tailwind.config.js (UPDATE existing)
Add `primary` color scale (based on indigo: primary-400=#818cf8, primary-500=#6366f1, primary-600=#4f46e5). Extend with custom animations.

---

## FULL CODE: PekkaRunner.jsx, RoadmapTree.jsx, Dashboard.jsx

These three files are the most complex. Their FULL source code is available in the conversation transcript at:
`C:\Users\Shank\.gemini\antigravity\brain\4f21622f-03cf-46c8-8bbe-13da88260556\.system_generated\logs\transcript.jsonl`

Search for `write_to_file` calls targeting these paths:
- `PekkaRunner.jsx` — ~580 lines, Chrome-dino-style side-scrolling game with parallax layers
- `RoadmapTree.jsx` — ~560 lines, Dynamic 16-node skill tree with real resource URLs
- `Dashboard.jsx` — ~318 lines, Main dashboard layout integrating all widgets

The transcript contains the EXACT file contents that were written. Use `grep "PekkaRunner" transcript.jsonl` to find them.

---

## CRITICAL INTEGRATION NOTES

1. The `delta.db` SQLite database already exists at `backend/delta.db` with all tables and seeded guest data. Do NOT delete it.
2. Backend runs on port 8000: `python -m uvicorn app.main:app --port 8000`
3. Frontend runs on port 3000: `npm start` (uses craco)
4. Frontend proxy is NOT configured — API calls go directly to `http://localhost:8000/api` via axios
5. The guest user ID is `00000000-0000-0000-0000-000000000000` — hardcoded in `authStore.js`
6. All icons come from `lucide-react` — verify icon names exist before importing (e.g., `Swords` and `GraduationCap` do NOT exist in the installed version)
