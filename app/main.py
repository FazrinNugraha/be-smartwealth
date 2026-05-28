"""
SmartWealth Backend — FastAPI Application Entry Point

Run with: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.routers import (
    auth,
    users,
    assets,
    transactions,
    prices,
    dashboard,
    insights,
    predictions,
)  # Import routers
from app.tasks import wealth_snapshot_job, price_updater_job
from app.utils.exceptions import SmartWealthException

# ── Background Scheduler ─────────────────────────────────────
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # ── Startup ──
    print(f"[START] SmartWealth API starting in {settings.APP_ENV} mode...")

    # Setup background jobs
    print("[SCHEDULER] Setting up background jobs...")

    # Job 1: Wealth snapshot (daily at 00:00)
    scheduler.add_job(
        wealth_snapshot_job,
        trigger="cron",
        hour=0,
        minute=0,
        id="wealth_snapshot",
        name="Daily Wealth Snapshot",
        replace_existing=True,
    )
    print("[SCHEDULER] ✓ Wealth snapshot job scheduled (daily at 00:00)")

    # Job 2: Price updater (every 5 minutes)
    scheduler.add_job(
        price_updater_job,
        trigger="interval",
        minutes=5,
        id="price_updater",
        name="Price Updater",
        replace_existing=True,
    )
    print("[SCHEDULER] ✓ Price updater job scheduled (every 5 minutes)")

    # Start scheduler
    scheduler.start()
    print("[SCHEDULER] Background jobs started!")

    yield

    # ── Shutdown ──
    print("[STOP] SmartWealth API shutting down...")
    scheduler.shutdown()
    print("[SCHEDULER] Background jobs stopped.")


app = FastAPI(
    title="SmartWealth API",
    description="Advanced Multi-Asset Portfolio Tracker & AI Insight Engine",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception Handlers ───────────────────────────────────────
@app.exception_handler(SmartWealthException)
async def smartwealth_exception_handler(request: Request, exc: SmartWealthException):
    """Handle custom SmartWealth exceptions"""
    content = {
        "error": exc.error_code or "ERROR",
        "message": exc.detail,
        "path": str(request.url.path),
    }
    if exc.details is not None:
        content["details"] = exc.details

    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": errors,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    # Log error (in production, use proper logging)
    print(f"[ERROR] Unexpected error: {exc}")
    import traceback

    traceback.print_exc()

    # Don't expose internal errors in production
    if settings.is_production:
        detail = "An unexpected error occurred. Please try again later."
    else:
        detail = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": detail,
            "path": str(request.url.path),
        },
    )


# ── Routers ──────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(assets.router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(
    transactions.router, prefix="/api/v1/transactions", tags=["Transactions"]
)
app.include_router(prices.router, prefix="/api/v1/prices", tags=["Prices"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(insights.router, prefix="/api/v1/insights", tags=["Insights"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])


# ── Health Check ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "app": "SmartWealth API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "environment": settings.APP_ENV}


@app.get("/api/v1/health/db", tags=["Health"])
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Test database connectivity."""
    result = await db.execute(text("SELECT 1"))
    return {"database": "connected", "result": result.scalar()}
