/**
 * PronunciaPA API types
 * Re-exported from the canonical type definitions in api.ts
 */

export * from './api';
export type { IPADisplay, IPADisplayToken, DisplayMode, TokenColor, RepresentationLevel } from './api';

// Session/practice types
export type TranscriptionMode = 'phonemic' | 'phonetic' | 'auto';
export type CompareMode = 'casual' | 'objective' | 'phonetic' | 'auto';
export type FeedbackLevel = 'casual' | 'precise';
export type SupportedLang = 'es' | 'en' | 'fr' | 'de';
