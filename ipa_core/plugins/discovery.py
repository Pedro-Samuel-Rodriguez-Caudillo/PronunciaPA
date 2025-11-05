"""Descubrimiento de plugins disponibles (stub).

Estado: Implementación pendiente (enumeración de entry points/registro).

TODO
----
- Descubrir via entry points e incluir metadatos (versiones, proveedor).
- Exponer un índice cacheable y actualizable en caliente.
"""
from __future__ import annotations

from typing import Mapping


def available_plugins() -> Mapping[str, list[str]]:
    """Retorna un índice por tipo -> lista de nombres.

    Tipos: "asr", "textref", "comparator", "preprocessor".
    """
    return {"asr": [], "textref": [], "comparator": [], "preprocessor": []}
