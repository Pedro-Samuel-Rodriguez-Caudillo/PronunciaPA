"""Esqueleto de API HTTP.

Estado: Implementación pendiente (contratos de endpoints por definir).

TODO
----
- Definir `GET /health` y `POST /v1/compare` (payload y respuesta enlazados a tipos).
- Establecer manejo de errores y mapeo consistente a códigos HTTP.
- Preparar hooks de instrumentación (Observer) para métricas y trazas.
"""
from __future__ import annotations

from typing import Any


def get_app() -> Any:
    """Devuelve una app HTTP (stub)."""
    raise NotImplementedError("HTTP app sin implementar (contrato únicamente)")
