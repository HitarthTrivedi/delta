from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.models import *  # noqa: F401,F403 — ensures all models register with Base
from app.routers import users, skills, briefs, chat, resume, calendar, dossier, career_os, ingestion

app = FastAPI(
    title="Delta 2.0 API",
    description="Career Intelligence Platform — AI-driven skill tracking & market alignment",
    version="2.0.0",
)

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



@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    print("[OK] Delta 2.0 API started - tables synced")


@app.get("/")
def root():
    return {"status": "ok", "app": "Delta 2.0", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
