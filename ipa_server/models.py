from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    """Respuesta exitosa de transcripción."""
    ipa: str = Field(..., description="Transcripción completa en formato IPA", json_schema_extra={"example": "o l a"})
    tokens: List[str] = Field(..., description="Lista de tokens fonéticos extraídos", json_schema_extra={"example": ["o", "l", "a"]})
    lang: str = Field(..., description="Código de idioma utilizado", json_schema_extra={"example": "es"})
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales del backend")

class TextRefResponse(BaseModel):
    """Respuesta de conversion texto a IPA."""
    ipa: str = Field(..., description="Transcripción en formato IPA", json_schema_extra={"example": "o l a"})
    tokens: List[str] = Field(..., description="Lista de tokens IPA generados", json_schema_extra={"example": ["o", "l", "a"]})
    lang: str = Field(..., description="Código de idioma utilizado", json_schema_extra={"example": "es"})
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales del proveedor")

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
    alignment: List[Tuple[Optional[str], Optional[str]]] = Field(
        ...,
        description="Pares de tokens alineados [ref, hyp]",
        json_schema_extra={"example": [["h", "h"], ["o", "u"]]}
    )
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales de la comparación")

class ErrorReport(BaseModel):
    """Reporte canonico de errores usado como input para el LLM."""
    target_text: str = Field(..., description="Texto objetivo")
    target_ipa: str = Field(..., description="IPA objetivo")
    observed_ipa: str = Field(..., description="IPA observado")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Metricas de comparacion")
    ops: List[EditOp] = Field(default_factory=list, description="Operaciones de edicion")
    alignment: List[Tuple[Optional[str], Optional[str]]] = Field(
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
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")

class FeedbackResponse(BaseModel):
    """Respuesta con analisis y feedback generado."""
    report: ErrorReport = Field(..., description="Reporte canonico de errores")
    compare: CompareResponse = Field(..., description="Resultado de comparacion")
    feedback: Dict[str, Any] = Field(..., description="Salida del modelo LLM")

class ErrorResponse(BaseModel):
    """Estructura estandarizada para respuestas de error."""
    detail: str = Field(..., description="Descripción detallada del error", json_schema_extra={"example": "El formato de audio no es compatible."})
    type: str = Field(..., description="Tipo de error (código corto)", json_schema_extra={"example": "validation_error"})
    code: int = Field(default=400, description="Código HTTP asociado (opcional)", json_schema_extra={"example": 400})

class AudioUploadMeta(BaseModel):
    """Metadatos esperados para la subida de audio."""
    lang: str = Field(default="es", description="Idioma del audio")
    sample_rate: Optional[int] = Field(default=None, description="Frecuencia de muestreo esperada (si se conoce)")

class SoundArticulation(BaseModel):
    """Rasgos articulatorios de un sonido IPA."""
    place: Optional[str] = None
    manner: Optional[str] = None
    voicing: Optional[str] = None
    height: Optional[str] = None
    backness: Optional[str] = None
    rounding: Optional[str] = None
    description: Optional[str] = None

class VisualGuide(BaseModel):
    """Guía visual para producir un sonido."""
    tongue: Optional[str] = None
    teeth: Optional[str] = None
    lips: Optional[str] = None
    airflow: Optional[str] = None
    jaw: Optional[str] = None

class CommonError(BaseModel):
    """Error común al pronunciar un sonido."""
    substitution: Optional[str] = None
    example: Optional[str] = None
    tip: Optional[str] = None

class AudioExample(BaseModel):
    """Ejemplo de audio para un sonido."""
    text: str
    ipa: Optional[str] = None
    focus_position: Optional[str] = None
    audio_url: Optional[str] = None

class DrillTargetAudio(BaseModel):
    """Target de drill con audio."""
    text: str
    audio_url: str

class DrillPairAudio(BaseModel):
    """Par mínimo con audio."""
    word1: str
    word2: str
    audio1_url: str
    audio2_url: str

class LessonDrill(BaseModel):
    """Drill de lección con targets y/o pares."""
    type: str
    instruction: Optional[str] = None
    target: Optional[str] = None
    targets: Optional[List[str]] = None
    pairs: Optional[List[List[str]]] = None
    hints: Optional[List[str]] = None
    targets_with_audio: Optional[List[DrillTargetAudio]] = None
    pairs_with_audio: Optional[List[DrillPairAudio]] = None

class LearningModule(BaseModel):
    """Módulo de aprendizaje."""
    id: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None

class SoundSummary(BaseModel):
    """Resumen de sonido en overview."""
    id: str
    ipa: Optional[str] = None
    common_name: Optional[str] = None
    label: Optional[str] = None
    name: Optional[str] = None
    difficulty: Optional[int] = None

class LearningOverview(BaseModel):
    """Overview de aprendizaje IPA por idioma."""
    language: str
    name: Optional[str] = None
    has_learning_content: bool = False
    inventory: Optional[Dict[str, Any]] = None
    modules: Optional[List[LearningModule]] = None
    progression: Optional[Dict[str, List[str]]] = None
    sounds_count: Optional[int] = None
    sounds: List[SoundSummary] = Field(default_factory=list)

class SoundLesson(BaseModel):
    """Lección completa para un sonido IPA."""
    language: str
    sound_id: str
    ipa: str
    name: Optional[str] = None
    common_name: Optional[str] = None
    difficulty: Optional[int] = None
    note: Optional[str] = None
    articulation: Optional[SoundArticulation] = None
    visual_guide: Optional[VisualGuide] = None
    audio_examples: Optional[List[AudioExample]] = None
    common_errors: Optional[List[CommonError]] = None
    tips: Optional[List[str]] = None
    minimal_pairs: Optional[List[List[str]]] = None
    drills: List[LessonDrill] = Field(default_factory=list)
    total_drills: int = 0
    has_learning_content: bool = False
    generated_drills: bool = False
