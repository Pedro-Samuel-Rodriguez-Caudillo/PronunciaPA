"""Endpoints de historial y progreso de pronunciación.

Rutas disponibles
-----------------
POST /v1/history/attempts
    Registrar un intento de pronunciación manualmente.
    (La mayoría de los clientes no necesitan esto; el pipeline lo hace auto.)

GET /v1/history/{user_id}/attempts
    Listar intentos paginados de un usuario.

GET /v1/history/{user_id}/phonemes
    Estadísticas de maestría por fonema.

GET /v1/history/{user_id}/summary
    Resumen global de progreso.
"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ipa_server.routers.pipeline import _get_or_create_kernel

router = APIRouter(prefix="/v1/history", tags=["history"])


# ── Pydantic models ───────────────────────────────────────────────────

class RecordAttemptIn(BaseModel):
    user_id: str = Field(..., description="Identificador opaco del usuario")
    lang: str = Field(..., description="Idioma del intento, ej: 'es'")
    text: str = Field(..., description="Texto que el usuario intentó pronunciar")
    score: float = Field(..., ge=0, le=100, description="Puntuación global (0-100)")
    per: float = Field(..., ge=0, le=1, description="Phone Error Rate (0-1)")
    ops: List[dict[str, Any]] = Field(
        default_factory=list,
        description="Operaciones de edición (eq/sub/ins/del)",
    )
    meta: Optional[dict[str, Any]] = Field(
        default=None, description="Metadatos extra opcionales"
    )


class AttemptOut(BaseModel):
    attempt_id: str
    user_id: str
    lang: str
    text: str
    score: float
    per: float
    ops: List[dict[str, Any]]
    timestamp: float
    meta: dict[str, Any] = Field(default_factory=dict)


class PhonemeStatsOut(BaseModel):
    phoneme: str
    attempts: int
    correct: int
    error_rate: float
    mastery_level: str


class SummaryOut(BaseModel):
    total_attempts: int
    avg_score: float
    languages: List[str]
    top_errors: List[str]


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/attempts", response_model=dict[str, str], status_code=201)
async def record_attempt(body: RecordAttemptIn) -> dict[str, str]:
    """Registrar manualmente un intento de pronunciación."""
    kernel = await _get_or_create_kernel()
    if kernel.history is None:
        raise HTTPException(status_code=503, detail="Historial no configurado en el servidor.")
    attempt_id = await kernel.history.record_attempt(
        user_id=body.user_id,
        lang=body.lang,
        text=body.text,
        score=body.score,
        per=body.per,
        ops=body.ops,
        meta=body.meta,
    )
    return {"attempt_id": attempt_id}


@router.get("/{user_id}/attempts", response_model=List[AttemptOut])
async def get_attempts(
    user_id: str,
    lang: Optional[str] = Query(default=None, description="Filtrar por idioma"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Obtener intentos de un usuario, más recientes primero."""
    kernel = await _get_or_create_kernel()
    if kernel.history is None:
        raise HTTPException(status_code=503, detail="Historial no configurado en el servidor.")
    return await kernel.history.get_attempts(
        user_id, lang=lang, limit=limit, offset=offset
    )


@router.get("/{user_id}/phonemes", response_model=List[PhonemeStatsOut])
async def get_phoneme_stats(
    user_id: str,
    lang: str = Query(..., description="Idioma para las estadísticas, ej: 'es'"),
) -> list[dict[str, Any]]:
    """Obtener estadísticas de maestría por fonema (primero los de más error)."""
    kernel = await _get_or_create_kernel()
    if kernel.history is None:
        raise HTTPException(status_code=503, detail="Historial no configurado en el servidor.")
    return await kernel.history.get_phoneme_stats(user_id, lang)


@router.get("/{user_id}/summary", response_model=SummaryOut)
async def get_summary(user_id: str) -> dict[str, Any]:
    """Obtener resumen global de progreso del usuario."""
    kernel = await _get_or_create_kernel()
    if kernel.history is None:
        raise HTTPException(status_code=503, detail="Historial no configurado en el servidor.")
    return await kernel.history.get_summary(user_id)
