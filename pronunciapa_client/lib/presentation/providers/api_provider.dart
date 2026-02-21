import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/debug/app_logger.dart';
import '../../core/debug/debug_http_client.dart';
import '../../core/debug/debug_log_store.dart';

class EditOp {
  final String op;
  final String? ref;
  final String? hyp;

  EditOp({required this.op, this.ref, this.hyp});

  factory EditOp.fromJson(Map<String, dynamic> json) {
    return EditOp(
      op: json['op'] as String,
      ref: json['ref'] as String?,
      hyp: json['hyp'] as String?,
    );
  }
}

class TranscriptionResult {
  final String ipa;
  final double? score; // 0-100 scale (higher is better)
  final double? per; // Phone Error Rate 0.0-1.0 (lower is better)
  final List<List<String?>>? alignment;
  final List<EditOp>? ops; // Edit operations from backend
  final List<String>? tokens; // Observed IPA tokens
  final String? mode; // casual, objective, phonetic
  final String? evaluationLevel; // phonemic, phonetic
  final String? targetIpa; // Reference IPA
  final Map<String, dynamic>? meta;

  TranscriptionResult({
    required this.ipa,
    this.score,
    this.per,
    this.alignment,
    this.ops,
    this.tokens,
    this.mode,
    this.evaluationLevel,
    this.targetIpa,
    this.meta,
  });
}

class FeedbackDrill {
  final String type;
  final String text;

  FeedbackDrill({required this.type, required this.text});

  factory FeedbackDrill.fromJson(Map<String, dynamic> json) {
    return FeedbackDrill(
      type: json['type'] as String,
      text: json['text'] as String,
    );
  }
}

class FeedbackPayload {
  final String summary;
  final String adviceShort;
  final String adviceLong;
  final List<FeedbackDrill> drills;
  final String? feedbackLevel;
  final String? tone;
  final String? confidence;
  final List<String>? warnings;

  FeedbackPayload({
    required this.summary,
    required this.adviceShort,
    required this.adviceLong,
    required this.drills,
    this.feedbackLevel,
    this.tone,
    this.confidence,
    this.warnings,
  });

  factory FeedbackPayload.fromJson(Map<String, dynamic> json) {
    return FeedbackPayload(
      summary: json['summary'] as String,
      adviceShort: json['advice_short'] as String,
      adviceLong: json['advice_long'] as String,
      drills: (json['drills'] as List<dynamic>)
          .map((d) => FeedbackDrill.fromJson(d as Map<String, dynamic>))
          .toList(),
      feedbackLevel: json['feedback_level'] as String?,
      tone: json['tone'] as String?,
      confidence: json['confidence'] as String?,
      warnings: (json['warnings'] as List<dynamic>?)?.cast<String>(),
    );
  }
}

class FeedbackResult {
  final TranscriptionResult compare;
  final FeedbackPayload feedback;
  final Map<String, dynamic> report;

  FeedbackResult({
    required this.compare,
    required this.feedback,
    required this.report,
  });
}

class PronunciaApiService {
  static const Duration _requestTimeout = Duration(seconds: 60);
  static const Duration _fileRetryDelay = Duration(milliseconds: 120);
  static const int _fileRetryAttempts = 3;
  static const int _minWavBytes = 46;

  final String baseUrl;
  final http.Client _client;

  PronunciaApiService({String? baseUrl, http.Client? client})
      : baseUrl = baseUrl ?? _determineBaseUrl(),
        _client = client ?? (kDebugMode ? DebugHttpClient() : http.Client());

  static String _determineBaseUrl() {
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://127.0.0.1:8000';
  }

  static const _tag = 'ApiService';

  void _log(String message) {
    AppLogger.d(_tag, message);
  }

  Map<String, dynamic>? _parseMeta(dynamic value) {
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return null;
  }

