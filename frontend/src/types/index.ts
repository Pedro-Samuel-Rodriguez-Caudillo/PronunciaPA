/**
 * PronunciaPA API types
 * Re-exported from the original type definitions
 */

export interface TranscriptionResponse {
  ipa: string;
  tokens: string[];
  lang: string;
  meta: Record<string, unknown>;
}

export interface TextRefResponse {
  ipa: string;
  tokens: string[];
  lang: string;
  meta: Record<string, unknown>;
}

export interface EditOp {
  op: 'eq' | 'sub' | 'ins' | 'del';
  ref?: string;
  hyp?: string;
}

export interface CompareResponse {
  per: number;
  score?: number;
  mode: 'casual' | 'objective' | 'phonetic';
  evaluation_level: 'phonemic' | 'phonetic';
  ipa?: string;
  tokens?: string[];
  target_ipa?: string;
  ops: EditOp[];
  alignment: Array<[string | null, string | null]>;
  meta: Record<string, unknown>;
}

export interface ErrorReport {
  target_text: string;
  target_ipa: string;
  observed_ipa: string;
  metrics: Record<string, unknown>;
  ops: EditOp[];
  alignment: Array<[string | null, string | null]>;
  mode?: 'casual' | 'objective' | 'phonetic';
  evaluation_level?: 'phonemic' | 'phonetic';
  feedback_level?: 'casual' | 'precise';
  confidence?: string;
  warnings?: string[];
  lang: string;
  meta: Record<string, unknown>;
}

export interface FeedbackDrill {
  type: string;
  text: string;
}

export interface FeedbackPayload {
  summary: string;
  advice_short: string;
  advice_long: string;
  drills: FeedbackDrill[];
  feedback_level?: 'casual' | 'precise';
  tone?: 'friendly' | 'technical';
  confidence?: string;
  warnings?: string[];
}

export interface FeedbackResponse {
  report: ErrorReport;
  compare: CompareResponse;
  feedback: FeedbackPayload;
}

export interface ErrorResponse {
  detail: string;
  type: string;
  code: number;
}

export interface HealthResponse {
  status: string;
  components: Record<string, ComponentHealth>;
}

export interface ComponentHealth {
  status: 'ready' | 'not_ready' | 'error';
  detail?: string;
}

export interface AudioQualityWarning {
  issue: string;
  message: string;
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
  inventory?: Record<string, unknown>;
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

// Session/practice types
export type TranscriptionMode = 'phonemic' | 'phonetic' | 'auto';
export type CompareMode = 'casual' | 'objective' | 'phonetic' | 'auto';
export type FeedbackLevel = 'casual' | 'precise';
export type SupportedLang = 'es' | 'en' | 'fr' | 'de';
