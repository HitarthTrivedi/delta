# Delta — Operations runbook

How Delta runs in production: first-time setup, deploys, database changes, backups, monitoring and what to do when something breaks. For *what* Delta is and the build plan, see [DELTA_MASTER_PLAN.md](DELTA_MASTER_PLAN.md).

**Never put a real key, password or connection string in this repo.** They go in the host's encrypted settings (Railway, Cloudflare, GitHub secrets) and in teammates' local `.env` files.

## 1. What runs where

| Piece | Service | Notes |
|---|---|---|
| Frontend (React build) | Cloudflare Pages | Static files; `frontend/public/_headers` sets caching and security headers |
| API (FastAPI) | Railway, Southeast Asia (Singapore) region, **1 replica** | Built from `backend/Dockerfile`; runs `alembic upgrade head` on every start |
| Database + sign-in | Supabase, Mumbai (`ap-south-1`) | Postgres 17 + Supabase Auth |
| AI | Google Gemini API (Groq optional) | Models from `GEMINI_MODEL` / `GEMINI_LITE_MODEL` |
| Interviewer voice | Google Cloud Text-to-Speech | Optional; without it the interview uses the browser voice + 2D avatar |
| Code runner | JDoodle | Free tier: 200 runs/day |
| Email | Gmail API or Brevo | Daily reminders |
| Backups | GitHub Actions → Cloudflare R2 | Nightly, `age`-encrypted, kept 30 days |
| Errors / uptime | Sentry + UptimeRobot | |

Keep **one API replica** for now: the reminder scheduler runs inside the API process, and rate limits are counted in memory per process.

## 2. First-time setup

Do these in order. Each step lists the values to copy into the next.

### 2.1 Supabase (database + sign-in)
1. Create a project in region **South Asia (Mumbai)**. Save the database password in a password manager.
2. **Project Settings → Database → Connection string → "Session pooler"** (works over IPv4). Append `?sslmode=require`. This is `DATABASE_URL`, and also the `BACKUP_DATABASE_URL` GitHub secret.
3. **Project Settings → API**: copy the Project URL (`SUPABASE_URL`, `REACT_APP_SUPABASE_URL`), the `anon` key (`REACT_APP_SUPABASE_ANON_KEY`) and the `service_role` key (`SUPABASE_SERVICE_ROLE_KEY`, backend only, never in the frontend).
4. **JWT**: new projects sign tokens with asymmetric keys, which the API verifies through `SUPABASE_URL` automatically. Only if the project uses the legacy shared secret, copy it into `SUPABASE_JWT_SECRET`.
5. **Authentication → URL Configuration**: Site URL = the Pages domain (e.g. `https://app.example.com`); add the same under Redirect URLs. Enable the sign-in providers you use (email, Google).
6. The free plan pauses after a week without traffic and has no automatic backups. Our nightly backup (section 5) covers the data either way; move to **Pro** before scaling up or taking payments (daily backups + point-in-time restore).

### 2.2 Google Cloud Text-to-Speech (interviewer voice)
1. In Google Cloud console, create or pick a project with a billing account (needed even for the free monthly quota).
2. Enable **Cloud Text-to-Speech API**.
3. **APIs & Services → Credentials → Create API key**, then *Restrict key → API restrictions → Cloud Text-to-Speech API*. This is `GOOGLE_TTS_API_KEY` (backend only).
4. Set a **budget alert** on the billing account (e.g. ₹500/month) so a bug can't run up costs.

### 2.3 Railway (API)
1. New service from the GitHub repo. **Root directory:** `backend`. Builder: Dockerfile. Region: Southeast Asia.
2. **Healthcheck path:** `/health`. Replicas: 1.
3. Variables: see section 3. **Never** set `ALLOW_HEADER_AUTH` or `DEV_MODE` here.
4. Generate a domain; this is the API base (`https://<api>`). The frontend uses `https://<api>/api`.

