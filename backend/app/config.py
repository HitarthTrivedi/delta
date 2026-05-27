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

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./delta.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]
    OPPORTUNITY_SOURCE_MODE: str = os.getenv("OPPORTUNITY_SOURCE_MODE", "mock")
    LEETCODE_SOURCE_MODE: str = os.getenv("LEETCODE_SOURCE_MODE", "")
    CODEFORCES_SOURCE_MODE: str = os.getenv("CODEFORCES_SOURCE_MODE", "")
    KAGGLE_SOURCE_MODE: str = os.getenv("KAGGLE_SOURCE_MODE", "")
    UNSTOP_SOURCE_MODE: str = os.getenv("UNSTOP_SOURCE_MODE", "")
    HACKATHON_SOURCE_MODE: str = os.getenv("HACKATHON_SOURCE_MODE", "")
    JOBPOSTS_SOURCE_MODE: str = os.getenv("JOBPOSTS_SOURCE_MODE", "")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
