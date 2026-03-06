"""Aplicacion HTTP basada en FastAPI.

Este modulo define la API REST para interactuar con el microkernel de
PronunciaPA.  Las rutas estan organizadas en modulos separados bajo
``ipa_server.routers``.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
import warnings
from datetime import datetime
from typing import Any

# Suppress pydub's "Couldn't find ffmpeg" RuntimeWarning that fires on import.
# The real ffmpeg path is configured below in _configure_ffmpeg() once all
# modules are loaded.
warnings.filterwarnings("ignore", message=".*ffmpeg.*", category=RuntimeWarning, module="pydub")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ipa_core.errors import (
    AudioFormatError,
    FileNotFound,
    KernelError,
    LLMAPIError,
    LLMTimeoutError,
    ModelLoadError,
    NotReadyError,
    UnsupportedFormat,
    ValidationError,
)
from ipa_server.realtime import realtime_router
from ipa_server.routers.debug import router as debug_router
from ipa_server.routers.drills import router as drills_router
from ipa_server.routers.health import router as health_router
from ipa_server.routers.history import router as history_router
from ipa_server.routers.ipa_catalog import router as ipa_catalog_router
from ipa_server.routers.lesson_plan import router as lesson_plan_router
from ipa_server.routers.models import router as models_router
from ipa_server.routers.pipeline import router as pipeline_router, teardown_kernel_singleton
from ipa_server.routers.prosody import router as prosody_router
from ipa_server.routers.record import router as record_router
from ipa_server.routers.tts import router as tts_router

logger = logging.getLogger("ipa_server")


def _configure_ffmpeg() -> None:
    """Locate ffmpeg and configure pydub's converter to a real binary."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        # Try imageio-ffmpeg bundled binary (installed in the venv)
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

    if ffmpeg_path is None:
        # Common Windows install locations (winget / manual)
        candidates = [
            r"C:\ffmpeg\ffmpeg.exe",
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                ffmpeg_path = c
                break

    if ffmpeg_path:
        try:
            from pydub import AudioSegment
            AudioSegment.converter = ffmpeg_path
            logger.info("ffmpeg configured: %s", ffmpeg_path)
        except Exception:
            pass
    else:
        logger.warning(
            "ffmpeg not found. Audio format conversion (non-WAV) will be unavailable. "
            "Install ffmpeg and add it to PATH: https://ffmpeg.org/download.html"
        )


_configure_ffmpeg()


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

    @app.exception_handler(AudioFormatError)
    async def audio_format_exception_handler(request: Request, exc: AudioFormatError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "audio_format_error"},
        )

    @app.exception_handler(ModelLoadError)
    async def model_load_exception_handler(request: Request, exc: ModelLoadError):
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "type": "model_load_error"},
        )

    @app.exception_handler(LLMTimeoutError)
    async def llm_timeout_exception_handler(request: Request, exc: LLMTimeoutError):
        return JSONResponse(
            status_code=504,
            content={"detail": str(exc), "type": "llm_timeout_error"},
        )

    @app.exception_handler(LLMAPIError)
    async def llmapi_exception_handler(request: Request, exc: LLMAPIError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "type": "llm_api_error"},
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

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        """Tear down the /v1/quick-compare kernel singleton on server stop."""
        await teardown_kernel_singleton()

    return app


# Instancia global para uvicorn
app = get_app()
