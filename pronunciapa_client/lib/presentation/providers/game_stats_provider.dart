import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Gamification state for PronunciaPA
/// Includes XP, levels, achievements, and streaks
class GameStats {
  final int level;
  final int xp;
  final int xpToNextLevel;
  final int streak;
  final int totalPractices;
  final double avgScore;
  final List<String> achievements;
  final DateTime? lastPracticeDate;

  const GameStats({
    this.level = 1,
    this.xp = 0,
    this.xpToNextLevel = 100,
    this.streak = 0,
    this.totalPractices = 0,
    this.avgScore = 0.0,
    this.achievements = const [],
    this.lastPracticeDate,
  });

  GameStats copyWith({
    int? level,
    int? xp,
    int? xpToNextLevel,
    int? streak,
    int? totalPractices,
    double? avgScore,
    List<String>? achievements,
    DateTime? lastPracticeDate,
  }) {
    return GameStats(
      level: level ?? this.level,
      xp: xp ?? this.xp,
      xpToNextLevel: xpToNextLevel ?? this.xpToNextLevel,
      streak: streak ?? this.streak,
      totalPractices: totalPractices ?? this.totalPractices,
      avgScore: avgScore ?? this.avgScore,
      achievements: achievements ?? this.achievements,
      lastPracticeDate: lastPracticeDate ?? this.lastPracticeDate,
    );
  }

  Map<String, dynamic> toJson() => {
        'level': level,
        'xp': xp,
        'xpToNextLevel': xpToNextLevel,
        'streak': streak,
        'totalPractices': totalPractices,
        'avgScore': avgScore,
        'achievements': achievements,
        'lastPracticeDate': lastPracticeDate?.toIso8601String(),
      };

  factory GameStats.fromJson(Map<String, dynamic> json) {
    return GameStats(
      level: json['level'] ?? 1,
      xp: json['xp'] ?? 0,
      xpToNextLevel: json['xpToNextLevel'] ?? 100,
      streak: json['streak'] ?? 0,
      totalPractices: json['totalPractices'] ?? 0,
      avgScore: (json['avgScore'] ?? 0.0).toDouble(),
      achievements: List<String>.from(json['achievements'] ?? []),
      lastPracticeDate: json['lastPracticeDate'] != null
          ? DateTime.parse(json['lastPracticeDate'])
          : null,
    );
  }

  String get levelName {
    const names = {
      1: 'Principiante',
      2: 'Aprendiz',
      3: 'Intermedio',
      4: 'Avanzado',
      5: 'Experto',
      6: 'Maestro',
      7: 'Virtuoso',
      8: 'Legendario',
    };
    return names[level] ?? 'Nivel $level';
  }

  double get xpProgress => xp / xpToNextLevel;
}

/// Achievement with metadata
class Achievement {
  final String id;
  final String title;
  final String description;
  final String emoji;

  const Achievement({
    required this.id,
    required this.title,
    required this.description,
    required this.emoji,
  });
}

/// All available achievements
const allAchievements = [
  Achievement(
    id: 'first_practice',
    title: 'Primera práctica',
    description: 'Completa tu primera práctica de pronunciación',
    emoji: '🏆',
  ),
  Achievement(
    id: 'ten_practices',
    title: 'En racha',
    description: 'Completa 10 prácticas',
    emoji: '🏆',
  ),
  Achievement(
    id: 'hundred_practices',
    title: 'Experto',
    description: 'Completa 100 prácticas',
    emoji: '🏆',
  ),
  Achievement(
    id: 'excellent_score',
    title: 'Excelente pronunciación',
    description: 'Obtén una puntuación del 90% o más',
    emoji: '⭐',
  ),
  Achievement(
    id: 'perfect_score',
    title: 'Pronunciación perfecta',
    description: 'Obtén una puntuación del 95% o más',
    emoji: '⭐',
  ),
  Achievement(
    id: 'week_streak',
    title: 'Semana de fuego',
    description: 'Mantén una racha de 7 días',
    emoji: '🔥',
  ),
];

