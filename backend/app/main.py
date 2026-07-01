from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter
from app.config import settings
from app.database import engine, Base
from app.models import *  # noqa: F401,F403 — ensures all models register with Base
from app.routers import users, skills, briefs, chat, resume, calendar, dossier, career_os, ingestion, feedback, reminders, achievements, opportunities

# Global rate limiter imported from app.limiter (avoids circular imports)

app = FastAPI(
    title="delta 2.0 API",
    description="Career Intelligence Platform — AI-driven skill tracking & market alignment",
    version="2.0.0",
)

# Attach limiter to app state so decorators can find it
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Compress large JSON payloads (career context, market snapshots) over the wire.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(skills.router)
app.include_router(briefs.router)
app.include_router(chat.router)
app.include_router(resume.router)
app.include_router(calendar.router)
app.include_router(dossier.router)
app.include_router(career_os.router)
app.include_router(ingestion.router)
app.include_router(feedback.router)
app.include_router(reminders.router)
app.include_router(achievements.router)
app.include_router(opportunities.router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # Add persistent JSON columns to users table (safe no-op if already present)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            if str(engine.url).startswith("postgresql"):
                # Override Supabase's short default statement_timeout for this transaction only
                conn.execute(text("SET LOCAL statement_timeout = '30s'"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_data TEXT"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS agent2_memory_data TEXT"))
            else:
                for col in ("profile_data", "agent2_memory_data"):
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} TEXT"))
                    except Exception:
                        pass
            conn.commit()
    except Exception as e:
        print(f"[WARN] users column migration skipped: {e}")

    # Composite indexes for the hot ordered/range queries (latest market
    # snapshot per user, recent journey events per user). IF NOT EXISTS is
    # supported by both SQLite and Postgres, so this is a safe idempotent no-op.
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_market_user_date "
                "ON market_snapshots (user_id, snapshot_date)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_journey_user_created "
                "ON journey_events (user_id, created_at)"
            ))
            conn.commit()
    except Exception as e:
        print(f"[WARN] composite index creation skipped: {e}")

    # Warm the embedding model + cache connection in the background so the first
    # real request doesn't pay the ~2s model load / Redis probe. Non-blocking;
    # failures are harmless (model falls back to MOCK, cache fails open).
    def _warm():
        try:
            from app.services.memory_graph import _get_embedding_model
            _get_embedding_model()
        except Exception as e:
            print(f"[WARN] embedding model warmup skipped: {e}")
        try:
            from app.services.cache import _get_redis
            _get_redis()
        except Exception as e:
            print(f"[WARN] cache warmup skipped: {e}")

    import threading
    threading.Thread(target=_warm, name="delta-warmup", daemon=True).start()

    print("[OK] delta 2.0 API started - tables synced")


@app.get("/")
def root():
    return {"status": "ok", "app": "delta 2.0", "version": "2.0.0"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}
