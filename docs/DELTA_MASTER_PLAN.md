# Delta — Master Plan

> **Read this first.** This is the shared source of truth for what Delta is, what's built, and what we build next. Humans and Claude sessions alike: read it before starting work, and **update the Status table when you finish (or start) a feature.**
>
> For *how* the existing system works internally, see [SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md) and [ARCHITECTURE.md](ARCHITECTURE.md). This doc covers *what* and *why*.

## 1. Vision

Delta is an **AI learning companion** sold as a startup product, with three modules: **School**, **College** and **Professionals**. Think of a college's placement cell: students on one side, companies arriving to hire on the other, and Delta in the middle. Delta trains students with roadmaps and daily/weekly tasks, tests them in a sandbox, and gives recruiters candidates who have been verified against exactly the skills the recruiter asked for.

Because the recruiter side exists, a student's learning gets a concrete goal, and the assessments carry weight with employers. Everything we build should serve **both sides**: a student-facing output (a test score, a completed task) should also be readable by a recruiter, which means it must be verifiable and broken down skill by skill.

## 2. The modules

### Module 1 — Delta for School
- **Who:** school children in CBSE classes 6–10, with their parents in charge.
- **What:** an LMS with a **fixed** curriculum (NCERT chapter lists), not AI roadmaps. v1 covers Maths and Science.
- **How it works:**
  - **Parent:** an adult who has passed the consent gate goes to `/school`, gives parental consent and adds a child (first name, class, PIN).
  - **Child:** studies in **child mode** (`/school/learn/:childId`), which locks the app to their lessons; the parent PIN is needed to leave.
  - **Lessons:** the content is identical for every child in a class. An AI draft is generated **once per chapter**, edited and **approved by a reviewer** at `/school/review`; children only ever see approved lessons.
  - **Progress:** each chapter has a 5-question quiz, and the best score is shown to both the child and the parent.
- **Not built (on purpose):** AI tutor chat for children, accounts or logins for children, other boards or subjects.
- **Before launch:** check the class 6–8 chapter lists (new NCERT books) in `services/school_curriculum.py` against the printed books, and approve lessons.


### Module 2 — Delta for College (main module)
This module has two sides.

**2a. Student side.** For college students preparing for job interviews or upskilling.
- **Roadmaps:** one intake conversation builds a model of the student; Agent 2 turns it into a roadmap toward their target role, delivered **one week at a time**.
- **Daily/weekly tasks:** concrete tasks with progress tracking, reminders, and a weekly check-in.
- **Testing sandbox**, which has three parts:
  1. **Technical theory test:** MCQ tests on theory, auto-graded, with a per-skill breakdown.
  2. **Coding sandbox:** real problems, code runs against test cases.
  3. **AI interview:** a live one-to-one mock interview (voice or text) with a structured feedback report.
- **Proof layer:** progress report, resume, achievements and opportunities, all built from completed, verified work.

**2b. Recruiter side.**
- A recruiter enters their **preferences**: role, required skills, minimum scores, and other filters such as location/year.
- Delta **suggests matching students**, ranked by how well their profile fits and by their **sandbox scores** (theory + coding + interview, per skill).
- Recruiters have **separate accounts** (`/recruiter/login`), are **manually approved** by a Delta admin before they see anyone, and only ever see students who **opted in** (Section 6).
- Later: company-specific roadmaps, where a company's requirements become a roadmap that students can opt into, plus company-specific assessments.

### Module 3 — Delta for Professionals
- **Who:** people who are *not* in college: working professionals, career switchers, people from any field who want to upskill.
- **What:** they give their goals (e.g. "move from support to data analytics in 9 months", "learn cloud for my current job"), and Delta builds a plan around them.
- **How it relates to College:** it reuses the same engine (intake → roadmap → weekly tasks → practice sandbox). The differences are what to plan for:
  - intake asks about current job, industry, years of experience and goal type (upskill in current role / switch career / get promoted), instead of college, year or GPA;
  - plans must fit a **tight time budget** (evenings/weekends) and have shorter, outcome-focused milestones;
  - roadmaps lean on job-relevant projects and certifications rather than placements;
  - recruiter visibility works the same way (opt-in), which is useful for career switchers.
