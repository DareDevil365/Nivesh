import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class Settings:
    PROJECT_NAME: str = "Nivesh Backend"
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    UPSTASH_REDIS_URL: str = os.getenv("UPSTASH_REDIS_REST_URL", os.getenv("UPSTASH_REDIS_URL", ""))
    UPSTASH_REDIS_TOKEN: str = os.getenv(
        "UPSTASH_REDIS_REST_TOKEN", os.getenv("UPSTASH_REDIS_TOKEN", "")
    )
    GEMINI_API_KEYS: str = os.getenv("GEMINI_API_KEYS", "").strip() or os.getenv(
        "GEMINI_API_KEY", ""
    )
    GEMINI_KEY_PROJECTS: str = os.getenv("GEMINI_KEY_PROJECTS", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    ENV: str = os.getenv("ENV", "development")


settings = Settings()
