import 'dart:convert';

class IpaSound {
  final String? id;
  final String? ipa;
  final String? label;
  final List<String> aliases;
  final List<String> tags;

  const IpaSound({
    this.id,
    this.ipa,
    this.label,
    this.aliases = const [],
    this.tags = const [],
  });

  factory IpaSound.fromJson(Map<String, dynamic> json) {
    return IpaSound(
      id: json['id'] as String?,
      ipa: json['ipa'] as String?,
      label: json['label'] as String?,
      aliases: _asStringList(json['aliases']),
      tags: _asStringList(json['tags']),
    );
  }
}

class IpaExample {
  final String? id;
  final String? text;
  final String? ipa;
  final String? position;
  final String? context;
  final String? source;
  final bool validated;

  const IpaExample({
    this.id,
    this.text,
    this.ipa,
    this.position,
    this.context,
    this.source,
    this.validated = false,
  });

  factory IpaExample.fromJson(Map<String, dynamic> json) {
    return IpaExample(
      id: json['id'] as String?,
      text: json['text'] as String?,
      ipa: json['ipa'] as String?,
      position: json['position'] as String?,
      context: json['context'] as String?,
      source: json['source'] as String?,
      validated: json['validated'] == true,
    );
  }
}

abstract class IpaCliPayload {
  final String kind;
  final Map<String, dynamic> request;
  final List<String> warnings;
  final String? confidence;

  const IpaCliPayload({
    required this.kind,
    required this.request,
    this.warnings = const [],
    this.confidence,
  });
}

class IpaExplorePayload extends IpaCliPayload {
  final IpaSound? sound;
  final List<IpaExample> examples;

  const IpaExplorePayload({
    required super.kind,
    required super.request,
    super.warnings,
    super.confidence,
    this.sound,
    this.examples = const [],
  });
}

class IpaPracticeSetPayload extends IpaCliPayload {
  final IpaSound? sound;
  final List<IpaExample> items;

  const IpaPracticeSetPayload({
    required super.kind,
    required super.request,
    super.warnings,
    super.confidence,
    this.sound,
    this.items = const [],
  });
}

IpaCliPayload? parseIpaCliPayload(String raw) {
  final data = jsonDecode(raw);
  if (data is! Map<String, dynamic>) {
    return null;
  }
  final kind = data['kind'] as String?;
  if (kind == null) {
    return null;
  }
  final request = _asMap(data['request']);
  final warnings = _asStringList(data['warnings']);
  final confidence = data['confidence'] as String?;
  final sound = data['sound'] is Map<String, dynamic>
      ? IpaSound.fromJson(data['sound'] as Map<String, dynamic>)
      : null;
  if (kind == 'ipa.explore') {
    final examples = _asList(data['examples'])
        .whereType<Map<String, dynamic>>()
        .map(IpaExample.fromJson)
        .toList();
    return IpaExplorePayload(
      kind: kind,
      request: request,
      warnings: warnings,
      confidence: confidence,
      sound: sound,
      examples: examples,
    );
  }
  if (kind == 'ipa.practice.set') {
    final items = _asList(data['items'])
        .whereType<Map<String, dynamic>>()
        .map(IpaExample.fromJson)
        .toList();
    return IpaPracticeSetPayload(
      kind: kind,
      request: request,
      warnings: warnings,
      confidence: confidence,
      sound: sound,
      items: items,
    );
  }
  return null;
}

List<String> _asStringList(dynamic value) {
  if (value is List) {
    return value.whereType<String>().toList();
  }
  return const [];
}

List<dynamic> _asList(dynamic value) {
  if (value is List) {
    return value;
  }
  return const [];
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }
  return const {};
}
