import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Nivesh Backend"
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    UPSTASH_REDIS_URL: str = os.getenv("UPSTASH_REDIS_URL", "")
    UPSTASH_REDIS_TOKEN: str = os.getenv("UPSTASH_REDIS_TOKEN", "")
    GEMINI_API_KEYS: str = os.getenv("GEMINI_API_KEYS", os.getenv("GEMINI_API_KEY", ""))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    ENV: str = os.getenv("ENV", "development")

settings = Settings()
