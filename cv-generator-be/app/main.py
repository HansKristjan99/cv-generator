import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import cv, cv_edit, cv_invent, cv_sessions, memory, templates, users, billing
from app.config import LOG_FORMAT, settings


def _configure_logging() -> None:
    """Configure the root logger from LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)."""
    raw_level = (settings.log_level or "INFO").strip().upper()
    if raw_level == "WARN":
        raw_level = "WARNING"
    level = logging.getLevelName(raw_level)
    if not isinstance(level, int):
        level = logging.INFO

    logging.basicConfig(level=level, format=LOG_FORMAT)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(level)
    logging.getLogger(__name__).info("Logging configured at level %s", raw_level)


_configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.clerk_authorized_parties or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cv.router)
app.include_router(cv_edit.router)
app.include_router(cv_sessions.router)
app.include_router(cv_invent.router)
app.include_router(memory.router)
app.include_router(templates.router)
app.include_router(users.router)
app.include_router(billing.router)


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    start = time.perf_counter()
    logger.info("--> %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.exception("!!! %s %s failed after %.1fms", request.method, request.url.path, elapsed_ms)
        raise
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "<-- %s %s %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "cv-generator-be is running"}
