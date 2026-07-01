# Delta 2.0 — Complete System Documentation

> **The single "read this to understand the whole system" document.** It covers
> what Delta is, everything it has, what each part does, and how it does it —
> product, features, architecture, data, AI pipeline, security, and operations.
>
> Companion docs:
> - [ARCHITECTURE.md](./ARCHITECTURE.md) — condensed technical reference (layers, data model, API tables, caching).
> - [DELTA_CAREER_OS_BLUEPRINT.md](./DELTA_CAREER_OS_BLUEPRINT.md) — the product vision and the ten pillars.
> - [../README.md](../README.md) — local setup and run instructions.
> - [PRIVACY_POLICY.md](./PRIVACY_POLICY.md) / [TERMS_OF_SERVICE.md](./TERMS_OF_SERVICE.md) — legal documents (DPDP Act, India).

**Last updated:** 2026-07-02 · **Version:** 2.0.0

---

## Table of contents

1. [What Delta is](#1-what-delta-is)
2. [The core idea & the Weekly Loop](#2-the-core-idea--the-weekly-loop)
3. [System at a glance](#3-system-at-a-glance)
4. [Technology stack](#4-technology-stack)
5. [Repository layout](#5-repository-layout)
6. [Feature catalogue — what it has and what each does](#6-feature-catalogue--what-it-has-and-what-each-does)
7. [Backend architecture — how it works](#7-backend-architecture--how-it-works)
8. [The Central AI Engine & AI pipeline](#8-the-central-ai-engine--ai-pipeline)
9. [Semantic memory & the Career Memory Profile](#9-semantic-memory--the-career-memory-profile)
10. [Data model — every table and blob](#10-data-model--every-table-and-blob)
11. [Complete API reference](#11-complete-api-reference)
12. [Frontend architecture](#12-frontend-architecture)
13. [Authentication, authorization & security](#13-authentication-authorization--security)
14. [Performance & caching](#14-performance--caching)
15. [External integrations & data flows](#15-external-integrations--data-flows)
16. [Configuration & environment variables](#16-configuration--environment-variables)
17. [Deployment & operations](#17-deployment--operations)
18. [Personal-data map (for privacy/DPDP)](#18-personal-data-map-for-privacydpdp)
19. [Conventions & non-negotiables](#19-conventions--non-negotiables)

---

## 1. What Delta is

**Delta 2.0** (branded **"Delta by Alpha.Kore"**) is a **Career Intelligence
platform / Career Operating System** for students and early-career
professionals. It converts a person's messy, invisible career situation into a
**living, personalized, week-by-week plan** driven by **AI + live market
signals**.

The premise: most students don't fail from lack of motivation — they fail
because *the path ahead is invisible*. Delta makes the path visible, keeps it
current with the real job market, and turns it into concrete weekly action with
proof-of-work.

It is a web application:

- a **React single-page app** (the product surface + a public marketing site), and
- a **FastAPI backend** exposing career, skills, chat, resume, calendar,
  dossier, onboarding, opportunities, achievements, reminders and weekly-brief
  APIs — all orchestrated through a **Central AI Engine**.

---

## 2. The core idea & the Weekly Loop

Delta is built around a repeating **Weekly Loop**. Every cycle:

1. **Read the user's memory** — the structured Career Memory Profile + journey history.
2. **Pull market signals** — live data on roles, skills, and opportunities.
3. **Compare** — where the user is vs. where the market/role demands.
4. **Update the roadmap** — long-term phases and the current week's focus.
5. **Generate this week's plan + a brief** — concrete tasks and a written summary.

Between cycles, the user works tasks, chats with **Agent 2** (the weekly-planning
assistant), logs progress, and everything they do feeds back into memory for the
next cycle. This loop is the heart of the product; almost every feature is a
window into some stage of it.

---

## 3. System at a glance

```
┌───────────────────────── Browser (Vercel) ─────────────────────────┐
│  React SPA:  marketing site + product pages                         │
│  • Zustand auth store (Supabase session, persisted to localStorage) │
│  • TanStack React Query (server-state cache)                        │
│  • Axios client → attaches X-User-Id + Bearer JWT on every request  │
└───────────────┬──────────────────────────────────┬─────────────────┘
                │ HTTPS (Axios/fetch + JWT)          │ session
                ▼                                    ▼
┌─────────── FastAPI backend (Railway) ───────────┐  ┌── Supabase Auth ──┐
│  Routers /api/*  (thin, owner-scoped)           │  │ email/pw + Google  │
│        │                                        │  │ OAuth; issues JWT  │
│        ▼                                        │  └────────────────────┘
│  Central AI Engine (orchestration)              │
│        │                                        │
│        ├─► Services (market, brief, resume,     │        ┌───────────────┐
│        │   memory graph, opportunities, …)      │──LLM──►│ Google Gemini │
│        │                                        │        └───────────────┘
│        ├─► SQLAlchemy (sync) ──► SQLite / Postgres        ┌──────────────┐
│        └─► Cache (Redis + in-process fallback) │──fetch──►│ Web / market │
└─────────────────────────────────────────────────┘        │ GitHub, jobs,│
                                                            │ Serper/Tavily│
                                                            └──────────────┘
```

Every feature routes through the **Central AI Engine**, which reads memory +
market context + journey history *before* generating anything.

---

## 4. Technology stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Create React App + CRACO, React Router 7, Tailwind CSS 3, Radix UI (design system in `components/ui/*`), Axios, Zustand 5 (auth), TanStack React Query 5, Framer Motion, Recharts, sonner (toasts), lucide-react (icons) |
| **Backend** | Python 3.11, FastAPI 0.110, Uvicorn, **synchronous** SQLAlchemy 2.x, Pydantic 2 / pydantic-settings, slowapi (rate limiting) |
| **Database** | SQLite (local, sync driver, WAL mode); PostgreSQL in production (Supabase-hosted; `psycopg2-binary`) |
| **Auth** | Supabase (email/password + Google OAuth); backend verifies Supabase JWTs (PyJWT + cryptography, HS256 or ES256/RS256 via JWKS) |
| **AI / LLM** | Google Gemini via `google-genai`. Default model `gemma-4-31b-it` for everything; `gemini-2.5-flash` **only** for resume analysis |
| **Embeddings** | Local, deterministic **hash-based mock** (384-dim). `sentence-transformers` was removed to fit the 512 MB Render tier — no embedding data leaves the server |
| **Web search** | Tavily / Serper with a provider waterfall → mock fallback |
| **Cache** | Redis (optional) with in-process `cachetools.TTLCache` fallback (fail-open) |
| **Email** | Gmail SMTP (daily task reminders) |
| **Deploy** | Frontend → Vercel; Backend → Railway (Docker, `python:3.11-slim`, dynamic `$PORT`; previously Render); DB → Supabase Postgres |

> **Two hard constraints** (see [§19](#19-conventions--non-negotiables)): the
> backend is **synchronous** SQLAlchemy end-to-end (no async engine), and the
> **AI model selection is fixed** — do not change models without explicit approval.

---

## 5. Repository layout

```text
delta/
├── backend/                      # FastAPI application
│   ├── app/
│   │   ├── main.py               # App entry: middleware, routers, startup migrations, warmup
│   │   ├── config.py             # Settings (self-healing .env loader, all env vars)
│   │   ├── database.py           # Sync SQLAlchemy engine/session, SQLite pragmas, pooling
│   │   ├── limiter.py            # slowapi rate limiter
│   │   ├── dependencies/auth.py  # JWT verification + resource-ownership guard (require_owner)
│   │   ├── routers/              # HTTP endpoints, one module per domain
│   │   ├── services/             # Business logic + integrations (the engine + all pillars)
│   │   ├── models/               # SQLAlchemy ORM models
│   │   └── schemas/              # Pydantic request/response schemas
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # React (CRA + CRACO) SPA
│   ├── src/
│   │   ├── App.js                # Routes, QueryClient, auth gating, code-splitting
│   │   ├── pages/                # Route pages (Dashboard, WeeklyPlan, Opportunities, …)
│   │   ├── components/           # Landing components + ui/ (Radix design system)
│   │   ├── hooks/                # React Query hooks (useUser, useScore, useChat, …)
│   │   ├── store/                # Zustand stores (authStore, agent2ChatStore)
│   │   └── lib/api.js            # Axios instance + typed API method groups
│   └── vercel.json               # SPA rewrite (all routes → index.html)
├── docs/                         # This file + architecture + blueprint + legal docs
├── data/                         # Local dev artifacts (agent2 memory JSONL, sample profile)
├── docker-compose.yml
└── README.md
```

---

## 6. Feature catalogue — what it has and what each does

This is the full user-facing surface. Each feature lists **what it does** and
**how it does it** (the code path behind it).

### 6.1 Public marketing site
- **What:** Landing page, About, Careers, Contact, Partners, Investors, Early
  Access, Privacy, Terms. Public, no auth.
- **How:** `frontend/src/components/*` (Hero, Showcase, HowItWorks, Feedback,
  Footer) and `pages/*Page.jsx`, code-split via `React.lazy`.

### 6.2 Authentication & "smart" login
- **What:** Email/password and Google OAuth sign-in; sessions persist across
  reloads; expired sessions auto-log-out and redirect to `/login`.
- **How:** Supabase client (`lib/supabaseClient.js`) + Zustand `store/authStore.js`.
  On boot, `initializeAuth()` syncs `getSession()` and subscribes to auth
  changes. The Axios response interceptor catches `401` → `logout()` → redirect.

### 6.3 Adaptive onboarding (Agent 1)
- **What:** A conversational intake ("adaptive ingestion") that builds a rich
  profile instead of a static form. It asks tailored questions, can ingest a
  resume, detects goal/exam tracks, and enriches with web search.
- **How:** `services/ingestion_engine_v2.py` + `services/onboarding_pipeline.py`,
  exposed by `routers/ingestion.py` and `routers/chat.py`
  (`/chat/onboarding/start`, `/finalize`). Output is persisted as the structured
  profile (`users.profile_data`) via `services/profile_store.py`.

### 6.4 Dashboard
- **What:** The home surface after onboarding — role alignment, gaps, Delta
  Score, this week's focus, quick stats and optimistic task actions.
- **How:** `pages/Dashboard.jsx` pulls `users/{id}/stats`, career context,
  score, and brief. Task actions optimistically refresh only stats + context
  (not all dashboard calls) for perceived speed.

### 6.5 Weekly Plan / Roadmap + Agent 2 chat
- **What:** The current week's tasks and the long-term roadmap, alongside a
  **persistent chat with Agent 2** (the weekly-planning assistant) that can
  explain tasks, adjust the plan, add/adjust tasks, schedule events, and answer
  questions. Chat state survives navigation.
- **How:** `pages/WeeklyPlan.jsx` + `store/agent2ChatStore.js` (Zustand, keeps
  chat history in the client). Backend: `routers/chat.py` with two paths —
  `/chat/message` (structured, action-capable Agent 2) and `/chat/stream`
  (SSE token streaming for the general assistant, with graceful fallback to
  `/chat/message`). Roadmap/week state lives in `RoadmapState`.

### 6.6 Weekly cycle, briefs & dossier
- **What:** The automated Weekly Loop — regenerate market context, update the
  roadmap, produce this week's plan and a written **weekly brief** + **dossier**.
- **How:** `central_engine.run_weekly_career_cycle` orchestrates
  `services/market_pulse.py`, `services/brief_generator.py`,
  `services/dossier_generator.py`. Briefs stored in `weekly_briefs`; exposed by
  `routers/briefs.py` and `routers/dossier.py`. Rate-limited (5/hr).

### 6.7 Market Pulse
- **What:** Weekly live market signals for the user's role — trending skills,
  demand, and opportunities.
- **How:** `services/market_pulse.py` fans out **in parallel** to GitHub,
  StackExchange, job boards (Arbeitnow), web search, and opportunity adapters,
  then caches the role-scoped snapshot for 12h. Stored in `market_snapshots`.

### 6.8 Delta Score & progress report
- **What:** A single score tracking career readiness/alignment over time, plus a
  progress report view.
- **How:** `services/delta_score.py`, stored in `delta_scores`; history exposed
  via `/briefs/scores/{id}/history`. UI in `pages/ProgressReport.jsx`.

### 6.9 Resume engine
- **What:** Generate a resume from the Delta profile, upload an existing PDF/DOCX
  to parse, get bi-weekly improvement suggestions, ATS-optimize, and download a
  `.docx`.
- **How:** `services/resume_parser.py` (extract text + skills from PDF/DOCX;
  LLM-structure via **`gemini-2.5-flash`**) and `services/resume_service.py`
  (generate, suggest, ATS-optimize, export). Stored in `resume_profiles`
  (`raw_text` + `structured_data` + `ats_score`). **The uploaded file itself is
  not retained** after parsing — only extracted text/structure.

### 6.10 Opportunities board *(new)*
- **What:** An **AI-matched jobs & internships** board. The user sets
  preferences (location, role types, work mode, industries, notes); Delta
  suggests role-level opportunities that fit them *now* and get better as their
  profile improves, each with a real job-search deeplink. The board flags itself
  as "stale" when the profile changes enough to be worth regenerating.
- **How:** `models/opportunity_board.py` (per-user, unique), `routers/opportunities.py`
  (get/update-preferences/generate), `services/opportunity_ai.py` (LLM matcher).
  Suggestions are role-level with target-company profiles (not fabricated live
  postings) and carry a **LinkedIn jobs search URL** built from the role +
  location — no user data is sent to LinkedIn; the user clicks through. A
  `profile_signature` (SHA-1 of fit-relevant profile fields) detects staleness.
  UI: `pages/Opportunities.jsx`.

### 6.11 Trophy Cabinet / Achievements *(new)*
- **What:** A place to manually track certificates, projects, awards, courses,
  and other accomplishments (title, issuer/org, date, URL, description).
- **How:** `models/achievement.py`, `routers/achievements.py` (owner-scoped CRUD).
  UI: `pages/TrophyCabinet.jsx` (route `/achievements`).

### 6.12 Calendar
- **What:** Aggregated upcoming events/deadlines and source statuses.
- **How:** `services/calendar_service.py`, `routers/calendar.py`
  (`/calendar/events`, `/calendar/sources`). UI in `pages/FeaturePages.jsx` (Calendar).

### 6.13 Daily email reminders
- **What:** A daily email nudging users with tasks still pending this week.
- **How:** `routers/reminders.py` `POST /reminders/daily` (protected by an
  `X-Reminder-Secret` header), called once/day by a cron job (Render Cron /
  cron-job.org). It iterates users with an active roadmap and pending weekly
  tasks and sends HTML email via **Gmail SMTP** (`services/email_service.py`).

### 6.14 Feedback
- **What:** In-app feedback submission.
- **How:** `routers/feedback.py`, stored in `feedbacks`.

### 6.15 Supplementary feature pages
- **What:** Ledger, Briefs, Pulse, Portfolio, Profile views.
- **How:** `pages/FeaturePages.jsx` (named exports mapped to lazy routes).

---

## 7. Backend architecture — how it works

The backend is a **layered FastAPI app**:

```
Routers  →  Central AI Engine  →  Services  →  Models / DB
(HTTP)      (orchestration)       (logic +      (SQLAlchemy)
                                   integrations)
```

- **Routers** (`app/routers/*`) — thin HTTP handlers. They validate input with
  Pydantic, enforce ownership with `Depends(require_owner)`, and delegate to
  services. **All handlers are synchronous `def`** and run in Starlette's
  threadpool.
- **Central AI Engine** (`services/central_engine.py`) — the orchestration core;
  assembles memory + market + journey and drives the other services (see [§8](#8-the-central-ai-engine--ai-pipeline)).
- **Services** (`app/services/*`) — focused units of business logic and external
  integration (one per pillar/subsystem).
- **Models** (`app/models/*`) — SQLAlchemy ORM tables.
- **Schemas** (`app/schemas/*`) — Pydantic request/response shapes.

**Cross-cutting infrastructure:**

| Concern | Where |
|---------|-------|
| LLM access (Gemini, key rotation, timeout) | `services/ai_service.py`, `services/http_client.py` |
| Caching (Redis + fallback) | `services/cache.py` |
| Parallel external calls | `services/parallel.py` |
| Embeddings / semantic graph | `services/memory_graph.py`, `models/semantic_memory.py` |
| Auth / ownership | `dependencies/auth.py` |
| Rate limiting | `limiter.py` (`/briefs/generate` 5/hr, `/chat/message` 20/min) |
| CORS + GZip | `main.py` |
| Startup table sync + idempotent migrations + warmup | `main.py` `startup()` |

**Startup (`main.py`):** creates all tables (`Base.metadata.create_all`), runs
idempotent column migrations (`profile_data`, `agent2_memory_data`), creates
composite indexes (`idx_market_user_date`, `idx_journey_user_created`), and warms
the embedding + cache in a background thread so the first real request is fast.

### The ten system pillars → code map

| # | Pillar | Primary code |
|---|--------|--------------|
| 1 | **Adaptive Ingestion** — AI onboarding, not static forms | `ingestion_engine_v2.py`, `onboarding_pipeline.py`, `routers/ingestion.py` |
| 2 | **Personal Data Vault** — structured per-user profile | `profile_store.py`, `agent2_memory.py`, `models/career_os.py` (`CareerMemoryProfile`) |
| 3 | **Central AI Engine** — all features route through here | `central_engine.py`, `ai_service.py`, `orchestrator.py` |
| 4 | **Market Pulse** — weekly live market signals | `market_pulse.py`, `web_search.py`, `opportunity_adapters.py`, `search_service.py` |
| 5 | **Roadmap** — long-term phases + this week | `central_engine.get_or_create_roadmap_state`, `models/career_os.py` (`RoadmapState`) |
| 6 | **Journey Until Today** — full history log | `models/career_os.py` (`JourneyEvent`), `central_engine.log_journey_event` |
| 7 | **Weekly Loop** — automated weekly cycle | `central_engine.run_weekly_career_cycle`, `brief_generator.py`, `dossier_generator.py` |
| 8 | **Projects As Proof** — proof-oriented project recs | `project_engine.py` |
| 9 | **Portfolio Assessment** — weekly gap analysis | `portfolio_engine.py` |
| 10 | **Domain Packs** — per-domain taxonomies | `domain_packs.py` |

**Supporting subsystems:** semantic memory graph (`memory_graph.py`,
`memory_consolidation.py`, `tension_resolver.py`, `models/semantic_memory.py`),
Delta Score (`delta_score.py`), resume engine (`resume_parser.py`,
`resume_service.py`), calendar (`calendar_service.py`), ideal frames
(`ideal_frames.py`), user-context store (`user_context_store.py`).

---

## 8. The Central AI Engine & AI pipeline

`services/central_engine.py` is the orchestration core. Key entry points:

- `initialize_career_os_for_user` — first-run setup (build memory + roadmap from profile + market).
- `run_weekly_career_cycle` — the full Weekly Loop (heaviest path: market + LLM).
- `compile_career_context` — assemble the full context blob the UI reads.
- `get_or_create_roadmap_state` — long-term phases + this week's focus.
- `log_journey_event` — append to the append-only history.
- `run_memory_consolidation_cycle` — periodic memory cleanup/consolidation.

**LLM access (`services/ai_service.py`):**
- All generation goes through Google **Gemini** via `google-genai`.
- Up to **5 API keys** are used in round-robin; on `429`/quota errors the client
  **rotates** to the next key.
- Calls are bounded by a **60s timeout** so a hung call fails fast.
- **Model policy:** `gemma-4-31b-it` is the default for *everything* (roadmaps,
  Agent 2 chat, onboarding, memory consolidation, market analysis, opportunity
  matching); **`gemini-2.5-flash` is used only for resume analysis**
  (`resume_parser.parse_resume_llm`, `resume_service`). See [§19](#19-conventions--non-negotiables).
- Streaming: `generate_response_stream` powers the SSE chat path.

**What context the AI receives:** the compiled career context (profile, skills,
goals, constraints, journey history, current roadmap, market snapshot). For
opportunity matching and resume work, the profile is flattened to a text block
(`profile_store.profile_as_context_string`) and sent in the prompt.

---

## 9. Semantic memory & the Career Memory Profile

Delta keeps two complementary representations of "what it knows about you":

1. **Career Memory Profile** (`CareerMemoryProfile`) — a structured snapshot with
   `identity`, `ambitions`, `capabilities`, `constraints`, `preferences`,
   `behavior`, `evidence`, `open_questions`, a `confidence_score`, and active
   `tension_nodes`. This is the "Data Vault."

2. **Semantic memory graph** (`memory_graph.py`, `models/semantic_memory.py`) —
   nodes and edges representing facts and their relationships, plus **tension
   nodes** (detected contradictions, e.g., "wants X but constrained by Y").
   Nodes carry **vector embeddings** for similarity search.

**Embeddings note:** embeddings are currently a **deterministic local mock**
(`np.random.seed(hash(text))` → 384-dim vector). `sentence-transformers` was
removed to fit the 512 MB Render free tier. This means similarity is
approximate, but crucially **no text is sent anywhere to compute embeddings** —
it's all in-process. The real-model path (with 30-day embedding cache) is still
in the code and re-activates if a model is restored.

**Consolidation & tensions:** `memory_consolidation.py` periodically merges/cleans
memory; `tension_resolver.py` surfaces and resolves contradictions so the
roadmap stays coherent.

---

## 10. Data model — every table and blob

Sync SQLAlchemy ORM; tables auto-created on startup. Most tables key off
`user_id` (FK → `users.id`).

| Table | Model file | Role | Key columns |
|-------|-----------|------|-------------|
| `users` | `user.py` | Account + serialized profile blobs | `id`, `email`, `name`, `current_role`, `years_experience`, `target_role`, `hours_per_week`, `learning_style`, `profile_data` (JSON text), `agent2_memory_data` (JSON text), timestamps |
| `career_memory_profiles` | `career_os.py` | Structured Career Memory Profile (Data Vault) | `user_id` **unique**; identity/ambitions/capabilities/constraints/preferences/behavior/evidence/open_questions (JSON), `confidence_score`, `tension_nodes` |
| `roadmap_states` | `career_os.py` | Current roadmap (phases + this week) | `user_id` **unique**; `destination`, `phases`, `active_phase_id`, `weekly_focus`, `resource_graph`, `proof_requirements` (JSON) |
| `journey_events` | `career_os.py` | Append-only history (tasks, moods, AI decisions) | `user_id` (idx), `event_type`, `summary`, `evidence`, `impact`, `event_date`, `created_at` |
| `resume_profiles` | `career_os.py` | Generated/parsed resume state | `user_id` **unique**; `raw_text`, `structured_data` (JSON), `ats_score`, `source` |
| `market_snapshots` | `market_snapshot.py` | Per-user market pulse snapshot | `user_id` (idx), `snapshot_date` |
| `recommendations` | `recommendation.py` | Proof-project / action recommendations | `user_id` (idx), `status` |
| `delta_scores` | `delta_score.py` | Delta Score history | `user_id` (idx), `created_at` |
| `weekly_briefs` | `weekly_brief.py` | Generated weekly briefs | `user_id` (idx), `created_at` |
| `skill_nodes` | `skill_node.py` | User's skills | `user_id` (idx) |
| `personalization_profiles` | `personalization.py` | Personalization settings | `user_id` **unique** |
| `opportunity_boards` *(new)* | `opportunity_board.py` | AI-matched jobs board | `user_id` **unique**; `preferences`, `opportunities` (JSON), `profile_signature`, `generated_at` |
| `achievements` *(new)* | `achievement.py` | Trophy-cabinet entries | `user_id` (idx), `type`, `title`, `organization`, `date_achieved`, `url`, `description` |
| `feedbacks` | `feedback.py` | User feedback submissions | `created_at` |
| `semantic_nodes` / `semantic_edges` / `tension_nodes` | `semantic_memory.py` | Embedding-backed memory graph + tensions | `user_id` (idx) |
| `ingestion_sessions` | `semantic_memory.py` | Onboarding/ingestion session state | `user_id` (idx) |

**The two big JSON blobs on `users`:**
- `profile_data` — the full onboarding intake profile (see the field list in
  [§18](#18-personal-data-map-for-privacydpdp)). This is the single source of
  truth that all agents read via `profile_store.py`.
- `agent2_memory_data` — Agent 2's working memory/context (current week, chat
  notes, upcoming events, progress log).

**Composite indexes** (idempotent on startup): `idx_market_user_date`
(`market_snapshots`) and `idx_journey_user_created` (`journey_events`).

---

## 11. Complete API reference

All routes are under `/api`. Owner-scoped routes require **both**
`X-User-Id: <uuid>` and `Authorization: Bearer <supabase-jwt>` and are guarded by
`require_owner` ([§13](#13-authentication-authorization--security)).

| Router | Method | Path | Purpose |
|--------|--------|------|---------|
| **users** | GET | `/users/{user_id}` | Get user |
| | GET | `/users/{user_id}/with-skills` | User + skills (Navbar/profile) |
| | PUT | `/users/{user_id}` | Update user |
| | GET | `/users/{user_id}/stats` | Dashboard stats |
| **skills** | GET | `/skills/{user_id}` | List skills |
| | POST | `/skills` | Create skill |
| | PUT | `/skills/{skill_id}` | Update skill |
| | POST | `/skills/{skill_id}/verify` | Verify skill |
| **briefs** | GET | `/briefs/user/{user_id}/latest` | Latest weekly brief |
| | POST | `/briefs/generate/{user_id}` | Generate brief *(LLM; 5/hr)* |
| | GET | `/briefs/scores/{user_id}/current` | Current Delta Score |
| | GET | `/briefs/scores/{user_id}/history` | Score history |
| | POST | `/briefs/recommendations/{rec_id}/complete` | Mark recommendation done |
| **chat** | POST | `/chat/message` | Agent 2 chat / weekly actions *(LLM; 20/min)* |
| | POST | `/chat/stream` | SSE token streaming (general assistant) |
| | GET | `/chat/history/{user_id}` | Chat history |
| | POST | `/chat/onboarding/start` · `/finalize` | Onboarding chat |
| **career-os** | GET | `/career-os/domain-packs` · `/domain-packs/{id}` | Domain packs |
| | GET | `/career-os/system-status` | System status |
| | GET | `/career-os/user/{id}/context` · `/context-docs` | Compiled context / context docs |
| | PUT | `/career-os/user/{id}/context-docs` · `/weekly-tasks` | Update context docs / tasks |
| | POST | `/career-os/user/{id}/initialize` | Initialize Career OS *(LLM + market)* |
| | POST | `/career-os/user/{id}/weekly-cycle` | Run Weekly Loop *(heaviest; LLM + market)* |
| | POST | `/career-os/user/{id}/journey` | Log a journey event |
| | POST | `/career-os/user/{id}/task-detail` | Task detail (LLM) |
| | POST | `/career-os/user/{id}/consolidate-memory` | Memory consolidation |
| **ingestion** | POST | `/ingestion/start` · `/answer` · `/resume` · `/bridge` · `/complete/{id}` · `/reset/{id}` | Adaptive ingestion pipeline |
| | GET/PUT | `/ingestion/state/{id}` · `/profile/{id}` | Ingestion state/profile |
| **resume** | GET | `/resume/{user_id}` · `/suggestions` · `/download` | Get / suggestions / export |
| | POST | `/resume/{user_id}/generate` · `/upload` · `/apply-suggestions` · `/ats-optimize` | Generation/parsing *(LLM)* |
| **opportunities** *(new)* | GET | `/opportunities/{user_id}` | Stored preferences + last board (no LLM) |
| | PUT | `/opportunities/{user_id}/preferences` | Save preferences |
| | POST | `/opportunities/{user_id}/generate` | Regenerate board *(LLM)* |
| **achievements** *(new)* | GET | `/achievements/{user_id}` | List achievements |
| | POST | `/achievements/{user_id}` | Add achievement |
| | DELETE | `/achievements/{user_id}/{achievement_id}` | Delete achievement |
| **calendar** | GET | `/calendar/events` · `/sources` | Events + source statuses |
| **dossier** | GET | `/dossier/weekly/{user_id}` | Weekly dossier |
| **reminders** | POST | `/reminders/daily` | Trigger daily reminder emails *(secret-protected cron)* |
| **feedback** | GET/POST | `/feedback` | Feedback |
| **system** | GET | `/` · `/health` | Health checks |

Interactive docs: `http://localhost:8000/docs` (Swagger).

---

## 12. Frontend architecture

A CRA + CRACO single-page app. `App.js` wires routing, the React Query client,
auth gating, and route-level code-splitting.

**Routing & gating:**
- **Public:** `/`, `/about`, `/careers`, `/contact`, `/partners`, `/investors`,
  `/early-access`, `/privacy`, `/terms`, `/login`.
- **Auth only (no onboarding required):** `/onboarding`, `/intake`.
- **Auth + onboarding complete:** `/dashboard`, `/weekly-plan`, `/roadmap`,
  `/progress-report`, `/resume`, `/achievements`, `/opportunities`, `/ledger`,
  `/briefs`, `/pulse`, `/calendar`, `/portfolio`, `/profile`.
- Gating: `<RequireAuth>` (Zustand `userId`/`loading`) then `<ProtectedRoute>`
  (`onboarding_complete`).

**State & data:**
- **Auth:** Zustand `store/authStore.js` — `userId` + JWT, persisted to
  `localStorage`, synced from Supabase `getSession()` on boot.
- **Persistent chat:** Zustand `store/agent2ChatStore.js` — keeps Agent 2 chat
  history in the client so it survives navigation.
- **Server state:** TanStack React Query. Global `staleTime: 60s`, `gcTime: 5m`
  so navigation doesn't refetch slow endpoints. Hooks in `hooks/`.
- **API client:** `lib/api.js` — one Axios instance (90s default timeout) with
  request/response interceptors, exposing typed method groups (`usersAPI`,
  `briefsAPI`, `chatAPI`, `careerOSAPI`, `resumeAPI`, `opportunitiesAPI`,
  `achievementsAPI`, `ingestionAPI`, …). The long weekly-cycle call overrides to
  300s.

**Rendering:** route pages loaded with `React.lazy` + `<Suspense>` (separate
chunks); design system in `components/ui/*` (Radix + Tailwind), `GlassPanel`,
`Navbar`; animations via Framer Motion; charts via Recharts.

---

## 13. Authentication, authorization & security

**Authentication:** Supabase issues a JWT on email/password or Google sign-in.
The frontend stores `userId` + token in the Zustand auth store and attaches them
to **every** request via the Axios interceptor: `X-User-Id` header and
`Authorization: Bearer <jwt>`.

**Authorization (ownership / BOLA prevention):** every owner-scoped route depends
on `require_owner` (`dependencies/auth.py`). It:
1. Verifies the Supabase JWT — **HS256** with the local secret, or **asymmetric
   (ES256/RS256, etc.)** via dynamic **JWKS** lookup from the Supabase
   `.well-known/jwks.json`.
2. Extracts the `sub` (user id) claim and checks it matches the `user_id` in the
   path — a user can only access their own resources (403 otherwise).
3. Falls back to `X-User-Id` matching if no bearer token is present (dev/back-compat).

A `401` on the client triggers `logout()` + redirect to `/login`.

**Other controls:**
- **Rate limiting** (slowapi): `/briefs/generate` 5/hr, `/chat/message` 20/min.
- **CORS**: allow-list (`localhost:3000`, `127.0.0.1:3000`, the Vercel origin;
  overridable via `CORS_ORIGINS`).
- **Transport**: HTTPS in production (Vercel + Render).
- **Reminder endpoint** protected by a shared `X-Reminder-Secret`.
- **Input validation** via Pydantic on every write route; `user_id` sanitized in
  `profile_store` (`[A-Za-z0-9_-]{1,80}`).

> **Note:** `00000000-0000-0000-0000-000000000000` is treated as a guest/seed
> sentinel and bypasses the ownership equality check — keep this in mind for
> production hardening.

---

## 14. Performance & caching

Latency is dominated by external calls (Gemini + live market scraping). The
design keeps the backend **synchronous** and attacks latency three ways:

**a) Parallelism (`services/parallel.py`)** — `run_parallel({name: callable}, …)`
fans blocking calls across a `ThreadPoolExecutor` and fails soft (a task that
errors/times out yields its default). Used by `market_pulse.get_market_snapshot`,
`web_search.search_for_market_pulse`, and `opportunity_adapters.collect_opportunities`.

**b) Caching (`services/cache.py`)** — Redis-backed with a **fail-open**
in-process `TTLCache` fallback; the app behaves identically with or without Redis.
Keys are `delta:{namespace}:{sha1(key)}`; empty results are not cached.

| Cached | Namespace | TTL |
|--------|-----------|-----|
| Market snapshot (by role) | `market_snapshot` | 12h |
| Web search results (by query) | `web_search` | 6h |
| Embeddings (by text) | `embedding` | 30d *(only when a real model is used)* |
| Intent classification | `intent` | 1h |

> **Never cached:** personalized generative output — weekly briefs, chat answers,
> resume generation, opportunity boards. These stay fresh per request.

**c) DB & server tuning** — SQLite WAL + `busy_timeout` + `synchronous=NORMAL`;
`pool_pre_ping` (+ pool sizing for Postgres); composite indexes; `GZipMiddleware`
(>1 KB); 60s LLM timeout; background warmup on startup.

**d) Frontend** — global React Query `staleTime`/`gcTime`; optimistic task
actions; route code-splitting; 90s Axios default (300s for weekly-cycle).

---

## 15. External integrations & data flows

| Service | Used for | Module | What data leaves Delta |
|---------|----------|--------|------------------------|
| **Supabase** | Auth + Postgres DB hosting | FE `authStore.js`, BE `auth.py`, DB | Account + all stored personal data (DB is Supabase-hosted in prod) |
| **Google Gemini** | All LLM generation | `ai_service.py` | Profile context, chat messages, resume text, prompts |
| **Tavily / Serper** | Web search (market pulse, enrichment) | `web_search.py` | Search queries (role/market terms; may include profile-derived terms) |
| **GitHub / StackExchange / Arbeitnow** | Market signals | `market_pulse.py` | Role/skill queries (no user PII) |
| **LeetCode / Codeforces / Kaggle / Unstop / Devpost** | Opportunities | `opportunity_adapters.py` | Public queries (no user PII); mock by default |
| **LinkedIn** | Job-search deeplinks | `opportunity_ai.py` | **Nothing** — only a URL is constructed for the user to click |
| **Gmail SMTP** | Daily reminder emails | `email_service.py` | Recipient email + task titles |
| **Redis** | Shared cache | `cache.py` | Market/search/embedding artifacts (optional; fail-open) |
| **Vercel** | Frontend hosting | — | Standard web/CDN logs |
| **Render** | Backend hosting | — | Standard server/request logs |

See [§18](#18-personal-data-map-for-privacydpdp) and the
[Privacy Policy](./PRIVACY_POLICY.md) for the personal-data view of these flows.

---

## 16. Configuration & environment variables

### Backend (`backend/.env`)
| Var | Default | Purpose |
|-----|---------|---------|
| `DATABASE_URL` | `sqlite:///./delta.db` | DB connection (async sqlite auto-converted to sync; Postgres in prod) |
| `GEMINI_API_KEY` … `GEMINI_API_KEY_5` | — | Gemini keys (round-robin) |
| `GEMINI_MODEL` | `gemma-4-31b-it` | Default LLM model (**do not change without approval**) |
| `OPENAI_API_KEY` | — | Present in config; not required (OpenAI removed from deps) |
| `REDIS_URL` | `redis://localhost:6379/0` | Shared cache; falls back to in-process |
| `CACHE_ENABLED` | `true` | Master cache switch |
| `TAVILY_API_KEY` / `SERPER_API_KEY` | — | Web search providers |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_JWT_SECRET` | — | Auth / JWT verification |
| `CORS_ORIGINS` | localhost + Vercel origin | Allowed origins (CSV) |
| `*_SOURCE_MODE` (`OPPORTUNITY`, `LEETCODE`, …) | `mock` | Live vs mock adapters |
| `REMINDER_FROM_EMAIL` / `REMINDER_FROM_PASSWORD` / `REMINDER_SECRET` | — | Gmail SMTP + cron protection |
| `FRONTEND_URL` | `https://delta-ai.vercel.app` | Links in emails |
| `SQL_ECHO` | `false` | Log all SQL |

### Frontend (`frontend/.env`)
| Var | Purpose |
|-----|---------|
| `REACT_APP_API_URL` | Backend base URL (default `http://localhost:8000/api`) |
| `REACT_APP_SUPABASE_URL` / `REACT_APP_SUPABASE_ANON_KEY` | Supabase client |
| `SKIP_PREFLIGHT_CHECK` | CRA/CRACO build flag |

---

## 17. Deployment & operations

- **Frontend → Vercel.** Root `frontend/`; `vercel.json` rewrites all routes to
  `index.html`. Build `npm run build` (`craco build`). Vercel builds with
  `CI=true`, so **lint warnings fail the build** — keep the tree warning-clean.
  Pushes to `main` auto-deploy.
- **Backend → Railway** (previously Render). Built from `backend/Dockerfile`
  (`python:3.11-slim`, installs `requirements.txt`, runs Uvicorn with dynamic
  `$PORT`). Must be **redeployed separately** to pick up backend changes / new
  dependencies. The prior Render free tier was memory-constrained (512 MB) —
  this is why `sentence-transformers`, `scipy`, and `openai` were removed to
  avoid OOM.
- **Database → Supabase Postgres** in production; SQLite locally. Tables/columns/
  indexes are created idempotently on startup.
- **Redis** — optional; provision managed Redis and set `REDIS_URL` for a shared
  cache; otherwise each instance uses its in-process fallback.
- **Daily reminders** — schedule a cron (Render Cron / cron-job.org) to
  `POST /api/reminders/daily` with the `X-Reminder-Secret` header.
- **Local dev** — `docker-compose up --build` (backend) + `npm start`
  (frontend), or run each manually per the [README](../README.md).

### Git workflow (collaborative repo)
A collaborator co-develops on this repo. **Always `git pull origin main` before
changes; never push unless explicitly told; surface merge conflicts instead of
auto-resolving.** (See `CLAUDE.md` §6.)

---

## 18. Personal-data map (for privacy/DPDP)

This is the authoritative list of personal data Delta processes, feeding the
[Privacy Policy](./PRIVACY_POLICY.md).

**Identity & contact:** name, email, phone number, `user_id`; LinkedIn, GitHub,
portfolio URLs. Auth credentials are handled by **Supabase** (Delta never stores
raw passwords).

**Education & academic:** institution/university, major, study year, GPA,
education/life stage, target exams, exam dates.

**Professional:** current role, target role, years of experience, experience
level, past experience, skills (+ depths), projects, certificates, achievements
(trophy cabinet), target industries.

**Resume:** extracted text (`raw_text`) and structured data (contact, summary,
skills, experience, projects, education) from uploaded PDF/DOCX. **The original
uploaded file is not retained** after parsing.

**Preferences & constraints:** hours/week, learning style, preferred content
types, location & relocation openness, opportunity preferences (location, role
types, work mode, industries, notes), personalization settings.

**Conversations:** Agent 1 (onboarding) and Agent 2 (weekly planning) chat
messages, chat notes, backstory / personal introduction / transition reason.

**Activity & derived data:** task completions, journey events (incl. moods and AI
decisions), progress logs, Delta Score history, weekly briefs, roadmaps, market
snapshots, semantic-memory nodes/edges/tensions.

**Technical:** session JWT (in `localStorage`), functional cookies/local storage,
and standard server/CDN logs (IP, request metadata) via Render/Vercel.

**Sub-processors receiving personal data:** Supabase (storage), Google Gemini
(LLM prompts), Tavily/Serper (search queries), Gmail/Google (reminder emails),
Redis provider (cache artifacts, if configured). Several are **outside India**
(cross-border transfer — see the Privacy Policy).

**Not intentionally collected:** financial, health, biometric, or other
sensitive categories. Free-text fields could technically contain such data, so
the policy asks users not to submit it.

---

## 19. Conventions & non-negotiables

- **AI model selection is fixed** (`CLAUDE.md` §5): `gemma-4-31b-it` is the
  default for everything; `gemini-2.5-flash` is used **only** for resume
  analysis. Do not introduce new model strings or change models "for speed"
  without explicit approval.
- **Synchronous backend:** respect the sync SQLAlchemy engine and sync handlers —
  do not introduce the async engine piecemeal.
- **Cache only deterministic/idempotent work;** never cache personalized
  generative output.
- **Memory is structured:** never store user understanding as raw chat only —
  always structured profiles.
- **Market before roadmap:** never generate a roadmap without market context;
  never generate weekly advice without reading journey history.
- **Prefer fewer, stronger projects** over many weak ones.
- **Git workflow** (`CLAUDE.md` §6): pull before changes; never push unless
  explicitly told; surface merge conflicts.
- **Keep the frontend lint-clean** — Vercel builds with `CI=true`.
