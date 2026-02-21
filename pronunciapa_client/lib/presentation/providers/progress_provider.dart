import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Progress data for a single sound
class SoundProgress {
  final String soundId;
  final int practiceCount;
  final int correctCount;
  final DateTime? lastPracticed;
  final int streak;
  final bool mastered;

  SoundProgress({
    required this.soundId,
    this.practiceCount = 0,
    this.correctCount = 0,
    this.lastPracticed,
    this.streak = 0,
    this.mastered = false,
  });

  double get accuracy => practiceCount > 0 ? correctCount / practiceCount : 0;
  
  int get masteryLevel {
    if (mastered) return 5;
    if (accuracy >= 0.9 && practiceCount >= 20) return 4;
    if (accuracy >= 0.8 && practiceCount >= 10) return 3;
    if (accuracy >= 0.6 && practiceCount >= 5) return 2;
    if (practiceCount > 0) return 1;
    return 0;
  }

  SoundProgress copyWith({
    String? soundId,
    int? practiceCount,
    int? correctCount,
    DateTime? lastPracticed,
    int? streak,
    bool? mastered,
  }) {
    return SoundProgress(
      soundId: soundId ?? this.soundId,
      practiceCount: practiceCount ?? this.practiceCount,
      correctCount: correctCount ?? this.correctCount,
      lastPracticed: lastPracticed ?? this.lastPracticed,
      streak: streak ?? this.streak,
      mastered: mastered ?? this.mastered,
    );
  }

  Map<String, dynamic> toJson() => {
    'soundId': soundId,
    'practiceCount': practiceCount,
    'correctCount': correctCount,
    'lastPracticed': lastPracticed?.toIso8601String(),
    'streak': streak,
    'mastered': mastered,
  };

  factory SoundProgress.fromJson(Map<String, dynamic> json) {
    return SoundProgress(
      soundId: json['soundId'] as String,
      practiceCount: json['practiceCount'] as int? ?? 0,
      correctCount: json['correctCount'] as int? ?? 0,
      lastPracticed: json['lastPracticed'] != null 
          ? DateTime.parse(json['lastPracticed'] as String)
          : null,
      streak: json['streak'] as int? ?? 0,
      mastered: json['mastered'] as bool? ?? false,
    );
  }
}

/// Overall learning progress state
class LearningProgressState {
  final Map<String, SoundProgress> soundProgress;
  final int totalPracticeTime; // in minutes
  final int currentStreak; // daily streak
  final DateTime? lastSessionDate;
  final List<String> completedModules;
  final int xp;

  LearningProgressState({
    this.soundProgress = const {},
    this.totalPracticeTime = 0,
    this.currentStreak = 0,
    this.lastSessionDate,
    this.completedModules = const [],
    this.xp = 0,
  });

  int get soundsMastered => soundProgress.values.where((p) => p.mastered).length;
  int get soundsPracticed => soundProgress.values.where((p) => p.practiceCount > 0).length;
  double get overallAccuracy {
    final practiced = soundProgress.values.where((p) => p.practiceCount > 0);
    if (practiced.isEmpty) return 0;
    return practiced.map((p) => p.accuracy).reduce((a, b) => a + b) / practiced.length;
  }

  LearningProgressState copyWith({
    Map<String, SoundProgress>? soundProgress,
    int? totalPracticeTime,
    int? currentStreak,
    DateTime? lastSessionDate,
    List<String>? completedModules,
    int? xp,
  }) {
    return LearningProgressState(
      soundProgress: soundProgress ?? this.soundProgress,
      totalPracticeTime: totalPracticeTime ?? this.totalPracticeTime,
      currentStreak: currentStreak ?? this.currentStreak,
      lastSessionDate: lastSessionDate ?? this.lastSessionDate,
      completedModules: completedModules ?? this.completedModules,
      xp: xp ?? this.xp,
    );
  }

  Map<String, dynamic> toJson() => {
    'soundProgress': soundProgress.map((k, v) => MapEntry(k, v.toJson())),
    'totalPracticeTime': totalPracticeTime,
    'currentStreak': currentStreak,
    'lastSessionDate': lastSessionDate?.toIso8601String(),
    'completedModules': completedModules,
    'xp': xp,
  };

