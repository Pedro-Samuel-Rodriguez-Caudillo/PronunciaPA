import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../widgets/mode_selector_widget.dart';

/// User preferences for the app
class UserPreferences {
  final String lang;
  final String langSource;
  final String langTarget;
  final TranscriptionMode mode;
  final String feedbackLevel; // 'casual' or 'precise'
  final String comparisonMode; // 'casual', 'objective', or 'phonetic'
  final bool darkMode;
  final bool hapticFeedback;
  final bool audioFeedback;
  final bool forcePhonetic;
  final bool allowQualityDowngrade;
  /// Model ID to pass as ?voice= to /api/tts/speak. null = server default.
  final String? selectedTtsVoice;

  const UserPreferences({
    this.lang = 'en',
    this.langSource = 'en',
    this.langTarget = 'en',
    this.mode = TranscriptionMode.phonemic,
    this.feedbackLevel = 'casual',
    this.comparisonMode = 'objective',
    this.darkMode = false,
    this.hapticFeedback = true,
    this.audioFeedback = true,
    this.forcePhonetic = false,
    this.allowQualityDowngrade = true,
    this.selectedTtsVoice,
  });

  UserPreferences copyWith({
    String? lang,
    String? langSource,
    String? langTarget,
    TranscriptionMode? mode,
    String? feedbackLevel,
    String? comparisonMode,
    bool? darkMode,
    bool? hapticFeedback,
    bool? audioFeedback,
    bool? forcePhonetic,
    bool? allowQualityDowngrade,
    String? selectedTtsVoice,
    bool clearTtsVoice = false,
  }) {
    return UserPreferences(
      lang: lang ?? this.lang,
      langSource: langSource ?? this.langSource,
      langTarget: langTarget ?? this.langTarget,
      mode: mode ?? this.mode,
      feedbackLevel: feedbackLevel ?? this.feedbackLevel,
      comparisonMode: comparisonMode ?? this.comparisonMode,
      darkMode: darkMode ?? this.darkMode,
      hapticFeedback: hapticFeedback ?? this.hapticFeedback,
      audioFeedback: audioFeedback ?? this.audioFeedback,
      forcePhonetic: forcePhonetic ?? this.forcePhonetic,
      allowQualityDowngrade:
          allowQualityDowngrade ?? this.allowQualityDowngrade,
      selectedTtsVoice: clearTtsVoice ? null : (selectedTtsVoice ?? this.selectedTtsVoice),
    );
  }

  Map<String, dynamic> toJson() => {
        'lang': lang,
      'langSource': langSource,
      'langTarget': langTarget,
        'mode': mode.name,
        'feedbackLevel': feedbackLevel,
        'comparisonMode': comparisonMode,
        'darkMode': darkMode,
        'hapticFeedback': hapticFeedback,
        'audioFeedback': audioFeedback,
        'forcePhonetic': forcePhonetic,
        'allowQualityDowngrade': allowQualityDowngrade,
        if (selectedTtsVoice != null) 'selectedTtsVoice': selectedTtsVoice,
      };

  factory UserPreferences.fromJson(Map<String, dynamic> json) {
    final resolvedLang = (json['lang'] ?? 'en') as String;
    return UserPreferences(
      lang: resolvedLang,
      langSource: (json['langSource'] ?? resolvedLang) as String,
      langTarget: (json['langTarget'] ?? resolvedLang) as String,
      mode: TranscriptionMode.values.firstWhere(
        (m) => m.name == json['mode'],
        orElse: () => TranscriptionMode.phonemic,
      ),
      feedbackLevel: json['feedbackLevel'] ?? 'casual',
      comparisonMode: json['comparisonMode'] ?? 'objective',
      darkMode: json['darkMode'] ?? false,
      hapticFeedback: json['hapticFeedback'] ?? true,
      audioFeedback: json['audioFeedback'] ?? true,
      forcePhonetic: json['forcePhonetic'] ?? false,
      allowQualityDowngrade: json['allowQualityDowngrade'] ?? true,
      selectedTtsVoice: json['selectedTtsVoice'] as String?,
    );
  }

  /// Get language display name
  String get langDisplayName {
    const names = {
      'es': 'Español',
      'en': 'English',
      'fr': 'Français',
      'de': 'Deutsch',
      'pt': 'Português',
      'it': 'Italiano',
    };
    return names[lang] ?? lang.toUpperCase();
  }

  /// Get language flag emoji
  String get langFlag {
    const flags = {
      'es': '🇪🇸',
      'en': '🇺🇸',
      'fr': '🇫🇷',
      'de': '🇩🇪',
      'pt': '🇧🇷',
      'it': '🇮🇹',
    };
    return flags[lang] ?? '🌍';
  }
}

/// Available languages
const availableLanguages = ['es', 'en', 'fr', 'de', 'pt', 'it'];

/// Preferences state notifier
class PreferencesNotifier extends StateNotifier<UserPreferences> {
  PreferencesNotifier() : super(const UserPreferences()) {
    _load();
  }

  static const _storageKey = 'pronunciapa_preferences';

  Future<void> _load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(_storageKey);
      if (stored != null) {
        state = UserPreferences.fromJson(jsonDecode(stored));
      }
    } catch (e) {
      // Keep default state
    }
  }

  Future<void> _save() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_storageKey, jsonEncode(state.toJson()));
    } catch (e) {
      // Ignore save errors
    }
  }

  void setLang(String lang) {
    state = state.copyWith(lang: lang, langSource: lang, langTarget: lang);
    _save();
  }

  void setLangSource(String lang) {
    state = state.copyWith(langSource: lang);
    _save();
  }

  void setLangTarget(String lang) {
    state = state.copyWith(langTarget: lang, lang: lang);
    _save();
  }

  void setMode(TranscriptionMode mode) {
    state = state.copyWith(mode: mode);
    _save();
  }

  void setFeedbackLevel(String level) {
    state = state.copyWith(feedbackLevel: level);
    _save();
  }

  void setComparisonMode(String mode) {
    state = state.copyWith(comparisonMode: mode);
    _save();
  }

  void setDarkMode(bool enabled) {
    state = state.copyWith(darkMode: enabled);
    _save();
  }

  void setHapticFeedback(bool enabled) {
    state = state.copyWith(hapticFeedback: enabled);
    _save();
  }

  void setAudioFeedback(bool enabled) {
    state = state.copyWith(audioFeedback: enabled);
    _save();
  }

  void setForcePhonetic(bool enabled) {
    state = state.copyWith(forcePhonetic: enabled);
    _save();
  }

  void setAllowQualityDowngrade(bool enabled) {
    state = state.copyWith(allowQualityDowngrade: enabled);
    _save();
  }

  void toggleMode() {
    final newMode = state.mode == TranscriptionMode.phonemic
        ? TranscriptionMode.phonetic
        : TranscriptionMode.phonemic;
    setMode(newMode);
  }

  void toggleFeedbackLevel() {
    final newLevel = state.feedbackLevel == 'casual' ? 'precise' : 'casual';
    setFeedbackLevel(newLevel);
  }

  void setTtsVoice(String? voiceId) {
    state = voiceId == null
        ? state.copyWith(clearTtsVoice: true)
        : state.copyWith(selectedTtsVoice: voiceId);
    _save();
  }
}

/// Provider for user preferences
final preferencesProvider =
    StateNotifierProvider<PreferencesNotifier, UserPreferences>((ref) {
  return PreferencesNotifier();
});
