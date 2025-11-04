"""Esquema de configuración (TypedDicts).

TODO (Issue #18)
----------------
- Incluir `preprocessor` como plugin configurable (alinea con `Kernel`).
- Definir versión de esquema y política de cambios compatibles hacia atrás.
- Especificar validaciones de valores por defecto y coerción de tipos.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class PluginCfg(TypedDict, total=False):
    name: str
    params: dict[str, Any]


class OptionsCfg(TypedDict, total=False):
    lang: Optional[str]
    output: str  # json|table


class AppConfig(TypedDict):
    version: int
    preprocessor: PluginCfg
    backend: PluginCfg
    textref: PluginCfg
    comparator: PluginCfg
    options: OptionsCfg
