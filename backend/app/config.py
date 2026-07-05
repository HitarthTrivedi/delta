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
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemma-4-31b-it")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # Security controls
    # ALLOW_HEADER_AUTH: when true, trust the unverified X-User-Id header (dev only).
    # MUST stay false in production — a verified Supabase JWT is then required.
    ALLOW_HEADER_AUTH: bool = parse_bool_env("ALLOW_HEADER_AUTH", False)
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "")
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
            "https://delta-kappa-pink.vercel.app",
        ])
    OPPORTUNITY_SOURCE_MODE: str = os.getenv("OPPORTUNITY_SOURCE_MODE", "mock")
    LEETCODE_SOURCE_MODE: str = os.getenv("LEETCODE_SOURCE_MODE", "")
    CODEFORCES_SOURCE_MODE: str = os.getenv("CODEFORCES_SOURCE_MODE", "")
    KAGGLE_SOURCE_MODE: str = os.getenv("KAGGLE_SOURCE_MODE", "")
    UNSTOP_SOURCE_MODE: str = os.getenv("UNSTOP_SOURCE_MODE", "")
    HACKATHON_SOURCE_MODE: str = os.getenv("HACKATHON_SOURCE_MODE", "")
    JOBPOSTS_SOURCE_MODE: str = os.getenv("JOBPOSTS_SOURCE_MODE", "")
    REMINDER_FROM_EMAIL: str = os.getenv("REMINDER_FROM_EMAIL", "")
    REMINDER_FROM_PASSWORD: str = os.getenv("REMINDER_FROM_PASSWORD", "")
    REMINDER_SECRET: str = os.getenv("REMINDER_SECRET", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://delta-ai.vercel.app")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
