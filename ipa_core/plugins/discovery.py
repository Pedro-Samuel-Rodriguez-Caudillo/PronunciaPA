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

    Tipos: "asr", "textref", "comparator", "preprocessor", "tts".
    Busca entry points en el grupo 'pronunciapa.plugins'.
    Formato esperado del nombre: 'categoria.nombre_plugin'.
    """
    results: dict[str, list[str]] = {
        "asr": [],
        "textref": [],
        "comparator": [],
        "preprocessor": [],
        "tts": [],
    }

    for category, name, _ in iter_plugin_entry_points():
        if category in results:
            results[category].append(name)

    return results


def get_package_metadata(package_name: str) -> dict[str, str]:
    """Extrae metadatos básicos de un paquete instalado."""
    try:
        meta = importlib.metadata.metadata(package_name)
        return {
            "version": meta.get("Version", "unknown"),
            "author": meta.get("Author", "unknown"),
            "description": meta.get("Summary", "No description provided.")
        }
    except importlib.metadata.PackageNotFoundError:
        return {
            "version": "unknown",
            "author": "unknown",
            "description": "Package not found."
        }


def get_plugin_details(category: str, name: str) -> dict[str, str]:
    """Retorna detalles de un plugin específico buscando su entry point."""
    for cat, n, ep in iter_plugin_entry_points():
        if cat == category and n == name:
            # Intentar deducir el paquete desde el entry point
            # ep.value suele ser 'package.module:attr'
            package_name = ep.value.split(".")[0].split(":")[0]
            details = get_package_metadata(package_name)
            details.update({
                "category": category,
                "name": name,
                "entry_point": ep.value
            })
            return details
    return {}
