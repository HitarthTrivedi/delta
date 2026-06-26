from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter
from app.config import settings
from app.database import engine, Base
from app.models import *  # noqa: F401,F403 — ensures all models register with Base
from app.routers import users, skills, briefs, chat, resume, calendar, dossier, career_os, ingestion, feedback

# Global rate limiter imported from app.limiter (avoids circular imports)

app = FastAPI(
    title="delta 2.0 API",
    description="Career Intelligence Platform — AI-driven skill tracking & market alignment",
    version="2.0.0",
)

# Attach limiter to app state so decorators can find it
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # Add profile_data column to existing users table (safe no-op if already present)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            if str(engine.url).startswith("postgresql"):
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_data TEXT"))
            else:
                # SQLite doesn't support IF NOT EXISTS on ALTER TABLE
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN profile_data TEXT"))
                except Exception:
                    pass
            conn.commit()
    except Exception as e:
        print(f"[WARN] profile_data column migration skipped: {e}")
    print("[OK] delta 2.0 API started - tables synced")
    try:
        from seed_guest import seed
        seed()
    except Exception as e:
        print(f"[WARN] Auto-seeding guest user failed: {e}")


@app.get("/")
def root():
    return {"status": "ok", "app": "delta 2.0", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