### 2.4 Cloudflare Pages (frontend)
1. Create a Pages project from the GitHub repo. **Root directory:** `frontend`. **Build command:** `npm run build`. **Output:** `build`.
2. Environment variables: `NODE_VERSION=22`, `REACT_APP_API_URL=https://<api>/api`, `REACT_APP_SUPABASE_URL`, `REACT_APP_SUPABASE_ANON_KEY`. Never set `REACT_APP_DEV_AUTH`.
3. Add the custom domain. Then set the API's `CORS_ORIGINS` and `FRONTEND_URL` to that exact origin.

### 2.5 Backups (Cloudflare R2 + GitHub Actions)
1. Install [age](https://github.com/FiloSottile/age) on your own computer and run `age-keygen -o delta-backup-key.txt`. The line starting `age1…` is the **public** key. The file is the **private** key: store it offline (password manager + a USB stick). Without it no backup can be restored; with it anyone can read them.
2. Cloudflare → R2: create a bucket (e.g. `delta-backups`). **Settings → Object lifecycle rules**: delete objects with prefix `db/` after **30 days**.
3. R2 → **Manage API tokens**: create a token with *Object Read & Write* on that bucket only. Copy the Access Key ID, Secret Access Key and your Account ID.
4. GitHub repo → **Settings → Secrets and variables → Actions**, add: `BACKUP_DATABASE_URL`, `AGE_RECIPIENT` (the `age1…` public key), `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
5. **Actions → Database backup → Run workflow**. Check the run is green and the file appears in the bucket. Then do one restore drill (section 5.3).

### 2.6 Study reminders (email + browser push)
1. Email reminders use the Gmail/Brevo settings you already have. Set `EMAIL_LINK_SECRET` (a long random string) so every reminder carries a one-click unsubscribe link.
2. Browser push: run `python -m app.services.push_service` once (from `backend/`) and copy the printed `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` into Railway, plus `VAPID_SUBJECT=mailto:<a monitored inbox>`. Keep the private key secret; changing it later invalidates every browser subscription.
3. Reminders are opt-in: learners switch them on from Today or Privacy settings. Each learner gets at most one a day, at their own study time (default `REMINDER_HOUR_LOCAL`, 19:00), only if they haven't studied that day, with automatic backoff when ignored.

### 2.7 Monitoring
1. Sentry: create a project (platform: FastAPI) and copy its DSN into `SENTRY_DSN` on Railway. Turn on email alerts for new issues.
2. UptimeRobot: an HTTP monitor on `https://<api>/health` every 5 minutes, alerting your email. `/health` checks the database, so it also catches a paused or unreachable Supabase.

## 3. Environment variables (API, production)

Full list with comments: `backend/.env.example`. The production essentials:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Supabase session-pooler URL with `?sslmode=require` |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (+ `SUPABASE_JWT_SECRET` if legacy) | From Supabase |
| `CORS_ORIGINS`, `FRONTEND_URL` | The frontend origin, e.g. `https://app.example.com` |
| `GEMINI_API_KEY` (…`_5`) | Gemini keys |
| `GEMINI_MODEL` / `GEMINI_LITE_MODEL` / `GEMINI_BACKUP_MODEL` | Current Flash / Flash-Lite model ids |
| `GOOGLE_TTS_API_KEY`, `INTERVIEW_TTS_VOICES` | Interviewer voice (optional) |
| `ADMIN_EMAILS`, `CONTENT_REVIEWER_EMAILS` | Comma-separated |
| `JDOODLE_CLIENT_ID`, `JDOODLE_CLIENT_SECRET` | Coding sandbox |
| `GMAIL_*` or `BREVO_*`, `REMINDER_SECRET`, `EMAIL_LINK_SECRET` | Reminder emails + unsubscribe links |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | Browser push reminders (optional) |
| `SENTRY_DSN` | Error reports |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 5 / 5 (fine for one replica) |
| **Must be unset or false** | `ALLOW_HEADER_AUTH`, `DEV_MODE`, `ENABLE_DOCS` |

## 4. Deploying and database changes

- **Deploy:** merge to `main`. Railway rebuilds the API (migrations run first; a failing migration stops the deploy and the old version keeps serving). Pages rebuilds the frontend.
- **CI** (`.github/workflows/ci.yml`) runs on every PR: backend tests on SQLite and Postgres, `alembic upgrade head` + `alembic check`, `pip-audit`, and the frontend build. Don't merge red.
- **Changing a model:** edit `backend/app/models/…`, then from `backend/`:
  ```
  alembic revision --autogenerate -m "describe the change"
  ```
  Read the generated file in `backend/migrations/versions/` (autogenerate misses renames and data moves), run `alembic upgrade head` locally, and commit it with the model change. Prefer additive changes (new nullable column, new table); remove old columns in a later release.
- **Dependencies:** backend pins live in `requirements.txt`, generated from `requirements.in` (instructions at its top). Frontend: `package-lock.json`; add packages with `npm install <pkg> --before=<date two weeks ago>`.

## 5. Backups and restore

### 5.1 What is backed up
Every night at 03:00 IST, `.github/workflows/db-backup.yml` dumps the database's `public` schema (all Delta app data), checks the dump has table data, encrypts it with `age` to the public key, and uploads `db/delta-<timestamp>Z.dump.age` to R2. The lifecycle rule deletes copies after 30 days (the Privacy Policy promises this, so don't lengthen it without updating the policy).

