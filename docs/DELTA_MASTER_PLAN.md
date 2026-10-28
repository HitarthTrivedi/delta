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
Sold to colleges **per seat**; the college gives seats to its students. A student on a seat belongs to that college
(a tenant): the college's placement officer (TPO) manages seats, batches, the roster and which recruiters can see its
students, and sees their learning progress (never their chats). Students without a seat use the same product as solo
learners. Two programs: **from first year** (4-year track) and **6-month placement-ready** (final year). See
`docs/COLLEGE_DATA_NOTES.md` for the data roles.

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
- **Two pools that never mix:** *campus* recruiters see only opted-in students of colleges that linked them; *open* (off-campus) recruiters see only opted-in solo students. Professionals and under-18s are never shown.
- Later: company-specific roadmaps, where a company's requirements become a roadmap that students can opt into, plus company-specific assessments.

### Module 3 — Delta for Professionals
- **Who:** people who are *not* in college: working professionals, career switchers, people from any field who want to upskill.
- **What:** they give their goals (e.g. "move from support to data analytics in 9 months", "learn cloud for my current job"), and Delta builds a plan around them.
- **How it relates to College:** it reuses the same engine (intake → roadmap → weekly tasks → practice sandbox). The differences are what to plan for:
  - intake asks about current job, industry, years of experience and goal type (upskill in current role / switch career / get promoted), instead of college, year or GPA;
  - plans must fit a **tight time budget** (evenings/weekends) and have shorter, outcome-focused milestones;
  - roadmaps lean on job-relevant projects and certifications rather than placements;
  - professionals are **not** shown to recruiters (decision, Oct 2026: recruiters are for college students).
- **How it works:**
  - **Intake:** onboarding first asks "college student or working professional?" and saves `audience` in the profile. For professionals, intake asks job, industry, experience and goal type first (`PROFESSIONAL_RULES` in `ingestion_engine_v2.py`), requires `current_role` instead of education, and suggests job-friendly paces (4 / 6 / 10 h per week).
  - **Roadmap:** the weekly roadmap prompt adds professional planning rules (`brief_generator.py`).
  - **Recruiters:** never shown (`compliance.recruiter_pool_for` returns no pool for `audience=professional`).

## 3. Status

