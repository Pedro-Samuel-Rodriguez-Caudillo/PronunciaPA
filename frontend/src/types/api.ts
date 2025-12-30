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
  /** Lista de operaciones de edición realizadas */
  ops: EditOp[];
  /** Pares de tokens alineados [ref, hyp] */
  alignment: Array<[string | null, string | null]>;
  /** Metadatos adicionales de la comparación */
  meta: Record<string, any>;
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
