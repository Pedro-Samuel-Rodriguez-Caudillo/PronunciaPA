"""IPA sound catalog loader and helpers.

El catálogo es agnóstico al idioma: soportar un nuevo idioma requiere
únicamente añadir un ``{lang}.yaml`` (y opcionalmente ``{lang}_learning.yaml``)
en el directorio de catálogos (``data/ipa_catalog/``).
"""
from __future__ import annotations

import functools
from pathlib import Path
import os
from typing import Any, Optional

import yaml

_CATALOG_ENV = "PRONUNCIAPA_IPA_CATALOG_DIR"


def normalize_lang(lang: str) -> str:
    """Normalize language code to base form (e.g., es-MX -> es)."""
    return (lang or "").strip().lower().split("-")[0]


def resolve_catalog_dir() -> Path:
    """Resolve catalog directory from env, cwd, or repo root."""
    env = os.getenv(_CATALOG_ENV)
    if env:
        return Path(env)
    cwd_candidate = Path.cwd() / "data" / "ipa_catalog"
    if cwd_candidate.exists():
        return cwd_candidate
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "data" / "ipa_catalog"


def available_languages() -> list[str]:
    """Return list of languages that have a catalog file."""
    catalog_dir = resolve_catalog_dir()
    if not catalog_dir.exists():
        return []
    return sorted(
        p.stem for p in catalog_dir.glob("*.yaml")
        if not p.stem.endswith("_learning") and not p.stem.endswith("_inventory")
    )


@functools.lru_cache(maxsize=32)
def load_catalog(lang: str) -> dict[str, Any]:
    """Load the catalog for a given language (cached)."""
    lang_key = normalize_lang(lang)
    catalog_dir = resolve_catalog_dir()
    path = catalog_dir / f"{lang_key}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"IPA catalog not found: {path}. "
            f"Available: {available_languages()}"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid catalog format for {lang_key}")
    return data


@functools.lru_cache(maxsize=32)
def load_inventory(lang: str) -> dict[str, Any]:
    """Load the inventory file for a given language (cached)."""
    lang_key = normalize_lang(lang)
    catalog_dir = resolve_catalog_dir()
    # Try dialect-specific first, then generic
    for suffix in (f"{lang_key}_inventory", f"{lang}_inventory"):
        path = catalog_dir / f"{suffix}.yaml"
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    raise FileNotFoundError(f"Inventory not found for {lang_key}")


def list_sounds(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the sound entries from a catalog."""
    sounds = catalog.get("sounds", [])
    if not isinstance(sounds, list):
        return []
    return [s for s in sounds if isinstance(s, dict)]


def resolve_sound_entry(catalog: dict[str, Any], query: str) -> Optional[dict[str, Any]]:
    """Resolve a sound entry by IPA, id, label, or alias."""
    if not query:
        return None
    needle = query.strip().lower()
    for entry in list_sounds(catalog):
        candidates = [
            entry.get("id"),
            entry.get("ipa"),
            entry.get("label"),
        ]
        aliases = entry.get("aliases", [])
        if isinstance(aliases, list):
            candidates.extend(aliases)
        for value in candidates:
            if value and str(value).strip().lower() == needle:
                return entry
    return None