- **How it works:**
  - **Intake:** onboarding first asks "college student or working professional?" and saves `audience` in the profile. For professionals, intake asks job, industry, experience and goal type first (`PROFESSIONAL_RULES` in `ingestion_engine_v2.py`), requires `current_role` instead of education, and suggests job-friendly paces (4 / 6 / 10 h per week).
  - **Roadmap:** the weekly roadmap prompt adds professional planning rules (`brief_generator.py`).
  - **Recruiters:** professionals who opt in show their current job instead of their college.

## 3. Status

| Area | Feature | Status | Main files |
|---|---|---|---|
| College / student | Intake / onboarding | Built | `backend/app/routers/ingestion.py`, `services/onboarding_pipeline.py`, `frontend/src/pages/Onboarding.jsx` |
| College / student | Weekly roadmap + Agent 2 chat | Built | `routers/career_os.py`, `services/central_engine.py`, `services/agent2_memory.py`, `pages/WeeklyPlan.jsx` |
| College / student | Daily reminders (email) | Built | `services/reminder_service.py`, `services/email_service.py`, `routers/reminders.py` |
| College / student | Progress report / achievements / resume | Built | `pages/ProgressReport.jsx`, `pages/TrophyCabinet.jsx`, `pages/ResumePage.jsx` |
| College / student | Opportunities board | Built | `routers/opportunities.py`, `services/opportunity_*.py`, `pages/Opportunities.jsx` |
| College / sandbox | Coding sandbox | Built | `routers/sandbox_coding.py`, `services/code_runner.py`, `services/sandbox_problems.py`, `pages/CodingSandbox.jsx` |
| College / sandbox | AI video interview (animated interviewer "Aria" that speaks, mic or typed answers, webcam self-view, rubric report with model answers) | Built (v2) | `routers/sandbox_interview.py`, `services/interview_ai.py`, `pages/InterviewSandbox.jsx`, `components/interview/*`, `hooks/useInterviewerVoice.js`, `hooks/useAnswerMic.js`, `hooks/useWebcam.js` |
| College / sandbox | Technical + aptitude tests (difficulty, timed mode, topic suggestions) | Built (v2) | `routers/sandbox_theory.py`, `services/theory_test_ai.py`, `pages/TheorySandbox.jsx` |
| College / sandbox | Test Center: readiness score, per-skill strengths/weaknesses, score trend, next steps (also shown to recruiters) | Built | `services/readiness.py`, `routers/sandbox_report.py`, `pages/PracticeHub.jsx` |
| Dev tooling | Test data script (student + 7 fictional opted-in candidates), local only | Built | `backend/scripts/seed_demo.py` |
| Dev tooling | Local dev login without Supabase (localhost + `REACT_APP_DEV_AUTH` only) | Built | `frontend/src/lib/devAuth.js` |
| College / recruiter | Separate recruiter login + registration + admin approval | Built (v1) | `routers/recruiter.py`, `models/compliance.py`, `pages/recruiter/RecruiterPortal.jsx`, `pages/recruiter/RecruiterAdmin.jsx`, `LoginPage.jsx` (`variant="recruiter"`) |
| College / recruiter | Preference form + ranked matching of opted-in students | Built (v1) | `routers/recruiter.py` (`/search`, `_score_candidate`) |
| College / recruiter | Candidate scorecard (per-skill sandbox evidence) | Built (v1) | `routers/recruiter.py` (`/candidates/{id}`), `RecruiterPortal.jsx` (`CandidateDetail`) |
| College / recruiter | Company-specific roadmaps | Not started | — |
| Compliance | Consent gate (Terms + Privacy + 18+ checkboxes, versioned) | Built | `components/ConsentGate.jsx`, `routers/privacy.py`, `services/compliance.py` |
| Compliance | Privacy settings: recruiter opt-in, who viewed me, export, delete account | Built | `pages/PrivacySettings.jsx`, `routers/privacy.py` |
| Compliance | Privacy Policy + Terms of Use (single source) | Built | `frontend/public/legal/*.md`, rendered by `components/LegalDocument.jsx` |
| Compliance | Parental consent + parent-managed child profiles | Built (v1) | `routers/school.py` (`add_child`, `remove_child`), `pages/school/SchoolParent.jsx` |
| Professionals | Student/professional choice + professional intake, pace and planning | Built (v1) | `services/ingestion_engine_v2.py`, `services/brief_generator.py`, `pages/Onboarding.jsx` |
| School | CBSE 6–10 Maths + Science curriculum (data) | Built, **class 6–8 lists need checking** | `services/school_curriculum.py` |
| School | Lesson drafting + human review/approval | Built (v1) | `services/school_content_ai.py`, `routers/school.py` (`/review/*`), `pages/school/SchoolReview.jsx` |
| School | Child mode: lessons, quizzes, progress, PIN exit | Built (v1) | `pages/school/SchoolLearn.jsx`, `lib/childMode.js`, `App.js` (`LayoutWrapper` lock) |

