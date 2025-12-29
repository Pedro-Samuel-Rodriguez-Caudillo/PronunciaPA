"""Aplicación HTTP basada en FastAPI.

Este módulo define la API REST para interactuar con el microkernel de
PronunciaPA.
"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path
from typing import Any, List, Optional
from fastapi import FastAPI, File, Form, UploadFile, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ipa_core.config import loader
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.errors import KernelError, ValidationError, NotReadyError
from ipa_core.types import AudioInput


class ASRResponse(BaseModel):
    """Respuesta exitosa de transcripción."""
    ipa: str = Field(..., description="Transcripción completa en formato IPA", json_schema_extra={"example": "o l a"})
    tokens: List[str] = Field(..., description="Lista de tokens fonéticos extraídos", json_schema_extra={"example": ["o", "l", "a"]})
    lang: str = Field(..., description="Código de idioma utilizado", json_schema_extra={"example": "es"})
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales del backend")


class EditOp(BaseModel):
    """Operación de edición individual."""
    op: str = Field(..., description="Tipo de operación (eq, sub, ins, del)", json_schema_extra={"example": "sub"})
    ref: Optional[str] = Field(None, description="Token de referencia", json_schema_extra={"example": "o"})
    hyp: Optional[str] = Field(None, description="Token de la hipótesis", json_schema_extra={"example": "u"})


class CompareResponse(BaseModel):
    """Respuesta exitosa de comparación."""
    per: float = Field(..., description="Phone Error Rate (0.0 a 1.0)", json_schema_extra={"example": 0.15})
    ops: List[EditOp] = Field(..., description="Lista de operaciones de edición realizadas")
    alignment: List[List[Optional[str]]] = Field(
        ..., 
        description="Pares de tokens alineados [ref, hyp]",
        json_schema_extra={"example": [["h", "h"], ["o", "u"]]}
    )
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales de la comparación")


def _get_kernel() -> Kernel:
    """Carga la configuración y crea el kernel (Inyectable)."""
    try:
        cfg = loader.load_config()
        return create_kernel(cfg)
    except KernelError as e:
        # Fallback para errores de inicialización pesados
        raise e


def get_app() -> FastAPI:
    """Construye y configura la aplicación FastAPI."""
    app = FastAPI(
        title="PronunciaPA API",
        description="API para reconocimiento y evaluación fonética",
        version="0.1.0"
    )

    # Configurar CORS
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

    # Handlers de excepciones
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "validation_error"},
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

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Endpoint de salud para monitoreo."""
        return {"status": "ok"}

    async def _process_upload(audio: UploadFile) -> Path:
        """Guarda un UploadFile en un archivo temporal y retorna su ruta."""
        suffix = Path(audio.filename).suffix if audio.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            return Path(tmp.name)

    @app.post("/v1/transcribe", response_model=ASRResponse)
    async def transcribe(
        audio: UploadFile = File(..., description="Archivo de audio a transcribir"),
        lang: str = Form("es", description="Idioma del audio"),
        kernel: Kernel = Depends(_get_kernel)
    ) -> dict[str, Any]:
        """Transcripción de audio a IPA usando el microkernel."""
        tmp_path = await _process_upload(audio)
        try:
            await kernel.setup()
            audio_in: AudioInput = {"path": str(tmp_path), "sample_rate": 16000, "channels": 1}
            # El kernel no tiene transcribe directo, orquestamos pre + asr como en el CLI
            processed = await kernel.pre.process_audio(audio_in)
            res = await kernel.asr.transcribe(processed, lang=lang)
            return {
                "ipa": " ".join(res["tokens"]),
                "tokens": res["tokens"],
                "lang": lang,
                "meta": res.get("meta", {})
            }
        finally:
            await kernel.teardown()
            if tmp_path.exists():
                tmp_path.unlink()

    @app.post("/v1/compare", response_model=CompareResponse)
    async def compare(
        audio: UploadFile = File(..., description="Archivo de audio a comparar"),
        text: str = Form(..., description="Texto de referencia"),
        lang: str = Form("es", description="Idioma del audio"),
        kernel: Kernel = Depends(_get_kernel)
    ) -> dict[str, Any]:
        """Comparación de audio contra texto de referencia usando el microkernel."""
        tmp_path = await _process_upload(audio)
        try:
            await kernel.setup()
            audio_in: AudioInput = {"path": str(tmp_path), "sample_rate": 16000, "channels": 1}
            res = await kernel.run(audio=audio_in, text=text, lang=lang)
            return res
        finally:
            await kernel.teardown()
            if tmp_path.exists():
                tmp_path.unlink()

    return app
