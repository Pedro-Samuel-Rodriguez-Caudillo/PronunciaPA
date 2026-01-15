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

    version: int = 1
    preprocessor: PluginCfg = Field(default_factory=lambda: PluginCfg(name="basic"))
    backend: PluginCfg = Field(default_factory=lambda: PluginCfg(name="allosaurus"))
    textref: PluginCfg = Field(default_factory=lambda: PluginCfg(name="grapheme"))
    comparator: PluginCfg = Field(default_factory=lambda: PluginCfg(name="levenshtein"))
    tts: PluginCfg = Field(default_factory=lambda: PluginCfg(name="default"))
    llm: PluginCfg = Field(default_factory=lambda: PluginCfg(name="auto"))
    options: OptionsCfg = Field(default_factory=OptionsCfg)
    language_pack: Optional[str] = None
    model_pack: Optional[str] = None