| Area | Feature | Status | Main files |
|---|---|---|---|
| College / student | Intake / onboarding | Built | `backend/app/routers/ingestion.py`, `services/onboarding_pipeline.py`, `frontend/src/pages/Onboarding.jsx` |
| College / student | Weekly roadmap + Agent 2 chat | Built | `routers/career_os.py`, `services/central_engine.py`, `services/agent2_memory.py`, `pages/WeeklyPlan.jsx` |
| College / student | Daily reminders (email) | Built | `services/reminder_service.py`, `services/email_service.py`, `routers/reminders.py` |
| College / student | Progress report / achievements / resume | Built | `pages/ProgressReport.jsx`, `pages/TrophyCabinet.jsx`, `pages/ResumePage.jsx` |
| College / student | Opportunities board | Built | `routers/opportunities.py`, `services/opportunity_*.py`, `pages/Opportunities.jsx` |
| College / sandbox | Coding sandbox | Built | `routers/sandbox_coding.py`, `services/code_runner.py`, `services/sandbox_problems.py`, `pages/CodingSandbox.jsx` |
| College / sandbox | AI video interview: 3D lip-synced interviewer "Aria" (TalkingHead + a custom CC0 avatar in a business suit, built with MPFB from `tools/avatar/`; voice from Google Cloud TTS via `/tts`), falling back to the 2D Aria + browser voice; mic or typed answers, webcam self-view, rubric report with model answers, one-click start | Built (v3) | `routers/sandbox_interview.py`, `services/interview_ai.py`, `pages/InterviewSandbox.jsx`, `components/interview/Avatar3D.jsx`, `components/interview/*`, `public/avatars/interviewer.glb`, `tools/avatar/*`, `hooks/useInterviewerVoice.js`, `hooks/useAnswerMic.js`, `hooks/useWebcam.js` |
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
| Production | Schema migrations (Alembic baseline; `alembic upgrade head` on container start) | Built | `backend/alembic.ini`, `backend/migrations/` |
| Production | Nightly encrypted off-site backups (pg_dump → age → Cloudflare R2, 30 days) + restore script | Built, **needs secrets set** | `.github/workflows/db-backup.yml`, `backend/scripts/restore_backup.sh` |
| Production | CI (tests on SQLite + Postgres, migration check, pip-audit, frontend build) | Built | `.github/workflows/ci.yml` |
| Production | Monitoring: Sentry (optional `SENTRY_DSN`), `/health` checks the DB | Built, **needs DSN + UptimeRobot** | `backend/app/main.py` |
| Production | Ops runbook (setup, deploy, migrations, backups, incidents) | Built | `docs/OPERATIONS.md` |
| Retention | Daily habit engine: streaks (freezes, break mode, repair), XP + levels, daily goal; XP only for server-verified learning actions, never affects scores | Built (Phase 1) | `services/engagement.py`, `routers/engagement.py`, `models/engagement.py` |
| Retention | Today home (one next step, Aria guide, habit at a glance) + celebrations | Built (Phase 1) | `pages/Today.jsx`, `components/engage/*`, `hooks/useEngagement.js`, `lib/celebrate.js` |
| Retention | Quick 5: daily 5-question spaced review from a shared, profile-free question bank | Built (Phase 1) | `services/quick_practice.py`, `routers/practice.py`, `pages/QuickPractice.jsx` |
| Retention | Opt-in study reminders (email + Web Push), per-learner time, backoff, one-click unsubscribe | Built (Phase 1), **needs VAPID keys + EMAIL_LINK_SECRET** | `services/reminder_service.py`, `services/push_service.py`, `public/sw.js` |
| Retention | Admin retention metrics (cohorts, DAU/WAU, streaks, reminders) | Built | `services/engagement_metrics.py` |
| Retention | De-intimidation pass (light practice pages, no-fear copy, Rewards + No-Fear design rules) | Built | `DESIGN.md`, practice pages |
| Retention | Daily quests (Quick 5 + 2 rotating, from verified XP events) + weekly challenge (quests on 4 days earns a streak freeze) | Built (Phase 2) | `services/quests.py`, `pages/Today.jsx` |
| Retention | Automatic badges (8 badges x 3 tiers, skill mastery needs evidence) + canvas share cards | Built (Phase 2) | `services/badges.py`, `components/engage/BadgeShelf.jsx`, `lib/shareCard.js` |
| Retention | Opt-in weekly leagues (5 tiers, groups of 20, XP-ranked, forgiving demotion, `leaderboard_visibility` consent) | Built (Phase 2) | `services/leagues.py`, `pages/League.jsx` |
| Retention | Progress path (roadmap phases as a path with "You are here") | Built (Phase 2) | `components/engage/ProgressPath.jsx` (Progress page) |
| Retention | "Consistent learner" recruiter badge (own `recruiter_habit_badge` consent; 20+ active days of 30; yes/no only) | Built (Phase 2) | `engagement.consistent_learners`, `routers/recruiter.py` |
| Retention | Study circles (up to 6, invite link, circle streak, shared weekly goal, `study_circles` consent) | Built (Phase 3) | `services/circles.py`, `routers/circles.py`, `pages/Circles.jsx`, `pages/CircleJoin.jsx` |
| Retention | Referrals (invite link; both get a streak freeze after the friend's 3 study days; `referral_link` consent; 5 rewards/month cap) | Built (Phase 3) | `services/referrals.py`, `lib/referral.js` |
| Retention | Personalised reminders: wording picked by a Thompson-sampling bandit (`nudge_log`), suggested study time from when the learner actually studies | Built (Phase 3) | `services/reminder_service.py`, `engagement.suggested_study_time` |
| Retention | WhatsApp reminders | Not planned (decision: email + browser push only) | — |
| College | Delta for College P1: colleges (tenants), seats, TPO/faculty staff, batches + join codes, roster CSV import, join by code/email domain (roster-verified), campus recruiter links, licence expiry | Built | `models/college.py`, `services/college.py`, `routers/college.py`, `pages/college/*`, `pages/CollegeJoin.jsx` |
| Recruiter | Two recruiter pools (campus / open), computed from consent + membership; professionals and minors never shown | Built | `compliance.recruiter_visible_ids`, `routers/recruiter.py` |
| Compliance | Under-18 college students (flag `MINOR_ACCOUNTS_ENABLED`, off until legal sign-off): parental consent link or college attestation, no AI on their data, restrictions, re-consent at 18 | Built (off) | `services/minors.py`, `dependencies/auth.block_minor_ai`, `pages/ParentConsent.jsx` |
| College | Delta for College P2: TPO analytics (college overview, batch dashboard with readiness spread, weekly activity, weakest skills and an at-risk list; per-student page limited to what the college may see) + CSV exports (roster status, batch readiness, NAAC 5.2.1 / NIRF outcomes sheet) | Built | `services/college_analytics.py`, `services/readiness.readiness_bulk`, `routers/college.py`, `pages/college/CollegeBatch.jsx`, `pages/college/CollegeStudent.jsx` |
| College | P3 role roadmap templates (placement 6m, SWE Google 12m, product SDE, data analyst, first-year 4y); P4 college-assigned plans and tests | Not started | — |
| College | Job match: paste a job ad -> skill gaps (code, not AI) -> add up to 3 tasks to this week, or plan the next 4 weeks around it (weekly cycle puts its gap tasks first) | Built | `services/job_match.py`, `routers/jobs.py`, `pages/JobMatch.jsx` |
| Recruiter | Trustworthy scores: per-session integrity notes (timed, tab switches, pasted code, implausibly fast answers), shown to the learner and to recruiters | Built | `services/integrity.py`, `hooks/useSessionSignals.js`, `components/IntegrityNote.jsx` |
| Recruiter | Public "verify this badge" links (`/v/:token`), created on share and revocable | Built | `badges.share/public_view`, `routers/public.py`, `pages/VerifyBadge.jsx` |

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
- **Accounts are 18+ only**, except under-18 college students on a seat when `MINOR_ACCOUNTS_ENABLED` is on (parental consent first; `block_minor_ai` on every AI route that would process their data; no recruiters, leagues, circles, invite or public links). School children never get accounts. They exist only as `child_profiles` under a parent who gave `parental_consent` (recorded with `subject_id` = the child). **Never** send child data to an AI provider, show it to recruiters, or use it for tracking, profiling or ads (DPDP §9). Child tables use the parent's id as `user_id`, so the parent's export and delete cover them.
- **School content is human-approved.** Never show a `SchoolLesson` to a child unless `status == 'approved'`. Any edit resets it to draft.
- **Recruiter visibility is a separate opt-in** (`recruiter_visibility` consent). Recruiters must only ever reach students through `compliance.recruiter_visible_ids()` / `can_recruiter_see()` (pool-aware). Joining or leaving a college withdraws visibility. New tables that link a learner to another record without a `user_id` column (like `roster_entries.claimed_user_id`) must be handled explicitly in `_erase_user_rows`. If you add a new recruiter-facing field, also update the "Recruiters see" list in `PrivacySettings.jsx` and Section 6 of the Privacy Policy.
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
| Frontend hosting | Vercel | Cloudflare Pages (free tier allows commercial use); `frontend/public/_headers` ready | not needed early |
| Backend (FastAPI) | Railway | Railway, Pro plan; more replicas later | traffic grows |
| Database + auth | SQLite locally; Postgres-ready code (psycopg 3, Alembic); Supabase project **not created yet** | Supabase Pro, Mumbai region: Postgres, auth, daily backups (the free tier pauses when idle) | before taking payments |
| AI | Gemini via `ai_service`; interview turns on `GEMINI_LITE_MODEL` | Gemini 2.5 Flash-Lite by default; Gemini 2.5 Flash only where quality matters (interview reports, tests, roadmaps); Batch API for non-urgent jobs | always pay-as-you-go |
| Interviewer voice | Google Cloud TTS (Neural2, SSML marks for lip-sync), optional | same; free monthly quota then pay per character | budget alert on the billing account |
| Code runner | JDoodle (free tier) | self-hosted Judge0 on a small VPS | more than 200 runs a day |
| Email | Gmail API / Brevo | Brevo, then Resend | more than 300 emails a day |
| Cache | in-process (Redis optional) | Upstash Redis | more than one backend replica |
| Monitoring | Sentry wired (needs DSN); `/health` checks the DB | Sentry (errors) + UptimeRobot (uptime) | — |
| Backups | nightly encrypted dump to Cloudflare R2 (GitHub Actions; needs secrets) | + Supabase Pro daily backups / point-in-time restore | before taking payments |
| Payments | none | Razorpay | — |

### AI cost rules (follow these in every AI feature)
- **Route by task:** use the lite model by default and the stronger model only where accuracy shows (scored reports, test generation, roadmaps).
- **Generate once, reuse many times:** test question bank, School lessons, coding problems and market snapshots are shared across users, not regenerated per user.
- **No AI where rules work:** grading, readiness scores and recruiter ranking use deterministic code.
- **The user's voice and video stay on their device:** speech recognition and the webcam run in the browser; never stream the user's audio or video to a paid API. The only voice we pay for is the interviewer's own (Google Cloud TTS of the question text, cached nowhere, free quota first); without a key the browser's voice is used.
- **Short prompts:** send the compact profile (`profile_as_compact_context`), not full histories.
- **Hard caps:** every expensive endpoint is rate-limited, and each plan will get monthly usage caps plus a spend alarm.

### Production backlog (in order)
1. **New Supabase project** (Mumbai). Keys go in the host's encrypted settings and teammates' local `.env` files, never in git.
2. ✅ **Postgres + migrations:** code is Postgres-ready (psycopg 3, tested on Postgres), Alembic adopted with a baseline. Remaining: point `DATABASE_URL` at the new Supabase project.
3. **Model routing in `ai_service`:** lite vs full model chosen per call site, with names from config. `GEMINI_LITE_MODEL` exists and the interview uses it; move other chatty call sites to it.
4. **Background job queue** for roadmap generation and other long AI work, so pages never wait on the model.
5. **Per-plan usage caps** and a monthly AI budget alarm.
6. ✅ **Monitoring:** Sentry wired (set `SENTRY_DSN`), `/health` checks the database; add the UptimeRobot monitor.
7. **Staging environment + load test** (at least 500 concurrent users) before any big college onboarding.
8. ✅ **Backups:** nightly encrypted off-site dump (`db-backup.yml`) + `restore_backup.sh`; set the secrets and run the monthly restore drill (`docs/OPERATIONS.md`).
9. **Anti-cheating** for sandbox scores recruiters rely on: integrity notes are built (signals, not proof); next would be a short supervised re-check for the scores recruiters weigh most.
10. **Legal:** lawyer review of `frontend/public/legal/*.md`; update the Data Fiduciary name once the company is registered.

**Gamification and retention** (research and plan: Duolingo's published streak, league and notification results; spaced retrieval; implementation intentions; CCPA dark-pattern rules; DPDP §9):
- Phases 1, 2 and 3 are built (see Status). The design rules are in `DESIGN.md` (Rewards exception, No-Fear rule) and `PRODUCT.md`.
- Phase 2 decisions worth knowing:
  - leagues prefer a same-field group but join any group at the tier with room, so early leagues aren't groups of one; revisit once there are enough learners per field;
  - the "Consistent learner" badge has its own consent on top of recruiter visibility, because the Privacy Policy promised recruiters never see habit data;
  - share cards are images made in the browser; a public "verify this badge" page is not built.
- Next for Phase 2, once there is data: tune quest rotation, league size and the challenge target from the retention numbers (`docs/OPERATIONS.md` §7).
- Phase 3 decisions worth knowing:
  - a circle streak needs every member to keep the day (a freeze or break counts), so it is a friend streak for 2 people and a team streak for more;
  - the reminder *time* is never moved automatically: the learner's chosen time is a plan they made, so Today only suggests a new time;
  - the policy text was updated without a version bump, because circles and referral links each ask for their own consent with a notice at the point of use; bump `POLICY_VERSION` if a lawyer prefers re-acceptance.
- Children (School) get content stars only: no streaks, XP history, reminders or leagues.

**Week 1 after the v1 beta launch** (deliberately not done before it):
- Frontend: move from Create React App (deprecated; its build tooling carries most `npm audit` findings) to Vite; remove unused dependencies (all `@radix-ui/*`, `cmdk`, `vaul`, `embla-carousel-react`, `input-otp`, `react-day-picker`, `react-resizable-panels`, `react-hook-form`, `zod`, `date-fns`, `motion`, `cra-template`) and the unused `components/ui/*`, `CareerChat.jsx`, `mockData.js`, `plugins/health-check`; self-host Monaco (today loaded from jsdelivr).
- Postgres-backed job queue (`jobs` table + `SKIP LOCKED`) for roadmap / weekly-cycle generation; delete the Celery stub.
- Before a 2nd API replica: advisory lock around the reminder scheduler, shared rate-limit storage.
- Interview: stream replies sentence by sentence; resume abandoned sessions; a male interviewer variant (same `tools/avatar/` pipeline, e.g. `toigo_male_suit_tie_and_jacket`) and a male/female choice.
- React Query + skeletons on the remaining pages; frontend Sentry; k6 load test (500 concurrent) on staging.
- Decide on the unlinked `/dashboard` page (link it or remove it).

### Local development
- **Env files:** copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env.development.local`. Both real files are gitignored. Ask a teammate for keys privately; never paste them into code, docs or commits.
- **Dev login (no Supabase needed):** set `REACT_APP_DEV_AUTH=true` (frontend) and `ALLOW_HEADER_AUTH=true` (backend). Any email signs you in with no password; the same email always opens the same account. It only works when the app is served from localhost, and production builds never have the flag. Never set either flag on a deployed environment.
- **Test data:** `python scripts/seed_demo.py --user-id <id> --with-candidates --yes` from `backend/` fills an account and adds fictional opted-in candidates. Local databases only.
- **Tests:** `pytest tests -q` from `backend/` (install `requirements-dev.txt`). Set `TEST_DATABASE_URL=postgresql://…` to run them against Postgres. CI runs both.
- **Schema changes:** edit the model, then `alembic revision --autogenerate -m "…"`, review, `alembic upgrade head` (see `docs/OPERATIONS.md`). Don't add new hand-written `ALTER`s.
- **Dependencies:** backend pins come from `requirements.in` (instructions at its top); frontend uses npm with a committed `package-lock.json`.
- **Production setup, deploys, backups, incidents:** `docs/OPERATIONS.md`.

## 8. Open questions

- **Recruiter verification:** what evidence do we accept before approving (company email domain, LinkedIn, a call)?
- **Parental verification:** today a parent is "verified" by being a signed-in adult who confirmed their age and relationship. DPDP Rules accept stronger checks (e.g. DigiLocker age tokens). Ask a lawyer whether that's needed before scaling School.
- **Legal entity:** the docs name Hitarth Trivedi as Data Fiduciary and Grievance Officer. Update both legal docs once a company is registered.
- **School curriculum source:** which boards and grades come first, and who authors or licenses the content?
- **Pricing:** recruiter-paid (B2B), student-paid, or institution-paid (colleges/schools)?
- **Anti-cheating** for sandbox scores that recruiters rely on: proctoring, time limits, question pools.
