"""Process-local credential rotation; quotas are shared within each configured project."""

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import RLock

import httpx

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class KeyState:
    key: str = field(repr=False)
    project: str = "unassigned"
    calls_today: int = 0
    errors_today: int = 0
    cooldown_until: float = 0.0
    status: str = "active"


class GeminiKeyRotator:
    def __init__(self):
        raw_keys = [k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()]
        projects = [p.strip() for p in settings.GEMINI_KEY_PROJECTS.split(",")]
        if not settings.GEMINI_KEY_PROJECTS.strip():
            projects = ["unassigned"] * len(raw_keys)
        if len(projects) != len(raw_keys) or any(not p for p in projects):
            raise ValueError("GEMINI_KEY_PROJECTS must contain one non-empty label per API key.")
        unique = {}
        for key, project in zip(raw_keys, projects, strict=True):
            if key in unique and unique[key] != project:
                raise ValueError("Duplicate Gemini credentials must have the same project label.")
            unique[key] = project
        self.keys = [KeyState(key=k, project=p) for k, p in unique.items()]
        self._current_index = 0
        self._last_reset_day = datetime.now(timezone.utc).date()
        self._lock = RLock()

    def _refresh(self):
        today = datetime.now(timezone.utc).date()
        if today != self._last_reset_day:
            self._last_reset_day = today
            for state in self.keys:
                state.calls_today = state.errors_today = 0
        for state in self.keys:
            if state.status == "cooldown" and state.cooldown_until <= time.monotonic():
                state.status = "active"

    def get_active_key(self, task_type="heavy", exclude=()):
        with self._lock:
            self._refresh()
            for offset in range(len(self.keys)):
                index = (self._current_index + offset) % len(self.keys)
                state = self.keys[index]
                if state.status == "active" and state.key not in exclude:
                    self._current_index = (index + 1) % len(self.keys)
                    return state.key
        return None

    def report_success(self, key):
        with self._lock:
            self._refresh()
            for state in self.keys:
                if state.key == key:
                    state.calls_today += 1
                    # Do not undo a concurrent request's cooldown/credential rejection.
                    break

    def report_error(self, key, status_code=429, retry_after=None):
        with self._lock:
            self._refresh()
            project = None
            for state in self.keys:
                if state.key == key:
                    project = state.project
                    state.errors_today += 1
                    if status_code in (401, 403):
                        state.status = "disabled"
                    break
            if status_code == 429 and project is not None:
                delay = max(60.0, retry_after or 0.0)
                # Unlabelled credentials conservatively share a single quota group.
                for state in self.keys:
                    if state.project == project and state.status != "disabled":
                        state.cooldown_until = max(state.cooldown_until, time.monotonic() + delay)
                        state.status = "cooldown"
                logger.warning("Gemini quota reached; project credential group paused.")

    def post(self, url, payload):
        """At most three attempts, fallback only for credential rejection or a different project quota."""
        tried = set()
        deadline = time.monotonic() + 50.0
        response = None
        key = None
        for _ in range(3):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            key = self.get_active_key(exclude=tried)
            if not key:
                break
            tried.add(key)
            response = httpx.post(
                url, headers={"x-goog-api-key": key}, json=payload, timeout=remaining
            )
            if response.status_code == 200:
                return response, key
            self.report_error(
                key, response.status_code, _retry_after(response.headers.get("Retry-After"))
            )
            if response.status_code not in (401, 403, 429):
                break
        return response, key

    def get_status(self):
        with self._lock:
            self._refresh()
            return {
                "total_keys": len(self.keys),
                "total_calls_today": sum(k.calls_today for k in self.keys),
                "active_keys": sum(k.status == "active" for k in self.keys),
                "keys": [
                    {
                        "key_id": f"credential-{i + 1}",
                        "calls_today": k.calls_today,
                        "errors_today": k.errors_today,
                        "status": k.status,
                        "cooldown_remaining_sec": max(
                            0, math.ceil(k.cooldown_until - time.monotonic())
                        ),
                    }
                    for i, k in enumerate(self.keys)
                ],
            }


def _retry_after(value):
    if not value:
        return None
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (ValueError, TypeError, OverflowError):
            return None
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


gemini_rotator = GeminiKeyRotator()
