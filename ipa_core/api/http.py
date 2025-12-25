"""Aplicación HTTP basada en FastAPI.

Este módulo define la API REST para interactuar con el microkernel de
PronunciaPA.
"""
from __future__ import annotations
from typing import Any, List, Optional
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel


class ASRResponse(BaseModel):
    """Respuesta exitosa de transcripción."""
    ipa: str
    tokens: List[str]
    lang: str
    meta: dict[str, Any] = {}


class CompareResponse(BaseModel):
    """Respuesta exitosa de comparación."""
    per: float
    ops: List[dict[str, Any]]
    alignment: List[List[Optional[str]]]
    meta: dict[str, Any] = {}


def get_app() -> FastAPI:
    """Construye y configura la aplicación FastAPI."""
    app = FastAPI(
        title="PronunciaPA API",
        description="API para reconocimiento y evaluación fonética",
        version="0.1.0"
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Endpoint de salud para monitoreo."""
        return {"status": "ok"}

    @app.post("/v1/transcribe", response_model=ASRResponse)
    async def transcribe(
        audio: UploadFile = File(..., description="Archivo de audio a transcribir"),
        lang: str = Form("es", description="Idioma del audio")
    ) -> dict[str, Any]:
        """Stub para transcripción de audio a IPA."""
        # TODO: Implementar integración con el Kernel
        return {
            "ipa": "o l a",
            "tokens": ["o", "l", "a"],
            "lang": lang,
            "meta": {"backend": "stub"}
        }

    @app.post("/v1/compare", response_model=CompareResponse)
    async def compare(
        audio: UploadFile = File(..., description="Archivo de audio a comparar"),
        text: str = Form(..., description="Texto de referencia"),
        lang: str = Form("es", description="Idioma del audio")
    ) -> dict[str, Any]:
        """Stub para comparación de audio contra texto de referencia."""
        # TODO: Implementar integración con el Kernel
        return {
            "per": 0.0,
            "ops": [{"op": "eq", "ref": "o", "hyp": "o"}],
            "alignment": [["o", "o"]],
            "meta": {"backend": "stub"}
        }

    return app