  String _formatError(int status, String body) {
    String detail = body.trim();
    String? errorType;
    String? backendName;
    if (detail.isEmpty) {
      detail = 'Empty response body';
    }
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map) {
        if (decoded['type'] != null) {
          errorType = decoded['type'].toString();
        }
        if (decoded['backend'] != null) {
          backendName = decoded['backend'].toString();
        }
        if (decoded['detail'] != null) {
          detail = decoded['detail'].toString();
        } else if (decoded['message'] != null) {
          detail = decoded['message'].toString();
        } else if (decoded['error'] != null) {
           detail = decoded['error'].toString();
        }
      }
    } catch (_) {
      // Si no es JSON, mostrar los primeros 200 caracteres del cuerpo
      if (detail.length > 200) {
        detail = '${detail.substring(0, 200)}...';
      }
    }
    if (errorType == 'asr_unavailable') {
      final backend = (backendName == null || backendName.isEmpty)
          ? 'stub'
          : backendName;
      return 'ASR IPA no disponible (backend: $backend). '
          'Configura un modelo ASR real en el servidor y desactiva PRONUNCIAPA_ASR=stub.';
    }
    return 'Error $status: $detail';
  }

  Future<File> _ensureAudioFile(String filePath) async {
    final file = File(filePath);
    for (var attempt = 0; attempt < _fileRetryAttempts; attempt++) {
      if (await file.exists()) {
        final length = await file.length();
        if (length >= _minWavBytes) {
          return file;
        }
      }
      await Future.delayed(_fileRetryDelay);
    }
    throw Exception(
      'Audio file missing or empty (recording too short): ${file.absolute.path}',
    );
  }

  Future<TranscriptionResult> transcribe(String filePath, {String lang = 'es'}) async {
    final file = await _ensureAudioFile(filePath);
    _log('Checking file at: ${file.absolute.path}');

    final uri = Uri.parse('$baseUrl/v1/transcribe');
    _log('Calling API: $uri');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      await http.MultipartFile.fromPath('audio', file.path),
    );
    if (lang.isNotEmpty) {
      request.fields['lang'] = lang;
    }

    final response = await _client.send(request).timeout(_requestTimeout);
    final body = await response.stream.bytesToString();
    _log('Response status: ${response.statusCode}');
    if (response.statusCode == 200) {
      final data = jsonDecode(body);
      return TranscriptionResult(
        ipa: data['ipa'] ?? '',
        score: (data['score'] as num?)?.toDouble(),
        per: (data['per'] as num?)?.toDouble(),
        alignment: _parseAlignment(data['alignment']),
        ops: _parseOps(data['ops']),
        tokens: (data['tokens'] as List?)?.cast<String>(),
        mode: data['mode'] as String?,
        evaluationLevel: data['evaluation_level'] as String?,
        targetIpa: data['target_ipa'] as String?,
        meta: _parseMeta(data['meta']),
      );
    } else {
      throw Exception(_formatError(response.statusCode, body));
    }
  }

  Future<TranscriptionResult> compare(
    String filePath,
    String referenceText, {
    String lang = 'es',
    String? evaluationLevel,
    String? mode,
  }) async {
    final file = await _ensureAudioFile(filePath);
    _log('Checking file at: ${file.absolute.path}');

    final uri = Uri.parse('$baseUrl/v1/compare');
    _log('Calling API: $uri');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      await http.MultipartFile.fromPath('audio', file.path),
    );
    request.fields['text'] = referenceText;
    if (lang.isNotEmpty) {
      request.fields['lang'] = lang;
    }
    if (evaluationLevel != null && evaluationLevel.isNotEmpty) {
      request.fields['evaluation_level'] = evaluationLevel;
    }
    if (mode != null && mode.isNotEmpty) {
      request.fields['mode'] = mode;
    }

    final response = await _client.send(request).timeout(_requestTimeout);
    final body = await response.stream.bytesToString();
    _log('Response status: ${response.statusCode}');
    if (response.statusCode == 200) {
      final data = jsonDecode(body);
      return TranscriptionResult(
        ipa: data['ipa'] ?? '',
        score: (data['score'] as num?)?.toDouble(),
        per: (data['per'] as num?)?.toDouble(),
        alignment: _parseAlignment(data['alignment']),
        ops: _parseOps(data['ops']),
        tokens: (data['tokens'] as List?)?.cast<String>(),
        mode: data['mode'] as String?,
        evaluationLevel: data['evaluation_level'] as String?,
        targetIpa: data['target_ipa'] as String?,
        meta: _parseMeta(data['meta']),
      );
    } else {
      throw Exception(_formatError(response.statusCode, body));
    }
  }

  /// Revisión rápida: usa /v1/quick-compare (sin quality-gates, kernel cacheado).
  Future<TranscriptionResult> quickCompare(
    String filePath,
    String referenceText, {
    String lang = 'es',
    String? evaluationLevel,
    String? mode,
  }) async {
    final file = await _ensureAudioFile(filePath);
    _log('Quick compare: ${file.absolute.path}');

    final uri = Uri.parse('$baseUrl/v1/quick-compare');
    _log('Calling API: $uri');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      await http.MultipartFile.fromPath('audio', file.path),
    );
    request.fields['text'] = referenceText;
    if (lang.isNotEmpty) {
      request.fields['lang'] = lang;
    }
    if (evaluationLevel != null && evaluationLevel.isNotEmpty) {
      request.fields['evaluation_level'] = evaluationLevel;
    }
    if (mode != null && mode.isNotEmpty) {
      request.fields['mode'] = mode;
    }

    final response = await _client.send(request).timeout(const Duration(seconds: 30));
    final body = await response.stream.bytesToString();
    _log('Quick compare response: ${response.statusCode}');
    if (response.statusCode == 200) {
      final data = jsonDecode(body);
      return TranscriptionResult(
        ipa: data['ipa'] ?? '',
        score: (data['score'] as num?)?.toDouble(),
        per: (data['per'] as num?)?.toDouble(),
        alignment: _parseAlignment(data['alignment']),
        ops: _parseOps(data['ops']),
        tokens: (data['tokens'] as List?)?.cast<String>(),
        mode: data['mode'] as String?,
        evaluationLevel: data['evaluation_level'] as String?,
        targetIpa: data['target_ipa'] as String?,
        meta: _parseMeta(data['meta']),
      );
    } else {
      throw Exception(_formatError(response.statusCode, body));
    }
  }

  List<List<String?>>? _parseAlignment(dynamic value) {
    if (value == null) return null;
    if (value is List) {
      return value.map((pair) {
        if (pair is List && pair.length == 2) {
          return [pair[0] as String?, pair[1] as String?];
        }
        return <String?>[null, null];
      }).toList();
    }
    return null;
  }

  List<EditOp>? _parseOps(dynamic value) {
    if (value == null) return null;
    if (value is! List) return null;
    try {
      return value
          .map((op) => EditOp.fromJson(op as Map<String, dynamic>))
          .toList();
    } catch (e) {
      _log('Error parsing ops: $e');
      return null;
    }
  }

  Future<FeedbackResult> feedback(
    String filePath,
    String referenceText, {
    String lang = 'es',
    String? evaluationLevel,
    String? mode,
    String? feedbackLevel,
    bool persist = false,
  }) async {
    final file = await _ensureAudioFile(filePath);
    _log('Checking file at: ${file.absolute.path}');

    final uri = Uri.parse('$baseUrl/v1/feedback');
    _log('Calling API: $uri');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      await http.MultipartFile.fromPath('audio', file.path),
    );
    request.fields['text'] = referenceText;
    if (lang.isNotEmpty) {
      request.fields['lang'] = lang;
    }
    if (evaluationLevel != null && evaluationLevel.isNotEmpty) {
      request.fields['evaluation_level'] = evaluationLevel;
    }
    if (mode != null && mode.isNotEmpty) {
      request.fields['mode'] = mode;
    }
    if (feedbackLevel != null && feedbackLevel.isNotEmpty) {
      request.fields['feedback_level'] = feedbackLevel;
    }
    if (persist) {
      request.fields['persist'] = 'true';
    }

    final response = await _client.send(request).timeout(_requestTimeout);
    final body = await response.stream.bytesToString();
    _log('Response status: ${response.statusCode}');
    if (response.statusCode == 200) {
      final data = jsonDecode(body);
      final compareData = data['compare'] as Map<String, dynamic>;
      final feedbackData = data['feedback'] as Map<String, dynamic>;
      
      return FeedbackResult(
        compare: TranscriptionResult(
          ipa: compareData['ipa'] ?? '',
          score: (compareData['score'] as num?)?.toDouble(),
          alignment: _parseAlignment(compareData['alignment']),
          meta: _parseMeta(compareData['meta']),
        ),
        feedback: FeedbackPayload.fromJson(feedbackData),
        report: data['report'] as Map<String, dynamic>,
      );
    } else {
      throw Exception(_formatError(response.statusCode, body));
    }
  }
}

