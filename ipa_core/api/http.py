"""Esqueleto de API HTTP.

Evita dependencias (FastAPI) para mantener import seguro.
"""
from __future__ import annotations

from typing import Any


def get_app() -> Any:
    """Devuelve una app HTTP (stub)."""
    raise NotImplementedError("HTTP app sin implementar (contrato únicamente)")

