from typing import Any, List, Optional
from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    """Respuesta exitosa de transcripción."""
    ipa: str = Field(..., description="Transcripción completa en formato IPA", json_schema_extra={"example": "o l a"})
    tokens: List[str] = Field(..., description="Lista de tokens fonéticos extraídos", json_schema_extra={"example": ["o", "l", "a"]})
    lang: str = Field(..., description="Código de idioma utilizado", json_schema_extra={"example": "es"})
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales del backend")

class TextRefResponse(BaseModel):
    """Respuesta de conversion texto a IPA."""
    ipa: str = Field(..., description="Transcripción en formato IPA", json_schema_extra={"example": "o l a"})
    tokens: List[str] = Field(..., description="Lista de tokens IPA generados", json_schema_extra={"example": ["o", "l", "a"]})
    lang: str = Field(..., description="Código de idioma utilizado", json_schema_extra={"example": "es"})
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales del proveedor")

class EditOp(BaseModel):
    """Operación de edición individual."""
    op: str = Field(..., description="Tipo de operación (eq, sub, ins, del)", json_schema_extra={"example": "sub"})
    ref: Optional[str] = Field(None, description="Token de referencia", json_schema_extra={"example": "o"})
    hyp: Optional[str] = Field(None, description="Token de la hipótesis", json_schema_extra={"example": "u"})

class CompareResponse(BaseModel):
    """Respuesta exitosa de comparación."""
    per: float = Field(..., description="Phone Error Rate (0.0 a 1.0)", json_schema_extra={"example": 0.15})
    score: Optional[float] = Field(
        default=None,
        description="Puntuación de pronunciación (0-100)",
        json_schema_extra={"example": 85.0},
    )
    mode: str = Field(
        default="objective",
        description="Modo de evaluación: casual, objective, phonetic",
        json_schema_extra={"example": "objective"},
    )
    evaluation_level: str = Field(
        default="phonemic",
        description="Nivel de evaluación: phonemic, phonetic",
        json_schema_extra={"example": "phonemic"},
    )
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

class ErrorReport(BaseModel):
    """Reporte canonico de errores usado como input para el LLM."""
    target_text: str = Field(..., description="Texto objetivo")
    target_ipa: str = Field(..., description="IPA objetivo")
    observed_ipa: str = Field(..., description="IPA observado")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Metricas de comparacion")
    ops: List[EditOp] = Field(default_factory=list, description="Operaciones de edicion")
    alignment: List[List[Optional[str]]] = Field(
        default_factory=list,
        description="Pares de tokens alineados [ref, hyp]",
    )
    mode: Optional[str] = Field(
        default=None,
        description="Modo de evaluacion: casual, objective, phonetic",
        json_schema_extra={"example": "objective"},
    )
    evaluation_level: Optional[str] = Field(
        default=None,
        description="Nivel de evaluacion: phonemic, phonetic",
        json_schema_extra={"example": "phonemic"},
    )
    feedback_level: Optional[str] = Field(
        default=None,
        description="Nivel de feedback: casual o precise",
        json_schema_extra={"example": "casual"},
    )
    confidence: Optional[str] = Field(
        default=None,
        description="Confianza de la comparacion",
        json_schema_extra={"example": "low"},
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Advertencias sobre confiabilidad o datos incompletos",
    )
    lang: str = Field(..., description="Codigo de idioma")
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")

class FeedbackResponse(BaseModel):
    """Respuesta con analisis y feedback generado."""
    report: ErrorReport = Field(..., description="Reporte canonico de errores")
    compare: CompareResponse = Field(..., description="Resultado de comparacion")
    feedback: dict[str, Any] = Field(..., description="Salida del modelo LLM")

class ErrorResponse(BaseModel):
    """Estructura estandarizada para respuestas de error."""
    detail: str = Field(..., description="Descripción detallada del error", json_schema_extra={"example": "El formato de audio no es compatible."})
    type: str = Field(..., description="Tipo de error (código corto)", json_schema_extra={"example": "validation_error"})
    code: int = Field(default=400, description="Código HTTP asociado (opcional)", json_schema_extra={"example": 400})

class AudioUploadMeta(BaseModel):
    """Metadatos esperados para la subida de audio."""
    lang: str = Field(default="es", description="Idioma del audio")
    sample_rate: Optional[int] = Field(default=None, description="Frecuencia de muestreo esperada (si se conoce)")
