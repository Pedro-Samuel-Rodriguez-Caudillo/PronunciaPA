"""Carga/validación de configuración.

Este módulo carga la configuración desde un archivo YAML y delega la
sobrescritura de variables de entorno a ``pydantic-settings`` (prefijo
``PRONUNCIAPA_``, delimitador ``__`` para nested).

Las únicas responsabilidades que quedan en este loader:
1. Resolver qué archivo YAML cargar (path explícito → env → CWD).
2. Aplicar aliases legacy (``PRONUNCIAPA_ASR`` → ``PRONUNCIAPA_BACKEND__NAME``).
3. Normalizar ``del`` → ``del_`` en params del comparador.
4. Construir ``AppConfig`` (que hereda ``BaseSettings`` y auto-lee env vars).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ipa_core.config.schema import AppConfig

# ── Aliases legacy ───────────────────────────────────────────────────
# Mapean env vars "cortas" (README / CLI) a la forma que
# pydantic-settings entiende (PREFIX + nested delimiter).
_ENV_ALIASES: dict[str, str] = {
    "PRONUNCIAPA_ASR": "PRONUNCIAPA_BACKEND__NAME",
    "PRONUNCIAPA_TEXTREF": "PRONUNCIAPA_TEXTREF__NAME",
    "PRONUNCIAPA_COMPARATOR": "PRONUNCIAPA_COMPARATOR__NAME",
    "PRONUNCIAPA_PREPROCESSOR": "PRONUNCIAPA_PREPROCESSOR__NAME",
    # Single-underscore legacy format (pre pydantic-settings migration)
    "PRONUNCIAPA_BACKEND_NAME": "PRONUNCIAPA_BACKEND__NAME",
}


def _apply_env_aliases() -> dict[str, tuple[str, str]]:
    """Copiar aliases legacy al formato nativo de pydantic-settings.

    Además, *elimina* temporalmente los alias originales del entorno
    para evitar que pydantic-settings intente parsear, p. ej.,
    ``PRONUNCIAPA_TEXTREF=grapheme`` como un ``PluginCfg`` completo.

    Retorna dict  alias → (target_var, valor_original)  para revertir.
    """
    applied: dict[str, tuple[str, str]] = {}
    for alias, target in _ENV_ALIASES.items():
        val = os.environ.get(alias)
        if val is not None:
            if target not in os.environ:
                os.environ[target] = val
            # Eliminar alias para que pydantic-settings no lo interprete
            # como el campo anidado completo (ej. textref → PluginCfg).
            applied[alias] = (target, val)
            del os.environ[alias]
    return applied


def _revert_env_aliases(applied: dict[str, tuple[str, str]]) -> None:
    """Restaurar env vars originales y limpiar targets temporales."""
    for alias, (target, original_val) in applied.items():
        os.environ.pop(target, None)
        os.environ[alias] = original_val


def _normalize_compare_weights(data: dict[str, Any]) -> None:
    """Mapea ``del`` → ``del_`` en params del comparador (YAML keyword)."""
    comparator = data.get("comparator")
    if not isinstance(comparator, dict):
        return
    params = comparator.get("params")
    if not isinstance(params, dict):
        return
    if "del" in params and "del_" not in params:
        params["del_"] = params.pop("del")


def format_validation_error(exc: ValidationError) -> str:
    """Transforma un ``ValidationError`` de Pydantic en un mensaje amigable.

    Parámetros
    ----------
    exc : ValidationError
        La excepción capturada.

    Retorna
    -------
    str
        Resumen formateado de los errores.
    """
    lines = ["Error en la configuración:"]
    for error in exc.errors():
        loc = " -> ".join(str(p) for p in error["loc"])
        msg = error["msg"]
        lines.append(f"  - [{loc}]: {msg}")
    return "\n".join(lines)


def load_config(path: str | None = None) -> AppConfig:
    """Carga YAML y construye ``AppConfig``.

    Prioridad de valores (mayor gana):
    1. Variables de entorno ``PRONUNCIAPA_*`` (auto-leídas por pydantic-settings).
    2. Datos del archivo YAML.
    3. Defaults de ``AppConfig``.

    Resolución del archivo YAML:
    1. ``path`` (argumento explícito).
    2. Variable de entorno ``PRONUNCIAPA_CONFIG``.
    3. ``./config.yaml``.
    4. ``./configs/local.yaml``.
    5. Sin archivo → solo defaults + env vars.

    Parámetros
    ----------
    path : str, opcional
        Ruta al archivo YAML.

    Retorna
    -------
    AppConfig
        Configuración validada.
    """
    # ── 1. Resolver archivo YAML ─────────────────────────────────
    p: Path | None = None
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Archivo de configuración no encontrado: {path}"
            )
    else:
        env_path = os.environ.get("PRONUNCIAPA_CONFIG")
        if env_path:
            p = Path(env_path)
            if not p.exists():
                raise FileNotFoundError(
                    f"Archivo PRONUNCIAPA_CONFIG no encontrado: {env_path}"
                )
        else:
            for candidate in ["config.yaml", "configs/local.yaml"]:
                cp = Path(candidate)
                if cp.exists():
                    p = cp
                    break

    # ── 2. Leer YAML ─────────────────────────────────────────────
    data: dict[str, Any] = {}
    if p:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    _normalize_compare_weights(data)

    # ── 3. Aliases legacy → pydantic-settings format ─────────────
    applied = _apply_env_aliases()

    try:
        # pydantic-settings auto-lee PRONUNCIAPA_* env vars y las
        # fusiona con los ``data`` del YAML (env tiene prioridad).
        cfg = AppConfig(**data)
    finally:
        _revert_env_aliases(applied)

    return cfg
