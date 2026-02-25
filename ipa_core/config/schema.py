"""Esquema de configuración (pydantic-settings + Pydantic v2).

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
- textref: "auto" (cascada: espeak → epitran → grapheme)
- comparator: "levenshtein" (distancia de edición estándar)
- tts: "default" (selector automático)
- llm: "rule_based" (genera consejos sin modelos externos; usa "ollama" o
                    "llama_cpp" cuando tengas un model_pack configurado)

Variables de entorno
--------------------
Todas las claves se pueden sobrescribir con variables de entorno usando el
prefijo ``PRONUNCIAPA_`` y el delimitador ``__`` para anidamiento::

    PRONUNCIAPA_STRICT_MODE=true
    PRONUNCIAPA_BACKEND__NAME=allosaurus
    PRONUNCIAPA_BACKEND__PARAMS={"emit_timestamps": true}
    PRONUNCIAPA_OPTIONS__LANG=es

Aliases de conveniencia (se normalizan en ``load_config``)::

    PRONUNCIAPA_ASR=allosaurus       →  backend.name
    PRONUNCIAPA_TEXTREF=espeak       →  textref.name
    PRONUNCIAPA_COMPARATOR=articulatory → comparator.name
    PRONUNCIAPA_PREPROCESSOR=basic   →  preprocessor.name
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings import PydanticBaseSettingsSource

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


class AppConfig(BaseSettings):
    """Estructura principal de configuración de la aplicación.

    Hereda de ``BaseSettings`` (pydantic-settings) para leer variables
    de entorno con prefijo ``PRONUNCIAPA_`` automáticamente.

    Versión actual del esquema: 1
    """

    model_config = SettingsConfigDict(
        env_prefix="PRONUNCIAPA_",
        env_nested_delimiter="__",
        # No leer .env automáticamente — YAML maneja eso.
        env_file=None,
        # Campos extra son ignorados (forward-compatible).
        extra="ignore",
    )

    version: int = CURRENT_SCHEMA_VERSION
    strict_mode: bool = False  # Si True, falla en errores; si False, usa fallbacks automáticos
    preprocessor: PluginCfg = Field(default_factory=lambda: PluginCfg(name="basic"))
    backend: PluginCfg = Field(default_factory=lambda: PluginCfg(name="stub"))
    textref: PluginCfg = Field(default_factory=lambda: PluginCfg(name="auto"))
    comparator: PluginCfg = Field(default_factory=lambda: PluginCfg(name="levenshtein"))
    tts: PluginCfg = Field(default_factory=lambda: PluginCfg(name="default"))
    llm: PluginCfg = Field(default_factory=lambda: PluginCfg(name="rule_based"))
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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Prioridad: env vars > init kwargs (YAML) > defaults.

        Por defecto pydantic-settings pone ``init_settings`` primero,
        pero nosotros queremos que las variables de entorno ganen sobre
        los valores del archivo YAML (que se pasan como kwargs).
        """
        return (env_settings, init_settings, dotenv_settings, file_secret_settings)

