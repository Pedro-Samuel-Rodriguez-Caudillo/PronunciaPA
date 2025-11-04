"""Descubrimiento de plugins disponibles (stub)."""
from __future__ import annotations

from typing import Mapping


def available_plugins() -> Mapping[str, list[str]]:
    """Retorna un índice por tipo -> lista de nombres.

    Tipos: "asr", "textref", "comparator", "preprocessor".
    """
    return {"asr": [], "textref": [], "comparator": [], "preprocessor": []}

