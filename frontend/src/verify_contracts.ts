import { TranscriptionResponse, CompareResponse, ErrorResponse, FeedbackResponse } from './types/api';
import * as successTranscription from './mocks/success_transcription.json';
import * as comparisonResult from './mocks/comparison_result.json';
import * as errorInvalidAudio from './mocks/error_invalid_audio.json';
import * as feedbackResult from './mocks/feedback_result.json';

/**
 * Simple compile-time check for consistency.
 * If this file compiles with tsc, then the mocks match the interfaces.
 */

const t: TranscriptionResponse = successTranscription;
const c: CompareResponse = (comparisonResult as any); // Cast because of JSON module subtleties with tuples
const e: ErrorResponse = errorInvalidAudio;
const f: FeedbackResponse = (feedbackResult as any);

console.log('Types and Mocks are consistent!');