## 4. Build order

1. **Phase 1: finish the student sandbox.** ✅ Theory tests are built. Next: aptitude tests on the same engine, plus a single "sandbox scorecard" per student that combines theory, coding and interview scores per skill.
2. **Phase 2: recruiter portal + DPDP compliance.** ✅ v1 built: separate recruiter accounts with admin approval, saved preferences, ranked matching, candidate scorecards, student opt-in, consent gate, privacy settings, rewritten legal docs. Next: anti-cheating for scores recruiters rely on.
3. **Phase 3: Delta for Professionals.** ✅ v1 built.
4. **Phase 4: Delta for School.** ✅ v1 built: Maths + Science, CBSE 6–10, parent-managed. Next: approve all lessons, then more subjects (Social Science, English), then more boards.
5. **Phase 5: company-specific roadmaps.** Recruiter requirements produce a roadmap template that students can join; their progress and scores feed back to the recruiter.

## 5. Conventions (follow these when adding features)

- **Sandboxes share one table.** `SandboxSession` (`backend/app/models/sandbox_session.py`) uses `type` = `coding | interview | theory`. Type-specific payload goes in the JSON `data` column; the 0–100 `score` is set on completion. Add new assessment types the same way instead of creating new tables.
- **Sandbox router shape:** `/api/sandbox/<type>/{user_id}/...`, with `Depends(require_owner)` and `@limiter.limit(...)` on mutating endpoints. When a session completes, call `bump_skill` (`services/sandbox_common.py`) and `log_journey_event` (`services/central_engine.py`). Copy `routers/sandbox_interview.py`.
- **AI calls** go through `services/ai_service.py` (`generate_response` / `generate_json`). Ground prompts with `profile_store.profile_as_compact_context(user_id)`. Model names come from config (`GEMINI_MODEL`, `GEMINI_BACKUP_MODEL`); don't hardcode them. Follow the AI cost rules in Section 7.
- **Config, not constants.** Model names, URLs, sender emails, limits and keys come from `backend/app/config.py` / env vars (documented in `backend/.env.example` and `frontend/.env.example`). Defaults must be safe for local development; production sets real values in the host's settings.
- **Grading is server-side.** Never send answer keys to the client before submission. Never let the LLM grade something that can be graded deterministically.
- **Scores are evidence.** Store enough detail (per-question results, per-skill breakdown) that a recruiter could check why a student got that score.
- **Honest over decorative.** If AI generation fails, return an error. Never return fake or placeholder content dressed up as real (see `PRODUCT.md`).
- **Privacy (DPDP Act):** see Section 6. Any new feature that collects new data, uses data for a new purpose, or shares it with anyone new needs a Privacy Policy update and possibly a new consent.
- **Never assume tech.** Delta serves every field. Decide a user's field with `domain_packs.resolve_field(profile)` (explicit `profile["field"]` → keyword match → neutral `general`). Take field-specific content (phases, skills, proof types, interview formats, exams, opportunities, weekly habit) from the pack, never hardcode software defaults. Coding, GitHub and LeetCode only apply when the pack is tech (`cs_ai`; `data` also counts as tech).
- **Frontend:** pages live in `frontend/src/pages/`, the API client goes in `frontend/src/lib/api.js`, and routes are registered in `frontend/src/App.js` behind `RequireAuth` + `ProtectedRoute`. Practice tools are linked from `pages/PracticeHub.jsx`. Design rules: `PRODUCT.md` and `DESIGN.md`.

## 5b. Fields (Delta works for every career)

17 field packs live in `backend/app/services/domain_packs.py`:
- Software & IT, Data & Analytics, Core Engineering;
- Finance, Accounting & Commerce; Business, Management & HR; Marketing, Sales & PR; Product Management;
- Healthcare & Medicine, Law, Design & Architecture, Teaching & Education;
- Hospitality, Travel & Aviation; Media, Journalism & Content; Government & Public Service;
- Science & Research, Entrepreneurship, General.

