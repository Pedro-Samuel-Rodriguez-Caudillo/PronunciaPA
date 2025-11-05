"""Esqueleto de API HTTP.

Estado: Implementación pendiente (contratos de endpoints por definir).

TODO (Issue #18)
----------------
- Definir `GET /health` y `POST /v1/compare` (formas de payload/respuesta).
- Establecer manejo de errores y mapeo a códigos HTTP.
- Preparar hooks de instrumentación (Observer) para métricas.
"""
from __future__ import annotations

from typing import Any


def get_app() -> Any:
    """Devuelve una app HTTP (stub)."""
    raise NotImplementedError("HTTP app sin implementar (contrato únicamente)")
