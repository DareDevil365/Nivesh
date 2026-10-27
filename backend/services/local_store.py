"""Durable SQLite storage for anonymous browser workspaces; no shared default user."""

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from fastapi import Request, Response

DATA_DIR = Path(os.getenv("NIVESH_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data")))
COOKIE = "nivesh_workspace"
_secret_lock = threading.Lock()


def secret():
    configured = os.getenv("SESSION_SECRET")
    if configured:
        if len(configured) < 32:
            raise RuntimeError("SESSION_SECRET must be at least 32 characters.")
        return configured.encode()
    with _secret_lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / ".session_secret"
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as f:
                f.write(secrets.token_hex(32).encode())
        except FileExistsError:
            pass
        value = path.read_bytes()
        if len(value) < 32:
            raise RuntimeError(
                "Local session secret is incomplete. Configure SESSION_SECRET to restore service."
            )
        return value


def workspace(request: Request, response: Response):
    token = request.cookies.get(COOKIE, "")
    identifier, _, signature = token.partition(".")
    expected = hmac.new(secret(), identifier.encode(), hashlib.sha256).hexdigest()
    if len(identifier) != 64 or not hmac.compare_digest(signature, expected):
        identifier = secrets.token_hex(32)
        signature = hmac.new(secret(), identifier.encode(), hashlib.sha256).hexdigest()
        response.set_cookie(
            COOKIE,
            f"{identifier}.{signature}",
            httponly=True,
            secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            samesite="lax",
            max_age=365 * 86400,
            path="/",
        )
    return hashlib.sha256(identifier.encode()).hexdigest()


@contextmanager
def connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DATA_DIR / "nivesh.sqlite3"), timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS watchlist (owner TEXT NOT NULL, name TEXT NOT NULL, ticker TEXT NOT NULL, added_at TEXT NOT NULL, PRIMARY KEY(owner,name,ticker));
            CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, owner TEXT NOT NULL, ticker TEXT NOT NULL, condition TEXT NOT NULL, threshold REAL NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, owner TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS market_snapshots (ticker TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at REAL NOT NULL);
        """)
        yield db
        db.commit()
    finally:
        db.close()