| What adapts to the field | Where |
|---|---|
| Intake classifies the field (editable "Career Field" in the profile review) | `ingestion_engine_v2.py`, `Onboarding.jsx` |
| Roadmap phases, skills, proof, certifications, opportunities (AI prompt and offline fallback) | `brief_generator.py` |
| Weekly habit: LeetCode for software, the field's own practice for others | `central_engine._recurring_habit_actions` |
| Market signals: GitHub/StackOverflow only for tech; field skills counted from web search | `market_pulse.py`, `web_search.py` |
| Opportunities: coding contests only for tech; Unstop case competitions, field web search and internship links for all | `opportunity_adapters.py` |
| Interview: "Role knowledge" and "Case / scenario" rounds use the field's real formats; system design only for tech | `interview_ai.py`, `InterviewSandbox.jsx` |
| Readiness: coding counts only for tech fields (others: tests 55% / interview 45%) | `readiness.py`, `PracticeHub.jsx` |
| Résumé parsing: skills from every pack, non-tech degrees (B.Com, MBBS, LLB, B.Sc Nursing…) | `resume_parser.py` |

To add a field: add a pack (copy an existing one and fill every key), add its id/label to `frontend/src/lib/fields.js`, and add a role to `backend/tests/test_fields.py`.

## 6. Privacy and DPDP compliance (read before touching user data)

Delta is a **Data Fiduciary** under India's DPDP Act, 2023. These rules are built into the code. Don't break them.

- **Consent before processing.** Every student route sits behind `RequireAuth` → `ConsentGate`, which blocks the app until the user ticks: 18+, Terms of Use, Privacy Policy. Each consent event is an append-only row in `consent_records`, with policy version and timestamp.
- **Changing the legal docs.** Edit `frontend/public/legal/privacy-policy.md` / `terms-of-use.md` (the only copies). For a **material** change, also bump `POLICY_VERSION` in `backend/app/services/compliance.py`, and every user is asked to accept again. Never rely on "continued use = acceptance".
- **Accounts are 18+ only.** Children never get accounts. They exist only as `child_profiles` under a parent who gave `parental_consent` (recorded with `subject_id` = the child). **Never** send child data to an AI provider, show it to recruiters, or use it for tracking, profiling or ads (DPDP §9). Child tables use the parent's id as `user_id`, so the parent's export and delete cover them.
- **School content is human-approved.** Never show a `SchoolLesson` to a child unless `status == 'approved'`. Any edit resets it to draft.
- **Recruiter visibility is a separate opt-in** (`recruiter_visibility` consent). Recruiters must only ever reach students through `compliance.visible_student_ids()`. If you add a new recruiter-facing field, also update the "Recruiters see" list in `PrivacySettings.jsx` and Section 6 of the Privacy Policy.
- **Recruiters are approved by hand.** `status='approved'` is set from `/recruiter/admin` by an email listed in `ADMIN_EMAILS`. Every full-profile view is logged in `recruiter_profile_views` and shown to the student.
- **Rights are self-serve.** Export (`GET /api/privacy/{id}/export`) and erasure (`DELETE /api/privacy/{id}`) find user data automatically through any table with a `user_id` column. **New tables holding user data must have a `user_id` column**, or export and delete will silently miss them.
- **New data processors** (a new AI provider, email service, host…) must be added to Section 7 of the Privacy Policy before going live.

**Ops checklist for production:**
- set `ADMIN_EMAILS` (comma-separated) on the backend, and `CONTENT_REVIEWER_EMAILS` for teachers who review School lessons;
- set `SUPABASE_SERVICE_ROLE_KEY`, otherwise account deletion erases the data but can't remove the Supabase login;
- have a lawyer review `frontend/public/legal/*.md` before public launch, especially before charging recruiters money.

## 7. Going to production (current phase)

**The demo is over. We are building Delta as a commercial product.** Shipped code must have no demo shortcuts, hardcoded values or fake data. Anything that exists only for local testing must be switched off by default and impossible to turn on in production (see "Local development" below).

Business documents (pricing, unit economics, pitch, funding forms) are kept **outside this repo**. Don't add them here; `.gitignore` blocks the usual file names.

### Target stack
Chosen to stay cheap while bootstrapped, with a known paid upgrade for every free tier.

