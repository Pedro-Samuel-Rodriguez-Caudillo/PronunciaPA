import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

/// Model for IPA learning module
class IpaModule {
  final String id;
  final String title;
  final String? description;
  final String? content;

  IpaModule({
    required this.id,
    required this.title,
    this.description,
    this.content,
  });

  factory IpaModule.fromJson(Map<String, dynamic> json) {
    return IpaModule(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      content: json['content'] as String?,
    );
  }
}

/// Model for sound lesson
class SoundLesson {
  final String id;
  final String ipa;
  final String? commonName;
  final int difficulty;

  SoundLesson({
    required this.id,
    required this.ipa,
    this.commonName,
    this.difficulty = 1,
  });

  factory SoundLesson.fromJson(Map<String, dynamic> json) {
    return SoundLesson(
      id: json['id'] as String,
      ipa: json['ipa'] as String,
      commonName: json['common_name'] as String?,
      difficulty: json['difficulty'] as int? ?? 1,
    );
  }
}

/// Model for drill exercise
class Drill {
  final String type;
  final String? instruction;
  final List<String> targets;
  final List<DrillTarget> targetsWithAudio;
  final List<DrillPair> pairsWithAudio;

  Drill({
    required this.type,
    this.instruction,
    this.targets = const [],
    this.targetsWithAudio = const [],
    this.pairsWithAudio = const [],
  });

  factory Drill.fromJson(Map<String, dynamic> json) {
    return Drill(
      type: json['type'] as String,
      instruction: json['instruction'] as String?,
      targets: (json['targets'] as List<dynamic>?)?.cast<String>() ?? [],
      targetsWithAudio: (json['targets_with_audio'] as List<dynamic>?)
          ?.map((e) => DrillTarget.fromJson(e))
          .toList() ?? [],
      pairsWithAudio: (json['pairs_with_audio'] as List<dynamic>?)
          ?.map((e) => DrillPair.fromJson(e))
          .toList() ?? [],
    );
  }
}

class DrillTarget {
  final String text;
  final String audioUrl;

  DrillTarget({required this.text, required this.audioUrl});

  factory DrillTarget.fromJson(Map<String, dynamic> json) {
    return DrillTarget(
      text: json['text'] as String,
      audioUrl: json['audio_url'] as String,
    );
  }
}

class DrillPair {
  final String word1;
  final String word2;
  final String audio1Url;
  final String audio2Url;

  DrillPair({
    required this.word1,
    required this.word2,
    required this.audio1Url,
    required this.audio2Url,
  });

  factory DrillPair.fromJson(Map<String, dynamic> json) {
    return DrillPair(
      word1: json['word1'] as String,
      word2: json['word2'] as String,
      audio1Url: json['audio1_url'] as String,
      audio2Url: json['audio2_url'] as String,
    );
  }
}

/// State for IPA learning
class IpaLearningState {
  final List<IpaModule> modules;
  final List<SoundLesson> sounds;
  final Map<String, int> inventory;
  final String? selectedLang;
  final bool isLoading;
  final String? error;

  IpaLearningState({
    this.modules = const [],
    this.sounds = const [],
    this.inventory = const {},
    this.selectedLang,
    this.isLoading = false,
    this.error,
  });

  IpaLearningState copyWith({
    List<IpaModule>? modules,
    List<SoundLesson>? sounds,
    Map<String, int>? inventory,
    String? selectedLang,
    bool? isLoading,
    String? error,
  }) {
    return IpaLearningState(
      modules: modules ?? this.modules,
      sounds: sounds ?? this.sounds,
      inventory: inventory ?? this.inventory,
      selectedLang: selectedLang ?? this.selectedLang,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Provider for IPA learning content
class IpaLearningNotifier extends StateNotifier<IpaLearningState> {
  static const String _baseUrl = 'http://127.0.0.1:8000';

  IpaLearningNotifier() : super(IpaLearningState()) {
    loadContent('en'); // Default to English
  }

  Future<void> loadContent(String lang) async {
    state = state.copyWith(isLoading: true, error: null, selectedLang: lang);

    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/ipa-learn/$lang'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);

        final modules = (data['modules'] as List<dynamic>?)
            ?.map((e) => IpaModule.fromJson(e))
            .toList() ?? [];

        final sounds = (data['sounds'] as List<dynamic>?)
            ?.map((e) => SoundLesson.fromJson(e))
            .toList() ?? [];

        final inventory = (data['inventory'] as Map<String, dynamic>?)
            ?.map((k, v) => MapEntry(k, v as int)) ?? {};

        state = state.copyWith(
          modules: modules,
          sounds: sounds,
          inventory: inventory,
          isLoading: false,
        );
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Failed to load content: ${response.statusCode}',
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Connection error: $e',
      );
    }
  }

  Future<List<Drill>> loadDrills(String soundId) async {
    try {
      final lang = state.selectedLang ?? 'en';
      // Extract just the IPA symbol from the sound_id
      final ipa = soundId.contains('/') ? soundId.split('/').last : soundId;
      
      final response = await http.get(
        Uri.parse('$_baseUrl/api/ipa-drills/$lang/$ipa'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return (data['drills'] as List<dynamic>?)
            ?.map((e) => Drill.fromJson(e))
            .toList() ?? [];
      }
    } catch (e) {
      // Silently fail, return empty
    }
    return [];
  }
}

final ipaLearningProvider =
    StateNotifierProvider<IpaLearningNotifier, IpaLearningState>((ref) {
  return IpaLearningNotifier();
});
