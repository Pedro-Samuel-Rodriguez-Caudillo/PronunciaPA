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
    """Construir y devolver la aplicación HTTP del proyecto.

    Explicación sencilla
    --------------------
    Aquí se creará la app (por ejemplo, con FastAPI) y se registrarán las
    rutas. De momento no hay implementación; solo dejamos claro el propósito
    para que cualquier persona nueva entienda qué va aquí.
    """
    raise NotImplementedError("HTTP app sin implementar (contrato únicamente)")
