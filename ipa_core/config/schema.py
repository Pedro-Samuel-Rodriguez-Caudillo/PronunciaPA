"""Esquema de configuración (Pydantic models).

Versionado del esquema
----------------------
- version: int - Versión actual del esquema de config (actual: 1)
- Nuevas versiones solo agregan campos (aditivos)
- Campos removidos se marcan deprecated por 2 versiones antes de eliminar

Política de compatibilidad
--------------------------
- Versión N puede leer configs de versión N-1
- Configs con version > actual lanzarán ValidationError
- Campos desconocidos son IGNORADOS (forward-compatible)

Valores por defecto
-------------------
- preprocessor: "basic" (normalización mínima)
- backend: "stub" (ASR de testing)
- textref: "grapheme" (conversión trivial)
- comparator: "levenshtein" (distancia de edición estándar)
- tts: "default" (selector automático)
- llm: "auto" (detecta runtime disponible)

Coerción de tipos
-----------------
- version: int (lanza error si es string)
- params: dict (acepta mapping y se convierte a dict)
- lang: str | None (acepta string o null/None)
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

# Versión actual del esquema
CURRENT_SCHEMA_VERSION = 1
# Versiones soportadas (actual y anteriores para migración)
SUPPORTED_VERSIONS = {1}


class PluginCfg(BaseModel):
    """Configura un plugin por nombre y parámetros.

    - name: nombre canónico del plugin (p. ej., "allosaurus").
    - params: diccionario plano de parámetros de inicialización.
    """

    name: str
    params: dict[str, Any] = Field(default_factory=dict)


class OptionsCfg(BaseModel):
    """Opciones generales de ejecución.

    - lang: idioma por defecto (ej: "es", "en"). None = usar el del language_pack.
    - output: formato de salida para CLI ("json" o "table").
    """

    lang: Optional[str] = None
    output: str = "json"  # json|table


class AppConfig(BaseModel):
    """Estructura principal de configuración de la aplicación.
    
    Versión actual del esquema: 1
    """

    version: int = CURRENT_SCHEMA_VERSION
    strict_mode: bool = False  # Si True, falla en errores; si False, usa fallbacks automáticos
    preprocessor: PluginCfg = Field(default_factory=lambda: PluginCfg(name="basic"))
    backend: PluginCfg = Field(default_factory=lambda: PluginCfg(name="stub"))
    textref: PluginCfg = Field(default_factory=lambda: PluginCfg(name="grapheme"))
    comparator: PluginCfg = Field(default_factory=lambda: PluginCfg(name="levenshtein"))
    tts: PluginCfg = Field(default_factory=lambda: PluginCfg(name="default"))
    llm: PluginCfg = Field(default_factory=lambda: PluginCfg(name="auto"))
    options: OptionsCfg = Field(default_factory=OptionsCfg)
    language_pack: Optional[str] = None
    model_pack: Optional[str] = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: int) -> int:
        """Validar que la versión del config está soportada."""
        if v not in SUPPORTED_VERSIONS:
            if v > CURRENT_SCHEMA_VERSION:
                raise ValueError(
                    f"Config version {v} es más nueva que la soportada ({CURRENT_SCHEMA_VERSION}). "
                    "Actualiza PronunciaPA a una versión más reciente."
                )
            raise ValueError(
                f"Config version {v} ya no está soportada. "
                f"Versiones soportadas: {SUPPORTED_VERSIONS}"
            )
        return v

