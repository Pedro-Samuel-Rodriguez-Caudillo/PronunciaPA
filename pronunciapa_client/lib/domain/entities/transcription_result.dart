import 'package:pronunciapa_client/domain/entities/feedback_result.dart';

/// Domain entity for transcription results
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

  factory TranscriptionResult.fromJson(Map<String, dynamic> json) {
    return TranscriptionResult(
      ipa: json['ipa'] as String? ?? '',
      score: (json['score'] as num?)?.toDouble(),
      per: (json['per'] as num?)?.toDouble(),
      alignment: _parseAlignment(json['alignment']),
      ops: _parseOps(json['ops']),
      tokens: (json['tokens'] as List?)?.cast<String>(),
      mode: json['mode'] as String?,
      evaluationLevel: json['evaluation_level'] as String?,
      targetIpa: json['target_ipa'] as String?,
      meta: json['meta'] as Map<String, dynamic>?,
    );
  }

  static List<List<String?>>? _parseAlignment(dynamic value) {
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

  static List<EditOp>? _parseOps(dynamic value) {
    if (value == null) return null;
    if (value is! List) return null;
    try {
      return value
          .map((op) => EditOp.fromJson(op as Map<String, dynamic>))
          .toList();
    } catch (e) {
      return null;
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'ipa': ipa,
      if (score != null) 'score': score,
      if (per != null) 'per': per,
      if (alignment != null) 'alignment': alignment,
      if (ops != null) 'ops': ops!.map((op) => op.toJson()).toList(),
      if (tokens != null) 'tokens': tokens,
      if (mode != null) 'mode': mode,
      if (evaluationLevel != null) 'evaluation_level': evaluationLevel,
      if (targetIpa != null) 'target_ipa': targetIpa,
      if (meta != null) 'meta': meta,
    };
  }
}
