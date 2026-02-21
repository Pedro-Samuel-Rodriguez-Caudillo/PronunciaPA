import '../entities/transcription_result.dart';
import '../entities/feedback_result.dart';

/// Domain repository contract for pronunciation operations
/// All implementations must satisfy this interface
abstract class PronunciationRepository {
  /// Transcribe audio to IPA with optional backend selection
  Future<TranscriptionResult> transcribe(
    String audioPath, {
    String? lang,
    String? asr,
    String? textref,
    bool persist = false,
  });

  /// Compare audio transcription with reference text
  Future<TranscriptionResult> compare(
    String audioPath,
    String referenceText, {
    String lang = 'es',
    String? asr,
    String? textref,
    String? comparator,
    String? evaluationLevel,
    String? mode,
    bool persist = false,
  });

  /// Get detailed feedback on pronunciation with drills and advice
  Future<FeedbackResult> getFeedback(
    String audioPath,
    String referenceText, {
    String lang = 'es',
    String? evaluationLevel,
    String? mode,
    String? feedbackLevel,
    bool persist = false,
  });

  /// Get text reference (convert text to IPA without audio)
  Future<String> getTextReference(
    String text, {
    String lang = 'es',
    String? textref,
  });

  /// Check API health
  Future<bool> checkHealth();
}
