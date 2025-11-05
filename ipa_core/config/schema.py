"""Esquema de configuración (TypedDicts).

TODO
----
- Incluir `preprocessor` como plugin configurable (alineado con el `Kernel`).
- Definir una versión de esquema y política de compatibilidad hacia atrás.
- Documentar valores por defecto y coerción de tipos (por ejemplo, números/strings).
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class PluginCfg(TypedDict, total=False):
    """Configura un plugin por nombre y parámetros.

    - name: nombre canónico del plugin (p. ej., "whisper_ipa").
    - params: diccionario plano de parámetros de inicialización.
    """

    name: str
    params: dict[str, Any]


class OptionsCfg(TypedDict, total=False):
    """Opciones generales de ejecución.

    - lang: idioma por defecto.
    - output: formato de salida para CLI ("json" o "table").
    """

    lang: Optional[str]
    output: str  # json|table


class AppConfig(TypedDict):
    """Estructura principal de configuración de la aplicación."""

    version: int
    preprocessor: PluginCfg
    backend: PluginCfg
    textref: PluginCfg
    comparator: PluginCfg
    options: OptionsCfg
