import logging
from typing import Optional, Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)

class DatabaseClient:
    """Supabase Postgres client wrapper with error handling and fallback support."""
    def __init__(self):
        self.client = None
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            try:
                from supabase import create_client
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("Connected to Supabase Postgres database.")
            except Exception as e:
                logger.warning(f"Could not connect to Supabase ({e}). Operating in memory mode.")

    def get_company(self, ticker: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        try:
            res = self.client.table("companies").select("*").eq("ticker", ticker).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase query error: {e}")
        return None

    def upsert_company(self, company_data: Dict[str, Any]):
        if not self.client:
            return
        try:
            self.client.table("companies").upsert(company_data).execute()
        except Exception as e:
            logger.warning(f"Supabase upsert company error: {e}")

    def get_saved_watchlists(self, user_id: str = "default") -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            res = self.client.table("watchlists").select("*, watchlist_items(*)").eq("user_id", user_id).execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"Supabase get watchlists error: {e}")
            return []

db_client = DatabaseClient()
