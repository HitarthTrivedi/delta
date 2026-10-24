import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Upgraded self-healing dotenv loader: searches multiple relative depths
env_loaded = False
for p in [Path("."), Path(__file__).parent, Path(__file__).parent.parent, Path(__file__).parent.parent.parent]:
    for candidate in [p / ".env", p / "backend" / ".env"]:
        if candidate.exists() and candidate.is_file():
            load_dotenv(candidate)
            print(f"[OK] Dynamic Career OS loaded environment from: {candidate.resolve()}")
            env_loaded = True
            break
    if env_loaded:
        break

if not env_loaded:
    print("[WARN] No .env file loaded by parent-scanning search.")


def parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if not raw_value:
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]

def parse_bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}

def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./delta.db")
    if url.startswith("sqlite+aiosqlite://"):
        print("[WARN] DATABASE_URL used async sqlite driver; converting to sync sqlite driver.")
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


class Settings(BaseSettings):
    DATABASE_URL: str = _database_url()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEY_2: str = os.getenv("GEMINI_API_KEY_2", "")
    GEMINI_API_KEY_3: str = os.getenv("GEMINI_API_KEY_3", "")
    GEMINI_API_KEY_4: str = os.getenv("GEMINI_API_KEY_4", "")
    GEMINI_API_KEY_5: str = os.getenv("GEMINI_API_KEY_5", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    # Used once when GEMINI_MODEL is overloaded or rate-limited. Empty = no retry.
    GEMINI_BACKUP_MODEL: str = os.getenv("GEMINI_BACKUP_MODEL", "gemini-2.5-flash-lite")
    # Cheap, fast model for chatty, latency-sensitive calls (e.g. interview turns).
    # GEMINI_MODEL stays the default for work where quality shows (reports, tests).
    GEMINI_LITE_MODEL: str = os.getenv("GEMINI_LITE_MODEL", "gemini-2.5-flash-lite")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    # Google Cloud Text-to-Speech: the 3D interviewer's voice + lip-sync timings.
    # Without a key the interview uses the browser voice and the 2D avatar.
    GOOGLE_TTS_API_KEY: str = os.getenv("GOOGLE_TTS_API_KEY", "")
    # Allowed interviewer voices (comma-separated); the first is the default.
    # Must support SSML <mark> (Standard, WaveNet or Neural2) for lip-sync timing.
    INTERVIEW_TTS_VOICES: str = os.getenv("INTERVIEW_TTS_VOICES", "en-IN-Neural2-A,en-IN-Neural2-D")
    # Local testing only: turns off weekly pacing guards and allows the offline
    # mock AI replies when no Gemini key is set. Never set on a deployed host.
    DEV_MODE: bool = parse_bool_env("DEV_MODE", False)
    # Browser push for study reminders (Web Push / VAPID). Empty = push disabled,
    # email reminders still work. Generate once: see docs/OPERATIONS.md.
    VAPID_PUBLIC_KEY: str = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY: str = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT: str = os.getenv("VAPID_SUBJECT", "")  # e.g. mailto:team@example.com
    # Signs one-click unsubscribe links in reminder emails (falls back to REMINDER_SECRET).
    EMAIL_LINK_SECRET: str = os.getenv("EMAIL_LINK_SECRET", "")
    # Error reporting (Sentry). Empty = disabled. No personal data is sent.
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    # Postgres connection pool per process (Supabase limits total connections).
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5") or "5")
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "5") or "5")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # JDoodle — code execution for the Coding Sandbox (free tier: 200 runs/day).
    # Get credentials at jdoodle.com/compiler-api. Without them, the sandbox's
    # run/submit endpoints return a clear "not configured" error.
    JDOODLE_CLIENT_ID: str = os.getenv("JDOODLE_CLIENT_ID", "")
    JDOODLE_CLIENT_SECRET: str = os.getenv("JDOODLE_CLIENT_SECRET", "")
    # Security controls
    # ALLOW_HEADER_AUTH: when true, trust the unverified X-User-Id header (dev only).
    # MUST stay false in production — a verified Supabase JWT is then required.
    ALLOW_HEADER_AUTH: bool = parse_bool_env("ALLOW_HEADER_AUTH", False)
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "")
    # Comma-separated emails allowed to approve/reject recruiter accounts.
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "")
    # Comma-separated emails (e.g. teachers) allowed to review/approve School lessons. Admins can too.
    CONTENT_REVIEWER_EMAILS: str = os.getenv("CONTENT_REVIEWER_EMAILS", "")
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "5") or "5")
    MAX_TEXT_CHARS: int = int(os.getenv("MAX_TEXT_CHARS", "60000") or "60000")
    ENABLE_DOCS: bool = parse_bool_env("ENABLE_DOCS", False)
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    SQL_ECHO: bool = parse_bool_env("SQL_ECHO", False)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_ENABLED: bool = parse_bool_env("CACHE_ENABLED", True)

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return parse_csv_env("CORS_ORIGINS", [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ])
    OPPORTUNITY_SOURCE_MODE: str = os.getenv("OPPORTUNITY_SOURCE_MODE", "mock")
    LEETCODE_SOURCE_MODE: str = os.getenv("LEETCODE_SOURCE_MODE", "")
    CODEFORCES_SOURCE_MODE: str = os.getenv("CODEFORCES_SOURCE_MODE", "")
    KAGGLE_SOURCE_MODE: str = os.getenv("KAGGLE_SOURCE_MODE", "")
    UNSTOP_SOURCE_MODE: str = os.getenv("UNSTOP_SOURCE_MODE", "")
    HACKATHON_SOURCE_MODE: str = os.getenv("HACKATHON_SOURCE_MODE", "")
    JOBPOSTS_SOURCE_MODE: str = os.getenv("JOBPOSTS_SOURCE_MODE", "")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    # Gmail API (preferred transport — sends from our own mailbox over HTTPS,
    # so Railway's outbound SMTP block doesn't apply). Requires OAuth2: there is
    # no API-key path for sending mail.
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    GMAIL_FROM_EMAIL: str = os.getenv("GMAIL_FROM_EMAIL", "")
    GMAIL_FROM_NAME: str = os.getenv("GMAIL_FROM_NAME", "Delta by Alpha.Kore")
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_FROM_EMAIL: str = os.getenv("BREVO_FROM_EMAIL", "")
    BREVO_FROM_NAME: str = os.getenv("BREVO_FROM_NAME", "Delta by Alpha.Kore")
    REMINDER_SECRET: str = os.getenv("REMINDER_SECRET", "")
    # Opt-in study reminders, checked every REMINDER_CHECK_INTERVAL_SECONDS (and on
    # user traffic, for hosts that sleep). Each learner is nudged at their own time;
    # REMINDER_TIMEZONE is the default timezone for new learners.
    REMINDERS_ENABLED: bool = os.getenv("REMINDERS_ENABLED", "true").lower() == "true"
    REMINDER_TIMEZONE: str = os.getenv("REMINDER_TIMEZONE", "Asia/Kolkata")
    # Hour (local) for a learner's reminder when they haven't picked a study time.
    REMINDER_HOUR_LOCAL: int = int(os.getenv("REMINDER_HOUR_LOCAL", "19"))
    REMINDER_CHECK_INTERVAL_SECONDS: int = int(os.getenv("REMINDER_CHECK_INTERVAL_SECONDS", "900"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
