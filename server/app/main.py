"""SurakshaX API server. Run locally: `uvicorn app.main:app --reload` from the server/ folder."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from . import config
from .db import engine, init_db
from .routers import admin, auth, safety, sos

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("surakshax")


def _warm_models():
    """Load the risk and voice models in the background so the first request is fast."""
    try:
        from .services.risk import get_crime_predictor
        from .services.voice import get_voice_classifier

        get_crime_predictor()
        get_voice_classifier().model_info()
        log.info("Models loaded")
    except Exception:
        log.exception("Model warm-up failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if config.JWT_SECRET_IS_EPHEMERAL:
        log.warning("JWT_SECRET is not set: logins will stop working after every restart")
    if not config.ADMIN_PASSWORD:
        log.warning("ADMIN_PASSWORD is not set: /police_dashboard is disabled")
    threading.Thread(target=_warm_models, daemon=True).start()
    yield


app = FastAPI(title="SurakshaX API", version=config.APP_VERSION, lifespan=lifespan)
# Render terminates TLS at its proxy; trust X-Forwarded-Proto so tracking links use https://
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# The app reads {"success": false, "error": "..."} from failed requests
@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    return JSONResponse(
        {"success": False, "error": exc.detail, "detail": exc.detail},
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:])
    message = f"{field}: {first.get('msg', 'invalid value')}" if field else "Invalid request"
    return JSONResponse({"success": False, "error": message, "detail": exc.errors()}, status_code=422)


@app.exception_handler(Exception)
async def server_error(_request: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse({"success": False, "error": "Server error, please try again"}, status_code=500)


@app.get("/", include_in_schema=False)
def root():
    return {"service": "SurakshaX API", "version": config.APP_VERSION, "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "version": config.APP_VERSION,
        "database": database,
        "twilio": config.TWILIO_ENABLED,
    }


app.include_router(auth.router)
app.include_router(safety.router)
app.include_router(sos.router)
app.include_router(admin.router)
