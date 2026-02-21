import '../../domain/repositories/pronunciation_repository.dart';
import '../../domain/entities/transcription_result.dart';
import '../../domain/entities/feedback_result.dart';
import '../datasources/pronuncia_remote_datasource.dart';

/// Implementation of PronunciationRepository using remote data source
class PronunciationRepositoryImpl implements PronunciationRepository {
  final PronunciaRemoteDataSource remoteDataSource;

  PronunciationRepositoryImpl({required this.remoteDataSource});

  @override
  Future<TranscriptionResult> transcribe(
    String audioPath, {
    String? lang,
    String? asr,
    String? textref,
    bool persist = false,
  }) async {
    final json = await remoteDataSource.transcribe(
      audioPath,
      lang: lang,
      asr: asr,
      textref: textref,
      persist: persist,
    );
    return TranscriptionResult.fromJson(json);
  }

  @override
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
  }) async {
    final json = await remoteDataSource.compare(
      audioPath,
      referenceText,
      lang: lang,
      asr: asr,
      textref: textref,
      comparator: comparator,
      evaluationLevel: evaluationLevel,
      mode: mode,
      persist: persist,
    );
    return TranscriptionResult.fromJson(json);
  }

  @override
  Future<FeedbackResult> getFeedback(
    String audioPath,
    String referenceText, {
    String lang = 'es',
    String? evaluationLevel,
    String? mode,
    String? feedbackLevel,
    bool persist = false,
  }) async {
    final json = await remoteDataSource.feedback(
      audioPath,
      referenceText,
      lang: lang,
      evaluationLevel: evaluationLevel,
      mode: mode,
      feedbackLevel: feedbackLevel,
      persist: persist,
    );
    return FeedbackResult.fromJson(json);
  }

  @override
  Future<String> getTextReference(
    String text, {
    String lang = 'es',
    String? textref,
  }) async {
    final json = await remoteDataSource.textref(
      text,
      lang: lang,
      textref: textref,
    );
    return json['ipa'] as String? ?? '';
  }

  @override
  Future<bool> checkHealth() async {
    try {
      final json = await remoteDataSource.health();
      return json['status'] == 'healthy';
    } catch (_) {
      return false;
    }
  }
}
