"""Aplicacion HTTP basada en FastAPI.

Este modulo define la API REST para interactuar con el microkernel de
PronunciaPA.  Las rutas estan organizadas en modulos separados bajo
``ipa_server.routers``.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ipa_core.errors import (
    FileNotFound,
    KernelError,
    NotReadyError,
    UnsupportedFormat,
    ValidationError,
)
from ipa_server.realtime import realtime_router
from ipa_server.routers.drills import router as drills_router
from ipa_server.routers.health import router as health_router
from ipa_server.routers.ipa_catalog import router as ipa_catalog_router
from ipa_server.routers.models import router as models_router
from ipa_server.routers.pipeline import router as pipeline_router
from ipa_server.routers.tts import router as tts_router

logger = logging.getLogger("ipa_server")


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
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
                "type": "validation_error",
                "path": request.url.path,
            },
        )

    @app.exception_handler(UnsupportedFormat)
    async def unsupported_exception_handler(request: Request, exc: UnsupportedFormat):
        return JSONResponse(
            status_code=415,
            content={"detail": str(exc), "type": "unsupported_format"},
        )

    @app.exception_handler(FileNotFound)
    async def file_not_found_handler(request: Request, exc: FileNotFound):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "file_not_found"},
        )

    @app.exception_handler(KeyError)
    async def plugin_not_found_handler(request: Request, exc: KeyError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "plugin_not_found"},
        )

    @app.exception_handler(NotReadyError)
    async def not_ready_exception_handler(request: Request, exc: NotReadyError):
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "type": "not_ready"},
        )

    @app.exception_handler(KernelError)
    async def kernel_exception_handler(request: Request, exc: KernelError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": "kernel_error"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        import traceback

        logger.error("Unhandled exception on %s: %s", request.url.path, exc)
        logger.error("Full traceback:\n%s", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "path": request.url.path,
            },
        )


def get_app() -> FastAPI:
    """Construye y configura la aplicacion FastAPI."""
    app = FastAPI(
        title="PronunciaPA API",
        description="API para reconocimiento y evaluacion fonetica",
        version="0.1.0",
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
    app.include_router(pipeline_router)
    app.include_router(drills_router)
    app.include_router(tts_router)
    app.include_router(ipa_catalog_router)
    app.include_router(models_router)
    app.include_router(realtime_router)

    return app


# Instancia global para uvicorn
app = get_app()
