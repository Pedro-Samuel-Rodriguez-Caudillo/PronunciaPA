/**
 * API Contract Types for PronunciaPA
 * Generated based on Backend Pydantic Models.
 */

// ---------------------------------------------------------------------------
// IPA Display — visualización dual técnica/casual con tokens coloreados
// ---------------------------------------------------------------------------

/** Color semántico de un token IPA. */
export type TokenColor = 'green' | 'yellow' | 'red' | 'gray';

/** Modo de visualización seleccionado por el aprendiz. */
export type DisplayMode = 'technical' | 'casual';

/** Nivel de representación fonológica. */
export type RepresentationLevel = 'phonemic' | 'phonetic';

/** Token IPA individual con color semántico y transliteración coloquial. */
export interface IPADisplayToken {
  /** Símbolo IPA canónico (modo técnico). */
  ipa: string;
  /** Transliteración coloquial legible (modo casual). */
  casual: string;
  /** Color semántico: green=correcto, yellow=cercano, red=error, gray=OOV. */
  color: TokenColor;
  /** Operación de edición: eq, sub, ins, del. */
  op: 'eq' | 'sub' | 'ins' | 'del';
  /** Token de referencia (IPA objetivo). Null para inserciones. */
  ref?: string | null;
  /** Token observado (IPA hipótesis). Null para borrados. */
  hyp?: string | null;
  /** Distancia articulatoria [0,1]. Null si no aplica. */
  articulatory_distance?: number | null;
  /** Nivel de representación de este token. */
  level: RepresentationLevel;
}

/** Resultado completo de la visualización dual de IPA. */
export interface IPADisplay {
  /** Modo de display activo. */
  mode: DisplayMode;
  /** Nivel de representación. */
  level: RepresentationLevel;
  /** IPA objetivo completo en modo técnico. */
  ref_technical: string;
  /** IPA objetivo en transliteración coloquial. */
  ref_casual: string;
  /** IPA observado completo en modo técnico. */
  hyp_technical: string;
  /** IPA observado en transliteración coloquial. */
  hyp_casual: string;
  /** Color global del score: green ≥ 80, yellow 50-79, red < 50. */
  score_color: TokenColor;
  /** Leyenda de colores para mostrar al aprendiz. */
  legend: Record<string, string>;
  /** Tokens individuales con color y transliteración. */
  tokens: IPADisplayToken[];
}


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
  /**
   * Visualización dual del IPA con tokens coloreados.
   * Solo presente cuando el cliente envía display_mode=technical|casual.
   */
  display?: IPADisplay | null;
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

export interface LearningModule {
  id: string;
  title: string;
  description?: string;
  content?: string;
}

export interface LearningSoundSummary {
  id: string;
  ipa?: string;
  common_name?: string;
  label?: string;
  name?: string;
  difficulty?: number;
}

export interface LearningOverview {
  language: string;
  name?: string;
  has_learning_content: boolean;
  inventory?: Record<string, any>;
  modules?: LearningModule[];
  progression?: Record<string, string[]>;
  sounds_count?: number;
  sounds: LearningSoundSummary[];
}

export interface AudioExample {
  text: string;
  ipa?: string;
  focus_position?: string;
  audio_url?: string;
}

export interface LessonDrillTargetAudio {
  text: string;
  audio_url: string;
}

export interface LessonDrillPairAudio {
  word1: string;
  word2: string;
  audio1_url: string;
  audio2_url: string;
}

export interface LessonDrill {
  type: string;
  instruction?: string;
  target?: string;
  targets?: string[];
  pairs?: string[][];
  hints?: string[];
  targets_with_audio?: LessonDrillTargetAudio[];
  pairs_with_audio?: LessonDrillPairAudio[];
}

export interface SoundLesson {
  language: string;
  sound_id: string;
  ipa: string;
  name?: string;
  common_name?: string;
  difficulty?: number;
  note?: string;
  articulation?: Record<string, string>;
  visual_guide?: Record<string, string>;
  audio_examples?: AudioExample[];
  common_errors?: Array<{ substitution?: string; example?: string; tip?: string }>;
  tips?: string[];
  minimal_pairs?: string[][];
  drills: LessonDrill[];
  total_drills: number;
  has_learning_content: boolean;
  generated_drills: boolean;
}
