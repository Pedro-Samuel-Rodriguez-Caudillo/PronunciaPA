import 'transcription_result.dart';

/// Domain entity for edit operations in alignment
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

  Map<String, dynamic> toJson() {
    return {
      'op': op,
      if (ref != null) 'ref': ref,
      if (hyp != null) 'hyp': hyp,
    };
  }
}

/// Domain entity for feedback drills
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

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'text': text,
    };
  }
}

/// Domain entity for feedback payload with advice and drills
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

  Map<String, dynamic> toJson() {
    return {
      'summary': summary,
      'advice_short': adviceShort,
      'advice_long': adviceLong,
      'drills': drills.map((d) => d.toJson()).toList(),
      if (feedbackLevel != null) 'feedback_level': feedbackLevel,
      if (tone != null) 'tone': tone,
      if (confidence != null) 'confidence': confidence,
      if (warnings != null) 'warnings': warnings,
    };
  }
}

/// Domain entity for complete feedback result
class FeedbackResult {
  final TranscriptionResult compare;
  final FeedbackPayload feedback;
  final Map<String, dynamic> report;

  FeedbackResult({
    required this.compare,
    required this.feedback,
    required this.report,
  });

  factory FeedbackResult.fromJson(Map<String, dynamic> json) {
    return FeedbackResult(
      compare: TranscriptionResult.fromJson(json['compare'] as Map<String, dynamic>),
      feedback: FeedbackPayload.fromJson(json['feedback'] as Map<String, dynamic>),
      report: json['report'] as Map<String, dynamic>,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'compare': compare.toJson(),
      'feedback': feedback.toJson(),
      'report': report,
    };
  }
}
