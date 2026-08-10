from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import companies, screener, watchlist, backtest, behavior, research

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Nivesh Backend — NSE Equity Research, Backtesting & Behavior Analysis Platform"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def normalize_api_path(request: Request, call_next):
    # Ensure request path starts with /api so all APIRouter routes match
    path = request.url.path
    if not path.startswith("/api") and path != "/" and path != "/health":
        request.scope["path"] = "/api" + path
    return await call_next(request)

app.include_router(companies.router)
app.include_router(screener.router)
app.include_router(watchlist.router)
app.include_router(backtest.router)
app.include_router(behavior.router)
app.include_router(research.router)

@app.get("/")
@app.get("/api")
@app.get("/api/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "delayed_badge_note": "NSE data delayed ~15 min"
    }

@app.get("/health")
@app.get("/api/health")
def healthcheck():
    return {"status": "ok", "timestamp": "live"}
