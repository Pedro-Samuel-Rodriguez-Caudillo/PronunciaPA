"""Esquema de configuración (Pydantic models).

TODO
----
- Definir una versión de esquema y política de compatibilidad hacia atrás.
- Documentar valores por defecto y coerción de tipos.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class PluginCfg(BaseModel):
    """Configura un plugin por nombre y parámetros.

    - name: nombre canónico del plugin (p. ej., "allosaurus").
    - params: diccionario plano de parámetros de inicialización.
    """

    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class OptionsCfg(BaseModel):
    """Opciones generales de ejecución.

    - lang: idioma por defecto.
    - output: formato de salida para CLI ("json" o "table").
    """

    lang: Optional[str] = None
    output: str = "json"  # json|table


class AppConfig(BaseModel):
    """Estructura principal de configuración de la aplicación."""

    version: int
    preprocessor: PluginCfg
    backend: PluginCfg
    textref: PluginCfg
    comparator: PluginCfg
    options: OptionsCfg = Field(default_factory=OptionsCfg)