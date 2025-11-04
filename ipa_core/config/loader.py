"""Carga/validación de configuración (stub).

TODO (Issue #18)
----------------
- Implementar carga desde YAML con validación contra `AppConfig`.
- Resolver `preprocessor/backend/textref/comparator` por nombre con defaults.
- Agregar soporte para variables de entorno y perfiles (dev/prod/local).
"""
from __future__ import annotations

from ipa_core.config.schema import AppConfig


def load_config(path: str) -> AppConfig:
    """Carga YAML desde `path` y valida contra `AppConfig`.

    Implementación pendiente: solo define el contrato.
    """
    raise NotImplementedError("load_config está sin implementar (contrato únicamente)")
