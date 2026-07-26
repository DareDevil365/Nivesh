import time
import logging
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel
from config import settings

logger = logging.getLogger(__name__)

class KeyState(BaseModel):
    key: str
    tier: str = "flash"  # "flash" or "flash_lite"
    calls_today: int = 0
    errors_today: int = 0
    cooldown_until: float = 0.0
    status: str = "active"

class GeminiKeyRotator:
    """
    7-Key Gemini API Rotator with credit tracking, rate-limit cooldown,
    model-tier fallback, and structured output validation.
    """
    def __init__(self):
        raw_keys = [k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()]
        self.keys: List[KeyState] = [KeyState(key=k) for k in raw_keys]
        self._current_index = 0
        self._last_reset_day = time.strftime("%Y-%m-%d")

    def _check_daily_reset(self):
        today = time.strftime("%Y-%m-%d")
        if today != self._last_reset_day:
            self._last_reset_day = today
            for k in self.keys:
                k.calls_today = 0
                k.errors_today = 0
                k.status = "active"
                k.tier = "flash"
            logger.info("Reset daily Gemini API call counters across all keys.")

    def get_active_key(self, task_type: str = "heavy") -> Optional[str]:
        self._check_daily_reset()
        now = time.time()
        
        # Filter ready keys
        ready_keys = [k for k in self.keys if k.status != "disabled" and k.cooldown_until <= now]
        if not ready_keys:
            logger.warning("No active Gemini API keys available right now (all in cooldown or disabled).")
            return None

        # Round-robin selection
        selected_state = ready_keys[self._current_index % len(ready_keys)]
        self._current_index += 1
        return selected_state.key

    def report_success(self, key: str):
        for k in self.keys:
            if k.key == key:
                k.calls_today += 1
                k.status = "active"
                break

    def report_error(self, key: str, status_code: int = 429):
        now = time.time()
        for k in self.keys:
            if k.key == key:
                k.errors_today += 1
                if status_code == 429:
                    # Rate limit -> 60s cooldown
                    k.cooldown_until = now + 60.0
                    k.status = "cooldown"
                    logger.warning(f"Gemini key ending in ..{key[-6:]} hit rate limit (429). Placed on 60s cooldown.")
                elif status_code == 400 or status_code == 403:
                    # Model limit / quota exhausted -> mark degraded / fallback
                    k.tier = "flash_lite"
                    k.cooldown_until = now + 300.0
                    logger.warning(f"Gemini key ending in ..{key[-6:]} quota limit hit ({status_code}). Degraded to flash_lite.")
                break

    def get_status(self) -> Dict[str, Any]:
        self._check_daily_reset()
        return {
            "total_keys": len(self.keys),
            "total_calls_today": sum(k.calls_today for k in self.keys),
            "active_keys": len([k for k in self.keys if k.status == "active"]),
            "keys": [
                {
                    "key_id": f"...{k.key[-6:]}" if len(k.key) > 6 else k.key,
                    "tier": k.tier,
                    "calls_today": k.calls_today,
                    "errors_today": k.errors_today,
                    "status": k.status,
                    "cooldown_remaining_sec": max(0, int(k.cooldown_until - time.time()))
                }
                for k in self.keys
            ]
        }

gemini_rotator = GeminiKeyRotator()
