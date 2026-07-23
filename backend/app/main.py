from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
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
    # Interactive docs and schema are disabled in production (avoid exposing the
    # full API surface); set ENABLE_DOCS=true to re-enable in dev.
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

# Attach limiter to app state so decorators + the global default_limits work
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)  # applies the global default rate limit to every route

_MAX_BODY_BYTES = (settings.MAX_UPLOAD_MB + 2) * 1024 * 1024


@app.middleware("http")
async def security_and_size_guard(request: Request, call_next):
    # Reject oversized bodies before reading them (memory-exhaustion DoS).
    cl = request.headers.get("content-length")
    if cl:
        try:
            if int(cl) > _MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body too large."})
        except ValueError:
            pass
    response = await call_next(request)
    # Baseline security headers on every response.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Piggyback the daily reminder sweep on real user traffic, so reminders still
    # go out on a host that sleeps when idle (the scheduler thread dies with it).
    # Runs after the response is built and hands off to a thread — never delays
    # the request. Health/root pings don't count as user activity.
    if request.url.path not in ("/", "/health"):
        try:
            from app.services.reminder_service import maybe_run_daily_sweep
            maybe_run_daily_sweep()
        except Exception as exc:
            logging.getLogger("delta").warning("reminder sweep hook failed: %s", exc)
    return response


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Never leak internal exception text to clients on server errors; log it instead.
    # 4xx details are intended, user-facing messages and pass through unchanged.
    if exc.status_code >= 500:
        logging.getLogger("delta").error("5xx at %s: %s", request.url.path, exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": "Internal server error. Please try again."})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=getattr(exc, "headers", None))

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
                conn.execute(text("ALTER TABLE roadmap_states ADD COLUMN IF NOT EXISTS plan_style TEXT"))
                conn.execute(text("ALTER TABLE roadmap_states ADD COLUMN IF NOT EXISTS day_schedule TEXT"))
                conn.execute(text("ALTER TABLE roadmap_states ADD COLUMN IF NOT EXISTS day_plan TEXT"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reminded_on DATE"))
            else:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_reminded_on DATE"))
                except Exception:
                    pass
                for col in ("profile_data", "agent2_memory_data"):
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} TEXT"))
                    except Exception:
                        pass
                for col in ("plan_style", "day_schedule", "day_plan"):
                    try:
                        conn.execute(text(f"ALTER TABLE roadmap_states ADD COLUMN {col} TEXT"))
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

    # Daily task reminders run inside this process — the external cron job was
    # unreliable. Idempotent per user per day, so restarts never double-send.
    try:
        from app.services.reminder_service import start_reminder_scheduler
        start_reminder_scheduler()
    except Exception as e:
        print(f"[WARN] reminder scheduler not started: {e}")

    print("[OK] delta 2.0 API started - tables synced")


@app.get("/")
def root():
    return {"status": "ok", "app": "delta 2.0", "version": "2.0.0"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy"}