Supabase's own `auth` schema (logins) is not in this dump. If the whole project were lost, users would sign up again with the same email, and their data would need re-linking to new ids. Supabase Pro's daily backups cover logins.

### 5.2 Restoring
1. Download the backup: `aws s3 cp s3://<bucket>/db/<file>.dump.age . --endpoint-url https://<account-id>.r2.cloudflarestorage.com`
2. Restore into the target (needs `age` and `pg_restore` 17+):
   ```
   CONFIRM_RESTORE=yes backend/scripts/restore_backup.sh <file>.dump.age delta-backup-key.txt "<target DATABASE_URL>"
   ```
   It drops and recreates the public-schema tables in the target. To recover production, first restore into a **new** Supabase project or a scratch database, check it, then point `DATABASE_URL` at it, rather than overwriting the live database in place.

### 5.3 Monthly restore drill (put it in your calendar)
Restore the latest backup into a scratch Postgres (a free Supabase project or a local one), then compare `select count(*) from users;` and a few other tables with production. A backup that has never been restored is not a backup.

## 6. When something breaks

| Symptom | First checks |
|---|---|
| UptimeRobot says API down | Railway deploy logs; `/health` returning 503 = database unreachable → Supabase status / project paused (free plan) |
| Users see "AI is not available right now" | Gemini quota or outage: Google AI Studio usage page; add a key (`GEMINI_API_KEY_2…`) or switch `GEMINI_MODEL` |
| Interview shows the 2D avatar | `GOOGLE_TTS_API_KEY` missing/invalid or quota hit (Sentry/Railway logs mention `tts`); the 2D fallback keeps interviews working |
| Errors after a deploy | Sentry → newest issue; roll back with Railway's "Redeploy" on the previous deployment |
| A migration failed on deploy | The old version keeps running. Fix the migration in a new commit; never edit a migration that already ran in production |
| Suspected data breach | Follow Privacy Policy section 12: contain it, record what happened, and inform affected users and the Data Protection Board without delay (DPDP Rules: within 72 hours). Rotate every key in section 3 |

## 7. Retention numbers

`GET /api/engagement/admin/metrics` (signed in with an `ADMIN_EMAILS` address) returns aggregates from our own tables:
- return rates by signup week (day 1, week 2, month 1);
- DAU, WAU, MAU and DAU/WAU;
- the share of weekly-active learners on a 7+ day streak;
- Quick 5 completions;
- reminder opt-ins, opt-outs, and how often a nudge is followed by studying within a day.

Watch opt-outs: a rising opt-out rate means reminders are too frequent or too pushy.

## 8. Limits to watch

- JDoodle free tier: 200 code runs/day. Above that, self-host Judge0 (Master Plan section 7).
- Gemini: per-key rate limits; rotation across up to 5 keys.
- Google TTS: free monthly character quota, then pay-per-character. Keep the budget alert on.
- Supabase free: 500 MB database, pauses when idle.
- One API replica: before adding a second, move the reminder scheduler and rate-limit counters to shared storage (Master Plan backlog).
