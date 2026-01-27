/**
 * API Contract Types for PronunciaPA
 * Generated based on Backend Pydantic Models.
 */

export interface TranscriptionResponse {
  /** Transcripción completa en formato IPA */
  ipa: string;
  /** Lista de tokens fonéticos extraídos */
  tokens: string[];
  /** Código de idioma utilizado */
  lang: string;
  /** Metadatos adicionales del backend */
  meta: Record<string, any>;
}

export interface TextRefResponse {
  /** Transcripción en formato IPA */
  ipa: string;
  /** Lista de tokens IPA generados */
  tokens: string[];
  /** Código de idioma utilizado */
  lang: string;
  /** Metadatos adicionales del proveedor */
  meta: Record<string, any>;
}

export interface EditOp {
  /** Tipo de operación (eq, sub, ins, del) */
  op: 'eq' | 'sub' | 'ins' | 'del';
  /** Token de referencia */
  ref?: string;
  /** Token de la hipótesis */
  hyp?: string;
}

export interface CompareResponse {
  /** Phone Error Rate (0.0 a 1.0) */
  per: number;
  /** Puntuación de pronunciación (0-100) */
  score?: number;
  /** Modo de evaluación */
  mode: 'casual' | 'objective' | 'phonetic';
  /** Nivel de evaluación */
  evaluation_level: 'phonemic' | 'phonetic';
  /** Transcripción IPA detectada */
  ipa?: string;
  /** Tokens IPA detectados */
  tokens?: string[];
  /** Lista de operaciones de edición realizadas */
  ops: EditOp[];
  /** Pares de tokens alineados [ref, hyp] */
  alignment: Array<[string | null, string | null]>;
  /** Metadatos adicionales de la comparación */
  meta: Record<string, any>;
}

export interface ErrorReport {
  /** Texto objetivo */
  target_text: string;
  /** IPA objetivo */
  target_ipa: string;
  /** IPA observado */
  observed_ipa: string;
  /** Metricas de comparacion */
  metrics: Record<string, any>;
  /** Operaciones de edicion */
  ops: EditOp[];
  /** Pares de tokens alineados [ref, hyp] */
  alignment: Array<[string | null, string | null]>;
  /** Modo de evaluacion */
  mode?: 'casual' | 'objective' | 'phonetic';
  /** Nivel de evaluacion */
  evaluation_level?: 'phonemic' | 'phonetic';
  /** Nivel de feedback */
  feedback_level?: 'casual' | 'precise';
  /** Confianza de la comparacion */
  confidence?: string;
  /** Advertencias sobre confiabilidad */
  warnings?: string[];
  /** Codigo de idioma */
  lang: string;
  /** Metadatos adicionales */
  meta: Record<string, any>;
}

export interface FeedbackDrill {
  /** Tipo de ejercicio */
  type: string;
  /** Texto del ejercicio */
  text: string;
}

export interface FeedbackPayload {
  /** Resumen corto */
  summary: string;
  /** Consejo breve */
  advice_short: string;
  /** Consejo detallado */
  advice_long: string;
  /** Ejercicios recomendados */
  drills: FeedbackDrill[];
  /** Nivel de feedback */
  feedback_level?: 'casual' | 'precise';
  /** Tono de explicacion */
  tone?: 'friendly' | 'technical';
  /** Confianza del resultado */
  confidence?: string;
  /** Advertencias */
  warnings?: string[];
}

export interface FeedbackResponse {
  /** Reporte canonico de errores */
  report: ErrorReport;
  /** Resultado de comparacion */
  compare: CompareResponse;
  /** Salida del modelo LLM */
  feedback: FeedbackPayload;
}

export interface ErrorResponse {
  /** Descripción detallada del error */
  detail: string;
  /** Tipo de error (código corto) */
  type: string;
  /** Código HTTP asociado */
  code: number;
}

export interface AudioUploadMeta {
  /** Idioma del audio */
  lang: string;
  /** Frecuencia de muestreo esperada */
  sample_rate?: number;
}
