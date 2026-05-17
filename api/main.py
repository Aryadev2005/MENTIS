"""MENTIS — FastAPI Application Entry Point."""

import time
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .database.postgres import init_db, close_db
from .database.redis_client import init_redis, close_redis
from .database.qdrant_init import init_qdrant
from .routers.interview_router import router as interview_router
from .routers.oa_router import router as oa_router
from .routers.user_router import router as user_router
from .routers.analytics_router import router as analytics_router
from .routers.transcription_router import router as transcription_router
from .routers.payment_router import router as payment_router
from .services.self_learning import start_scheduler
from .services.observability import setup_langsmith
from .middleware.security import SecurityMiddleware
from .config import settings

logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("MENTIS API starting up", version="1.0.0")

    await init_db()
    logger.info("PostgreSQL connected")

    await init_redis()
    logger.info("Redis connected")

    await init_qdrant()
    logger.info("Qdrant initialized")

    start_scheduler()
    logger.info("APScheduler started")

    setup_langsmith(api_key=getattr(settings, "LANGSMITH_API_KEY", None))
    logger.info("LangSmith tracing configured")

    yield

    logger.info("MENTIS API shutting down")
    await close_db()
    await close_redis()


app = FastAPI(
    title="MENTIS API",
    description="India's most advanced real-time AI career intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "app://.",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityMiddleware)


@app.middleware("http")
async def add_latency_header(request: Request, call_next: object) -> Response:
    start = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    response.headers["X-Powered-By"] = "MENTIS"
    return response


@app.middleware("http")
async def sanitize_request(request: Request, call_next: object) -> Response:
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body = await request.body()
                if len(body) > 10 * 1024 * 1024:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request body too large"},
                    )
            except Exception:
                pass
    response: Response = await call_next(request)
    return response


Instrumentator().instrument(app).expose(app)

app.include_router(interview_router, prefix="/api/v1/interview", tags=["interview"])
app.include_router(oa_router, prefix="/api/v1/oa", tags=["oa"])
app.include_router(user_router, prefix="/api/v1/user", tags=["user"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(transcription_router, prefix="/api/v1", tags=["transcription"])
app.include_router(payment_router, prefix="/api/v1/payment", tags=["payment"])


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": "mentis-api",
        "version": "1.0.0",
        "tagline": "Your Unfair Advantage",
    }


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "message": "MENTIS API — Your Unfair Advantage",
        "docs": "/docs",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