| Need | Now | Production target | Upgrade when |
|---|---|---|---|
| Frontend hosting | Vercel | Cloudflare Pages (free tier allows commercial use) | not needed early |
| Backend (FastAPI) | Railway | Railway, Pro plan; more replicas later | traffic grows |
| Database + auth | SQLite locally; Supabase project **deleted** | Supabase Pro, Mumbai region: Postgres, auth, daily backups (the free tier pauses when idle) | before taking payments |
| AI | Gemini via `ai_service` | Gemini 2.5 Flash-Lite by default; Gemini 2.5 Flash only where quality matters (interview reports, tests, roadmaps); Batch API for non-urgent jobs | always pay-as-you-go |
| Code runner | JDoodle (free tier) | self-hosted Judge0 on a small VPS | more than 200 runs a day |
| Email | Gmail API / Brevo | Brevo, then Resend | more than 300 emails a day |
| Cache | in-process (Redis optional) | Upstash Redis | more than one backend replica |
| Monitoring | none | Sentry (errors) + UptimeRobot (uptime) | — |
| Backups | none | Supabase backups + weekly off-site dump to Cloudflare R2 | — |
| Payments | none | Razorpay | — |

### AI cost rules (follow these in every AI feature)
- **Route by task:** use the lite model by default and the stronger model only where accuracy shows (scored reports, test generation, roadmaps).
- **Generate once, reuse many times:** test question bank, School lessons, coding problems and market snapshots are shared across users, not regenerated per user.
- **No AI where rules work:** grading, readiness scores and recruiter ranking use deterministic code.
- **Browser does voice and video:** speech recognition, text-to-speech and the webcam run on the user's device. Never stream audio or video to a paid API.
- **Short prompts:** send the compact profile (`profile_as_compact_context`), not full histories.
- **Hard caps:** every expensive endpoint is rate-limited, and each plan will get monthly usage caps plus a spend alarm.

### Production backlog (in order)
1. **New Supabase project** (Mumbai). Keys go in the host's encrypted settings and teammates' local `.env` files, never in git.
2. **Postgres + migrations:** move from SQLite to Supabase Postgres and adopt Alembic (today schema changes go through `add_missing_columns.py`).
3. **Model routing in `ai_service`:** lite vs full model chosen per call site, with names from config.
4. **Background job queue** for roadmap generation and other long AI work, so pages never wait on the model.
5. **Per-plan usage caps** and a monthly AI budget alarm.
6. **Monitoring:** Sentry error alerts and uptime checks.
7. **Staging environment + load test** (at least 500 concurrent users) before any big college onboarding.
8. **Backups:** weekly off-site database dump, with a restore tested monthly.
9. **Anti-cheating** for sandbox scores recruiters rely on.
10. **Legal:** lawyer review of `frontend/public/legal/*.md`; update the Data Fiduciary name once the company is registered.

### Local development
- **Env files:** copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env.development.local`. Both real files are gitignored. Ask a teammate for keys privately; never paste them into code, docs or commits.
- **Dev login (no Supabase needed):** set `REACT_APP_DEV_AUTH=true` (frontend) and `ALLOW_HEADER_AUTH=true` (backend). Any email signs you in with no password; the same email always opens the same account. It only works when the app is served from localhost, and production builds never have the flag. Never set either flag on a deployed environment.
- **Test data:** `python scripts/seed_demo.py --user-id <id> --with-candidates --yes` from `backend/` fills an account and adds fictional opted-in candidates. Local databases only.
- **Tests:** `pytest tests -q` from `backend/` (the `tests/` folder is gitignored for now).

## 8. Open questions

- **Recruiter verification:** what evidence do we accept before approving (company email domain, LinkedIn, a call)?
- **Parental verification:** today a parent is "verified" by being a signed-in adult who confirmed their age and relationship. DPDP Rules accept stronger checks (e.g. DigiLocker age tokens). Ask a lawyer whether that's needed before scaling School.
- **Legal entity:** the docs name Hitarth Trivedi as Data Fiduciary and Grievance Officer. Update both legal docs once a company is registered.
- **School curriculum source:** which boards and grades come first, and who authors or licenses the content?
- **Pricing:** recruiter-paid (B2B), student-paid, or institution-paid (colleges/schools)?
- **Anti-cheating** for sandbox scores that recruiters rely on: proctoring, time limits, question pools.
