"""Descubrimiento de plugins disponibles.

Busca plugins instalados via entry points y los clasifica por categoría.
"""
from __future__ import annotations

import importlib.metadata
from typing import Mapping


def iter_plugin_entry_points():
    """Yields (category, name, entry_point) for all discovered plugins."""
    # Python 3.9 compatibility
    eps = importlib.metadata.entry_points()
    
    plugins = []
    if hasattr(eps, "select"):
        plugins = eps.select(group="pronunciapa.plugins")
    elif isinstance(eps, dict):
        plugins = eps.get("pronunciapa.plugins", [])
    
    for ep in plugins:
        if "." in ep.name:
            category, name = ep.name.split(".", 1)
            yield category, name, ep


def available_plugins() -> Mapping[str, list[str]]:
    """Retorna un índice por tipo -> lista de nombres.

    Tipos: "asr", "textref", "comparator", "preprocessor".
    Busca entry points en el grupo 'pronunciapa.plugins'.
    Formato esperado del nombre: 'categoria.nombre_plugin'.
    """
    results: dict[str, list[str]] = {
        "asr": [],
        "textref": [],
        "comparator": [],
        "preprocessor": []
    }

    for category, name, _ in iter_plugin_entry_points():
        if category in results:
            results[category].append(name)

    return results