final apiServiceProvider = Provider((ref) => PronunciaApiService());

class ApiState {
  final bool isLoading;
  final String? error;
  final TranscriptionResult? result;
  final FeedbackResult? feedbackResult;
  final String? lastAudioPath;
  final String? lastReferenceText;
  final bool isQuickResult;

  ApiState({
    this.isLoading = false,
    this.error,
    this.result,
    this.feedbackResult,
    this.lastAudioPath,
    this.lastReferenceText,
    this.isQuickResult = false,
  });

  ApiState copyWith({
    bool? isLoading,
    String? error,
    TranscriptionResult? result,
    bool clearResult = false,
    FeedbackResult? feedbackResult,
    bool clearFeedback = false,
    String? lastAudioPath,
    String? lastReferenceText,
    bool? isQuickResult,
  }) {
    return ApiState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      result: clearResult ? null : (result ?? this.result),
      feedbackResult: clearFeedback ? null : (feedbackResult ?? this.feedbackResult),
      lastAudioPath: lastAudioPath ?? this.lastAudioPath,
      lastReferenceText: lastReferenceText ?? this.lastReferenceText,
      isQuickResult: isQuickResult ?? this.isQuickResult,
    );
  }
}

class ApiNotifier extends StateNotifier<ApiState> {
  final PronunciaApiService _service;

  ApiNotifier(this._service) : super(ApiState());

