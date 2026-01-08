from typing import Any, List, Optional
from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    """Respuesta exitosa de transcripción."""
    ipa: str = Field(..., description="Transcripción completa en formato IPA", json_schema_extra={"example": "o l a"})
    tokens: List[str] = Field(..., description="Lista de tokens fonéticos extraídos", json_schema_extra={"example": ["o", "l", "a"]})
    lang: str = Field(..., description="Código de idioma utilizado", json_schema_extra={"example": "es"})
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales del backend")

class EditOp(BaseModel):
    """Operación de edición individual."""
    op: str = Field(..., description="Tipo de operación (eq, sub, ins, del)", json_schema_extra={"example": "sub"})
    ref: Optional[str] = Field(None, description="Token de referencia", json_schema_extra={"example": "o"})
    hyp: Optional[str] = Field(None, description="Token de la hipótesis", json_schema_extra={"example": "u"})

class CompareResponse(BaseModel):
    """Respuesta exitosa de comparación."""
    per: float = Field(..., description="Phone Error Rate (0.0 a 1.0)", json_schema_extra={"example": 0.15})
    ipa: Optional[str] = Field(
        default=None,
        description="Transcripción IPA detectada (hipótesis)",
        json_schema_extra={"example": "o l a"},
    )
    tokens: List[str] = Field(
        default_factory=list,
        description="Tokens IPA detectados (hipótesis)",
        json_schema_extra={"example": ["o", "l", "a"]},
    )
    ops: List[EditOp] = Field(..., description="Lista de operaciones de edición realizadas")
    alignment: List[List[Optional[str]]] = Field(
        ...,
        description="Pares de tokens alineados [ref, hyp]",
        json_schema_extra={"example": [["h", "h"], ["o", "u"]]}
    )
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales de la comparación")

class ErrorResponse(BaseModel):
    """Estructura estandarizada para respuestas de error."""
    detail: str = Field(..., description="Descripción detallada del error", json_schema_extra={"example": "El formato de audio no es compatible."})
    type: str = Field(..., description="Tipo de error (código corto)", json_schema_extra={"example": "validation_error"})
    code: int = Field(default=400, description="Código HTTP asociado (opcional)", json_schema_extra={"example": 400})

class AudioUploadMeta(BaseModel):
    """Metadatos esperados para la subida de audio."""
    lang: str = Field(default="es", description="Idioma del audio")
    sample_rate: Optional[int] = Field(default=None, description="Frecuencia de muestreo esperada (si se conoce)")
