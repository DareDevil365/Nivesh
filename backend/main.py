from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from routers import (
    backtest,
    behavior,
    companies,
    developments,
    learning,
    news,
    reports,
    research,
    screener,
    watchlist,
)
from services.data_fetcher import MarketDataUnavailable
from services.local_store import workspace

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Nivesh Backend — NSE Equity Research, Backtesting & Behavior Analysis Platform",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.FRONTEND_URL.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(developments.router)
app.include_router(news.router)
app.include_router(learning.router)
app.include_router(screener.router)
app.include_router(watchlist.router)
app.include_router(backtest.router)
app.include_router(behavior.router)
app.include_router(research.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "data_note": "Yahoo Finance provider data may be delayed; inspect quote timestamps.",
    }


@app.get("/health")
def healthcheck():
    from datetime import datetime, timezone

    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/workspace")
def get_workspace(owner=Depends(workspace)):
    return {
        "storage": "browser_workspace",
        "note": "Saved locally on the server and isolated by a signed browser cookie. No cross-device account sync.",
    }


@app.middleware("http")
async def response_safety(request: Request, call_next):
    # Keep accidental oversized JSON uploads out of parsers.
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > 3_000_000):
        return JSONResponse({"detail": "Request exceeds the 3 MB limit."}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith(
        ("/api/watchlist", "/api/alerts", "/api/reports", "/api/workspace")
    ):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(MarketDataUnavailable)
async def market_unavailable(request: Request, exc: MarketDataUnavailable):
    return JSONResponse({"detail": str(exc)}, status_code=503)


@app.exception_handler(ValueError)
async def invalid_input(request: Request, exc: ValueError):
    return JSONResponse({"detail": str(exc)}, status_code=422)