  Future<void> processAudio(
    String? path, {
    String? referenceText,
    String? lang,
    String? evaluationLevel,
    String? mode,
    bool quick = true,
  }) async {
    if (path == null || path.trim().isEmpty) {
      state = state.copyWith(
        isLoading: false,
        error: 'No audio captured. Tap to record and try again.',
        clearResult: true,
        clearFeedback: true,
      );
      return;
    }

    state = state.copyWith(
      isLoading: true,
      error: null,
      clearResult: true,
      clearFeedback: true,
    );
    try {
      TranscriptionResult result;
      final trimmedReference = referenceText?.trim();
      if (trimmedReference != null && trimmedReference.isNotEmpty) {
        if (quick) {
          result = await _service.quickCompare(
            path,
            trimmedReference,
            lang: lang ?? 'es',
            evaluationLevel: evaluationLevel,
            mode: mode,
          );
        } else {
          result = await _service.compare(
            path,
            trimmedReference,
            lang: lang ?? 'es',
            evaluationLevel: evaluationLevel,
            mode: mode,
          );
        }
      } else {
        result = await _service.transcribe(path, lang: lang ?? 'es');
      }
      _logAudioChainToOverlay(result.meta);
      state = state.copyWith(
        isLoading: false,
        result: result,
        lastAudioPath: path,
        lastReferenceText: trimmedReference,
        isQuickResult: quick && trimmedReference != null && trimmedReference.isNotEmpty,
      );
    } on TimeoutException catch (e) {
      AppLogger.w('ApiNotifier', 'Timeout error: $e');
      state = state.copyWith(
        isLoading: false,
        error: 'Timeout: El servidor tardó demasiado en responder.',
        clearResult: true,
        clearFeedback: true,
      );
    } on SocketException catch (e) {
      AppLogger.w('ApiNotifier', 'Socket error: $e');
      state = state.copyWith(
        isLoading: false,
        error: 'Error de red: No se pudo conectar a ${_service.baseUrl}. ¿Está el backend encendido?',
        clearResult: true,
        clearFeedback: true,
      );
    } catch (e, stack) {
      AppLogger.e('ApiNotifier', 'Unhandled error: $e', error: e, stackTrace: stack);
      String msg = e.toString();
      if (msg.startsWith('Exception: ')) {
        msg = msg.substring(11);
      }
      state = state.copyWith(
        isLoading: false,
        error: msg,
        clearResult: true,
        clearFeedback: true,
      );
    }
  }
  /// Re-process the last recording with full analysis (quality gates, adaptation).
  Future<void> reprocessFull({
    String? lang,
    String? evaluationLevel,
    String? mode,
  }) async {
    final path = state.lastAudioPath;
    final ref = state.lastReferenceText;
    if (path == null || ref == null || ref.isEmpty) return;
    await processAudio(
      path,
      referenceText: ref,
      lang: lang,
      evaluationLevel: evaluationLevel,
      mode: mode,
      quick: false,
    );
  }
}

final apiNotifierProvider = StateNotifierProvider<ApiNotifier, ApiState>((ref) {
  final service = ref.watch(apiServiceProvider);
  return ApiNotifier(service);
});

// ── Audio chain debug overlay ─────────────────────────────────────────────────

/// Logs the audio processing chain metadata from the server response
/// to the debug overlay Events tab (visible via the 🐛 button in the app).
/// Only runs in debug builds; no-op otherwise.
void _logAudioChainToOverlay(Map<String, dynamic>? meta) {
  if (!kDebugMode || meta == null) return;

  final steps = (meta['steps'] as List?)?.join(' → ') ?? '?';
  final ensureWav = meta['ensure_wav'] as Map?;
  final agc = meta['agc'] as Map?;
  final vad = meta['vad'] as Map?;
  final quality = meta['quality'] as Map?;

  final lines = <String>[
    '🎵 Pipeline: $steps',
    if (ensureWav != null)
      '  ensure_wav: converted=${ensureWav['converted'] ?? false}',
    if (agc != null)
      '  agc: applied=${agc['applied'] ?? false}  target=${agc['target_dbfs'] ?? '?'} dBFS',
    if (vad != null) ...[
      '  vad: ratio=${(vad['speech_ratio'] as num?)?.toStringAsFixed(2) ?? '?'}  dur=${vad['duration_ms'] ?? '?'}ms  segs=${vad['speech_segments'] ?? '?'}',
      '  vad: trimmed=${vad['trimmed'] ?? false}  suggestion=${vad['trim_suggestion'] ?? 'none'}',
    ],
    if (quality != null)
      '  quality: passed=${quality['passed'] ?? '?'}  warnings=${(quality['warnings'] as List?)?.length ?? 0}',
  ];

  DebugLogStore.instance.addApp(AppLogEntry(
    tag: 'AudioChain',
    message: lines.join('\n'),
    level: AppLogLevel.debug,
    timestamp: DateTime.now(),
  ));
}