  factory LearningProgressState.fromJson(Map<String, dynamic> json) {
    return LearningProgressState(
      soundProgress: (json['soundProgress'] as Map<String, dynamic>?)
          ?.map((k, v) => MapEntry(k, SoundProgress.fromJson(v)))
          ?? {},
      totalPracticeTime: json['totalPracticeTime'] as int? ?? 0,
      currentStreak: json['currentStreak'] as int? ?? 0,
      lastSessionDate: json['lastSessionDate'] != null
          ? DateTime.parse(json['lastSessionDate'] as String)
          : null,
      completedModules: (json['completedModules'] as List<dynamic>?)
          ?.cast<String>()
          ?? [],
      xp: json['xp'] as int? ?? 0,
    );
  }
}

/// Provider for managing learning progress with persistence
class ProgressNotifier extends StateNotifier<LearningProgressState> {
  static const String _storageKey = 'learning_progress';
  
  ProgressNotifier() : super(LearningProgressState()) {
    _loadProgress();
  }

  Future<void> _loadProgress() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final data = prefs.getString(_storageKey);
      if (data != null) {
        state = LearningProgressState.fromJson(json.decode(data));
        _checkDailyStreak();
      }
    } catch (e) {
      // If loading fails, start fresh
    }
  }

  Future<void> _saveProgress() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_storageKey, json.encode(state.toJson()));
    } catch (e) {
      // Silent fail
    }
  }

  void _checkDailyStreak() {
    final today = DateTime.now();
    final lastSession = state.lastSessionDate;
    
    if (lastSession != null) {
      final daysDiff = today.difference(lastSession).inDays;
      if (daysDiff > 1) {
        // Streak broken
        state = state.copyWith(currentStreak: 0);
        _saveProgress();
      }
    }
  }

  /// Record a practice attempt for a sound
  void recordPractice({
    required String soundId,
    required bool correct,
  }) {
    final existing = state.soundProgress[soundId] ?? SoundProgress(soundId: soundId);
    final today = DateTime.now();
    
    // Check if practicing on a new day
    int newStreak = state.currentStreak;
    if (state.lastSessionDate == null || 
        !_isSameDay(state.lastSessionDate!, today)) {
      newStreak = state.currentStreak + 1;
    }

    final updated = existing.copyWith(
      practiceCount: existing.practiceCount + 1,
      correctCount: existing.correctCount + (correct ? 1 : 0),
      lastPracticed: today,
      streak: correct ? existing.streak + 1 : 0,
    );

    // Check for mastery
    final mastered = updated.accuracy >= 0.9 && 
                     updated.practiceCount >= 20 && 
                     updated.streak >= 5;

    final newSoundProgress = Map<String, SoundProgress>.from(state.soundProgress);
    newSoundProgress[soundId] = updated.copyWith(mastered: mastered);

    // Award XP
    int xpGain = correct ? 10 : 2;
    if (mastered && !existing.mastered) xpGain += 100; // Bonus for mastery

    state = state.copyWith(
      soundProgress: newSoundProgress,
      lastSessionDate: today,
      currentStreak: newStreak,
      xp: state.xp + xpGain,
    );

    _saveProgress();
  }

  /// Mark a module as completed
  void completeModule(String moduleId) {
    if (!state.completedModules.contains(moduleId)) {
      state = state.copyWith(
        completedModules: [...state.completedModules, moduleId],
        xp: state.xp + 50,
      );
      _saveProgress();
    }
  }

  /// Get progress for a specific sound
  SoundProgress? getProgressForSound(String soundId) {
    return state.soundProgress[soundId];
  }

  /// Add practice time
  void addPracticeTime(int minutes) {
    state = state.copyWith(
      totalPracticeTime: state.totalPracticeTime + minutes,
    );
    _saveProgress();
  }

  /// Reset all progress (for testing)
  Future<void> resetProgress() async {
    state = LearningProgressState();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_storageKey);
  }

  bool _isSameDay(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }
}

final progressProvider = StateNotifierProvider<ProgressNotifier, LearningProgressState>((ref) {
  return ProgressNotifier();
});

/// Quick access to a specific sound's progress
final soundProgressProvider = Provider.family<SoundProgress?, String>((ref, soundId) {
  final state = ref.watch(progressProvider);
  return state.soundProgress[soundId];
});
