"""Endpoint /v1/drills — genera ejercicios a partir de errores."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ipa_core.analysis.drill_generator import generate_drills_from_errors
from ipa_core.types import EditOp

logger = logging.getLogger("ipa_server")

router = APIRouter(prefix="/v1", tags=["drills"])


# ── Request / Response models ──────────────────────────────────────────

class DrillsRequest(BaseModel):
    """Cuerpo de la petición para generar drills."""

    ops: List[Dict[str, Any]] = Field(
        ...,
        description="Lista de EditOps devueltas por /v1/compare",
        json_schema_extra={"example": [
            {"op": "sub", "ref": "ɾ", "hyp": "r"},
            {"op": "eq", "ref": "a", "hyp": "a"},
        ]},
    )
    lang: str = Field(
        "es",
        description="Código de idioma (es, en, en-us, es-mx)",
        json_schema_extra={"example": "es"},
    )
    max_drills: int = Field(5, ge=1, le=20, description="Máximo de ejercicios")


class MinimalPairOut(BaseModel):
    word_a: str
    word_b: str
    ipa_a: str = ""
    ipa_b: str = ""
    target_phone: str
    contrast_phone: str
    position: str = "medial"


class DrillItemOut(BaseModel):
    text: str
    ipa: str
    target_phones: List[str] = []
    difficulty: int = 1
    hints: List[str] = []


class DrillSetOut(BaseModel):
    name: str
    description: str
    lang: str
    target_phones: List[str] = []
    items: List[DrillItemOut] = []
    minimal_pairs: List[MinimalPairOut] = []
    total: int = Field(0, description="Número total de ejercicios + pares mínimos")


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/drills",
    response_model=DrillSetOut,
    summary="Genera ejercicios de pronunciación a partir de errores",
    description=(
        "Recibe las operaciones de edición (ops) del endpoint /v1/compare "
        "y genera un DrillSet con ejercicios focalizados en las confusiones "
        "fonéticas más impactantes del usuario."
    ),
)
async def generate_drills(body: DrillsRequest) -> DrillSetOut:
    """Genera drills a partir de los errores del comparador."""
    ops: list[EditOp] = []
    for raw in body.ops:
        op_val = raw.get("op", "eq")
        if op_val not in ("eq", "sub", "ins", "del"):
            continue
        ops.append(EditOp(
            op=op_val,  # type: ignore[arg-type]
            ref=raw.get("ref"),
            hyp=raw.get("hyp"),
        ))

    drill_set = generate_drills_from_errors(
        ops,
        lang=body.lang,
        max_drills=body.max_drills,
    )

    data = drill_set.to_dict()
    data["total"] = len(drill_set)

    return DrillSetOut(**data)


@router.get(
    "/drills/preview",
    response_model=DrillSetOut,
    summary="Preview rápido de drills con errores inline",
    description="Versión GET para pruebas rápidas con errores en query.",
)
async def preview_drills(
    errors: str = Query(
        ...,
        description="Errores en formato ref:hyp separados por coma, ej: ɾ:r,s:θ",
        json_schema_extra={"example": "ɾ:r,s:θ"},
    ),
    lang: str = Query("es", description="Código de idioma"),
) -> DrillSetOut:
    """Genera drills desde string de errores (para pruebas rápidas)."""
    ops: list[EditOp] = []
    for pair in errors.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        ref, hyp = pair.split(":", 1)
        ops.append(EditOp(op="sub", ref=ref.strip(), hyp=hyp.strip()))

    drill_set = generate_drills_from_errors(ops, lang=lang)
    data = drill_set.to_dict()
    data["total"] = len(drill_set)
    return DrillSetOut(**data)
