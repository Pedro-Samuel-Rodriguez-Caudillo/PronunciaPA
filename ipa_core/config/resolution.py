"""Helpers compartidos para resolver configuracion derivada."""
from __future__ import annotations

import logging
import os
from typing import Optional

from ipa_core.config import loader

logger = logging.getLogger(__name__)


def default_lang_from_config() -> str:
    """Obtiene el idioma por defecto desde config con fallback seguro."""
    try:
        cfg = loader.load_config()
        opt_lang = getattr(cfg.options, "lang", None)
        if isinstance(opt_lang, str) and opt_lang.strip():
            return opt_lang.strip().lower()
        backend_lang = cfg.backend.params.get("lang")
        if isinstance(backend_lang, str) and backend_lang.strip():
            return backend_lang.strip().lower()
    except Exception as exc:  # pragma: no cover - fallback defensivo
        logger.debug("No se pudo resolver idioma por defecto desde config: %s", exc)
    return os.getenv("PRONUNCIAPA_DEFAULT_LANG", "es")


def resolve_request_lang(lang: Optional[str]) -> str:
    """Normaliza lang de request; si falta, usa config."""
    if isinstance(lang, str) and lang.strip():
        return lang.strip().lower()
    return default_lang_from_config()