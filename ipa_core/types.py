"""Tipos compartidos para el microkernel.

Descripción
-----------
Define tipos inmutables para el intercambio de datos entre puertos y el
`Kernel`.

Estado: Implementación pendiente de validación (si se adopta un validador de esquemas).

TODO (Issue #18)
----------------
- Alinear `CompareWeights` con claves externas (YAML) mapeando `del -> del_`.
- Incorporar tipos de dominio para audio (bit depth, formato de contenedor).
- Establecer versiones de esquema en los `TypedDict` si evoluciona el contrato.
- Considerar uso de `typing_extensions`/`pydantic` si se requiere validación.
"""
from __future__ import annotations

from typing import Any, Literal, Optional, Sequence, TypedDict


Token = str
TokenSeq = Sequence[Token]


class AudioInput(TypedDict):
    path: str
    sample_rate: int
    channels: int


class ASRResult(TypedDict, total=False):
    tokens: list[Token]
    raw_text: str
    time_stamps: list[tuple[float, float]]
    meta: dict[str, Any]


class CompareWeights(TypedDict, total=False):
    sub: float
    ins: float
    del_: float  # alias interno para "del"


class EditOp(TypedDict):
    op: Literal["eq", "sub", "ins", "del"]
    ref: Optional[Token]
    hyp: Optional[Token]


class CompareResult(TypedDict, total=False):
    per: float
    ops: list[EditOp]
    alignment: list[tuple[Optional[Token], Optional[Token]]]
    meta: dict[str, Any]


class RunOptions(TypedDict, total=False):
    lang: Optional[str]
    weights: CompareWeights
