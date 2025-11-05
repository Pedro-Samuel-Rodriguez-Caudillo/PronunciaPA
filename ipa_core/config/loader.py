"""Carga/validación de configuración (stub).

TODO
----
- Cargar YAML y validar que existan las claves mínimas (versión y plugins).
- Aplicar valores por defecto cuando falten parámetros esperados.
- Permitir un archivo base y uno local para sobreescrituras simples.
"""
from __future__ import annotations

from ipa_core.config.schema import AppConfig


def load_config(path: str) -> AppConfig:
    """Carga YAML desde `path` y valida contra `AppConfig`.

    Implementación pendiente: solo define el contrato.
    """
    raise NotImplementedError("load_config está sin implementar (contrato únicamente)")
