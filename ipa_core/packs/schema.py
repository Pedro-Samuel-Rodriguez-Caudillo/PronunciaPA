"""Pack schemas for Language and Model packs."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PackResource(BaseModel):
    """Reference to a resource file within a pack."""

    model_config = ConfigDict(extra="allow")

    path: str
    format: Optional[str] = None
    required: bool = True
    sha256: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("path")
    @classmethod
    def _path_not_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("path must be a non-empty string")
        return value

    def resolve_path(self, base_dir: Path) -> Path:
        resource_path = Path(self.path)
        if resource_path.is_absolute():
            return resource_path
        return base_dir / resource_path


class PackSource(BaseModel):
    """Metadata for a data source used in a pack."""

    model_config = ConfigDict(extra="allow")

    name: str
    url: Optional[str] = None
    license: Optional[str] = None
    note: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_not_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("name must be a non-empty string")
        return value


class PackCompatibility(BaseModel):
    """Compatibility hints between packs and the core/adapters."""

    model_config = ConfigDict(extra="allow")

    core_min: Optional[str] = None
    core_max: Optional[str] = None
    adapters: list[str] = Field(default_factory=list)


class ModeProfile(BaseModel):
    """Mode-specific configuration (casual, objective, phonetic)."""

    model_config = ConfigDict(extra="allow")

    id: str
    description: Optional[str] = None
    allow_variants: bool = False
    rules: list[str] = Field(default_factory=list)
    scoring_profile: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _id_not_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("id must be a non-empty string")
        return value


class ErrorWeights(BaseModel):
    """Pesos de error configurables por tipo de error fonético.

    Permiten que el pack ajuste cuánto penaliza el sistema cada tipo
    de error según las prioridades del idioma/dialecto.

    Campos
    ------
    semantic:
        Peso para errores que cambian el significado (mínimo par semántico).
    frequency:
        Peso inverso a la frecuencia léxica — errores en palabras raras
        penalizan menos que en palabras muy comunes.
    articulatory:
        Escalar adicional sobre la distancia articulatoria.  Un valor >1
        amplifica las diferencias fonéticas; <1 las suaviza.
    """

    model_config = ConfigDict(extra="allow")

    semantic: float = Field(
        default=1.0,
        ge=0.0,
        description="Peso para errores con impacto semántico.",
    )
    frequency: float = Field(
        default=1.0,
        ge=0.0,
        description="Escalar de frecuencia léxica (1.0 = sin ajuste).",
    )
    articulatory: float = Field(
        default=1.0,
        ge=0.0,
        description="Escalar sobre la distancia articulatoria.",
    )


class TTSConfig(BaseModel):
    """TTS configuration for local playback."""

    model_config = ConfigDict(extra="allow")

    provider: str
    voice: Optional[str] = None
    sample_rate: Optional[int] = None
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def _provider_not_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("provider must be a non-empty string")
        return value

    @field_validator("sample_rate")
    @classmethod
    def _sample_rate_positive(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("sample_rate must be positive")
        return value


class LanguagePack(BaseModel):
    """Schema for a language pack manifest."""

    model_config = ConfigDict(extra="allow")

    schema_version: int = 1
    id: str
    version: str
    language: str
    dialect: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    sources: list[PackSource] = Field(default_factory=list)
    compat: Optional[PackCompatibility] = None

    inventory: PackResource
    lexicon: PackResource
    rules: list[PackResource] = Field(default_factory=list)
    mappings: dict[str, PackResource] = Field(default_factory=dict)
    scoring_profile: Optional[PackResource] = None
    templates: Optional[PackResource] = None
    tts: Optional[TTSConfig] = None
    modes: list[ModeProfile] = Field(default_factory=list)

    # Léxico inline (palabra → IPA precomputado).  Permite funcionamiento
    # offline sin archivos externos adicionales.  Para packs grandes se
    # recomienda un archivo separado apuntado por ``lexicon`` (PackResource).
    inline_lexicon: Dict[str, str] = Field(
        default_factory=dict,
        description="Léxico precargado {palabra: IPA} para consulta offline sin archivos externos.",
    )

    # Pesos de error configurables por tipo.
    error_weights: ErrorWeights = Field(
        default_factory=ErrorWeights,
        description="Pesos de error por tipo (semántico, frecuencia, articulatorio).",
    )

    @field_validator("schema_version")
    @classmethod
    def _schema_version_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("schema_version must be positive")
        return value

    @field_validator("id", "version", "language")
    @classmethod
    def _field_not_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("field must be a non-empty string")
        return value


class RuntimeSpec(BaseModel):
    """Runtime adapter configuration for a model pack."""

    model_config = ConfigDict(extra="allow")

    kind: str
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kind")
    @classmethod
    def _kind_not_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("kind must be a non-empty string")
        return value


class ModelPack(BaseModel):
    """Schema for a model pack manifest."""

    model_config = ConfigDict(extra="allow")

    schema_version: int = 1
    id: str
    version: str
    family: Optional[str] = None
    size_tier: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    sources: list[PackSource] = Field(default_factory=list)
    compat: Optional[PackCompatibility] = None
    runtime: RuntimeSpec
    files: list[PackResource]
    tokenizer: Optional[PackResource] = None
    prompt: Optional[PackResource] = None
    output_schema: Optional[PackResource] = None
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _schema_version_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("schema_version must be positive")
        return value

    @field_validator("id", "version")
    @classmethod
    def _field_not_empty(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("field must be a non-empty string")
        return value

    @field_validator("files")
    @classmethod
    def _files_not_empty(cls, value: list[PackResource]) -> list[PackResource]:
        if not value:
            raise ValueError("files must include at least one resource")
        return value


__all__ = [
    "ErrorWeights",
    "LanguagePack",
    "ModelPack",
    "ModeProfile",
    "PackCompatibility",
    "PackResource",
    "PackSource",
    "RuntimeSpec",
    "TTSConfig",
]
