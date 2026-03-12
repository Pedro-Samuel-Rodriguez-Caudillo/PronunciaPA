"""Aplicacion HTTP basada en FastAPI.

Este modulo define la API REST para interactuar con el microkernel de
PronunciaPA.  Las rutas estan organizadas en modulos separados bajo
``ipa_server.routers``.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
import shutil
import time
import warnings
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ipa_core.audio.ffmpeg import find_ffmpeg_binary
from ipa_core.errors import (
    FileNotFound,
    KernelError,
    NotReadyError,
    UnsupportedFormat,
    ValidationError,
)
from ipa_server.http_errors import error_response, from_request, kernel_error_response, validation_error_response
from ipa_server.kernel_provider import teardown_kernel_singleton
from ipa_server.realtime import realtime_router
from ipa_server.routers.debug import router as debug_router
from ipa_server.routers.drills import router as drills_router
from ipa_server.routers.health import router as health_router
from ipa_server.routers.history import router as history_router
from ipa_server.routers.ipa_catalog import router as ipa_catalog_router
from ipa_server.routers.lesson_plan import router as lesson_plan_router
from ipa_server.routers.models import router as models_router
from ipa_server.routers.pipeline import router as pipeline_router
from ipa_server.routers.prosody import router as prosody_router
from ipa_server.routers.record import router as record_router
from ipa_server.routers.tts import router as tts_router

logger = logging.getLogger("ipa_server")


def _configure_runtime_warnings() -> None:
    """Suppress known noisy third-party warnings without hiding real issues."""
    warnings.filterwarnings(
        "ignore",
        message=r'.*"is" with a literal.*Did you mean "=="\?',
        category=SyntaxWarning,
        module=r"allosaurus\.pm\.preprocess",
    )


def _configure_ffmpeg() -> None:
    """Locate ffmpeg and log the resolved binary used by the backend."""
    ffmpeg_path = find_ffmpeg_binary()

    if ffmpeg_path:
        logger.info("ffmpeg configured: %s", ffmpeg_path)
    else:
        logger.warning(
            "ffmpeg not found. Audio format conversion (non-WAV) will be unavailable. "
            "Install imageio-ffmpeg or a system ffmpeg binary."
        )


_configure_ffmpeg()
_configure_runtime_warnings()


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware que agrega headers de timing."""

    async def dispatch(self, request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        response.headers["X-Timestamp"] = datetime.now().isoformat()
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los exception handlers de la aplicacion."""

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        logger.error("Validation error on %s: %s", request.url.path, exc)
        return validation_error_response(request, exc)

    @app.exception_handler(UnsupportedFormat)
    async def unsupported_exception_handler(request: Request, exc: UnsupportedFormat):
        return from_request(
            request,
            status_code=415,
            detail=str(exc),
            error_type="unsupported_format",
        )

    @app.exception_handler(FileNotFound)
    async def file_not_found_handler(request: Request, exc: FileNotFound):
        return from_request(
            request,
            status_code=400,
            detail=str(exc),
            error_type="file_not_found",
        )

    @app.exception_handler(KeyError)
    async def plugin_not_found_handler(request: Request, exc: KeyError):
        return from_request(
            request,
            status_code=400,
            detail=str(exc),
            error_type="plugin_not_found",
        )

    @app.exception_handler(NotReadyError)
    async def not_ready_exception_handler(request: Request, exc: NotReadyError):
        return from_request(
            request,
            status_code=503,
            detail=str(exc),
            error_type="not_ready",
        )

    @app.exception_handler(KernelError)
    async def kernel_exception_handler(request: Request, exc: KernelError):
        return kernel_error_response(request, exc)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        import traceback

        logger.error("Unhandled exception on %s: %s", request.url.path, exc)
        logger.error("Full traceback:\n%s", traceback.format_exc())
        return error_response(
            status_code=500,
            detail=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
        )


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    """Manage app lifecycle resources."""
    try:
        yield
    finally:
        await teardown_kernel_singleton()


def get_app() -> FastAPI:
    """Construye y configura la aplicacion FastAPI."""
    app = FastAPI(
        title="PronunciaPA API",
        description="API para reconocimiento y evaluacion fonetica",
        version="0.1.0",
        lifespan=_app_lifespan,
    )

    # CORS
    raw_origins = os.environ.get("PRONUNCIAPA_ALLOWED_ORIGINS", "")
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    if not allowed_origins and os.environ.get("DEBUG"):
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TimingMiddleware)

    # Exception handlers
    _register_exception_handlers(app)

    # Routers
    app.include_router(health_router)
    app.include_router(debug_router)
    app.include_router(pipeline_router)
    app.include_router(drills_router)
    app.include_router(history_router)
    app.include_router(lesson_plan_router)
    app.include_router(tts_router)
    app.include_router(prosody_router)
    app.include_router(record_router)
    app.include_router(ipa_catalog_router)
    app.include_router(models_router)
    app.include_router(realtime_router)

    return app


# Instancia global para uvicorn
app = get_app()