/// Gamification state notifier
class GameStatsNotifier extends StateNotifier<GameStats> {
  GameStatsNotifier() : super(const GameStats()) {
    _load();
  }

  static const _storageKey = 'pronunciapa_game_stats';

  Future<void> _load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(_storageKey);
      if (stored != null) {
        state = GameStats.fromJson(jsonDecode(stored));
        _checkStreak();
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

  void _checkStreak() {
    if (state.lastPracticeDate == null) return;

    final now = DateTime.now();
    final lastDate = state.lastPracticeDate!;
    final daysDiff = now.difference(lastDate).inDays;

    // Reset streak if more than 1 day has passed
    if (daysDiff > 1) {
      state = state.copyWith(streak: 0);
      _save();
    }
  }

  /// Add a practice result and return new achievements
  List<Achievement> addPractice(double score) {
    final newAchievements = <Achievement>[];
    final now = DateTime.now();

    // Update total practices
    final totalPractices = state.totalPractices + 1;

    // Update average score
    double avgScore;
    if (state.avgScore == 0) {
      avgScore = score;
    } else {
      avgScore =
          (state.avgScore * (totalPractices - 1) + score) / totalPractices;
    }

    // Calculate XP (higher score = more XP)
    final xpEarned = (score * 100).floor();
    var xp = state.xp + xpEarned;
    var level = state.level;
    var xpToNextLevel = state.xpToNextLevel;

    // Level up
    while (xp >= xpToNextLevel) {
      xp -= xpToNextLevel;
      level += 1;
      xpToNextLevel = (xpToNextLevel * 1.5).floor();
      // Level up is handled via UI notification, not as achievement
    }

    // Update streak
    var streak = state.streak;
    if (state.lastPracticeDate != null) {
      final daysDiff = now.difference(state.lastPracticeDate!).inDays;
      if (daysDiff == 1) {
        streak += 1;
      } else if (daysDiff > 1) {
        streak = 1;
      }
      // Same day = keep streak
    } else {
      streak = 1;
    }

    // Check achievements
    final achievements = List<String>.from(state.achievements);

    if (totalPractices == 1 && !achievements.contains('first_practice')) {
      achievements.add('first_practice');
      newAchievements
          .add(allAchievements.firstWhere((a) => a.id == 'first_practice'));
    }

    if (totalPractices == 10 && !achievements.contains('ten_practices')) {
      achievements.add('ten_practices');
      newAchievements
          .add(allAchievements.firstWhere((a) => a.id == 'ten_practices'));
    }

    if (totalPractices == 100 && !achievements.contains('hundred_practices')) {
      achievements.add('hundred_practices');
      newAchievements
          .add(allAchievements.firstWhere((a) => a.id == 'hundred_practices'));
    }

    if (score >= 0.95 && !achievements.contains('perfect_score')) {
      achievements.add('perfect_score');
      newAchievements
          .add(allAchievements.firstWhere((a) => a.id == 'perfect_score'));
    } else if (score >= 0.90 && !achievements.contains('excellent_score')) {
      achievements.add('excellent_score');
      newAchievements
          .add(allAchievements.firstWhere((a) => a.id == 'excellent_score'));
    }

    if (streak >= 7 && !achievements.contains('week_streak')) {
      achievements.add('week_streak');
      newAchievements
          .add(allAchievements.firstWhere((a) => a.id == 'week_streak'));
    }

    // Update state
    state = state.copyWith(
      level: level,
      xp: xp,
      xpToNextLevel: xpToNextLevel,
      streak: streak,
      totalPractices: totalPractices,
      avgScore: avgScore,
      achievements: achievements,
      lastPracticeDate: now,
    );

    _save();
    return newAchievements;
  }

  /// Reset all stats (for testing/debugging)
  void reset() {
    state = const GameStats();
    _save();
  }
}

/// Provider for game stats
final gameStatsProvider =
    StateNotifierProvider<GameStatsNotifier, GameStats>((ref) {
  return GameStatsNotifier();
});
