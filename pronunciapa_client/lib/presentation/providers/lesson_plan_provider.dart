import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'repository_provider.dart';

// ── Domain models ─────────────────────────────────────────────────────────────

class LessonDrillItem {
  final String type;
  final String text;

  const LessonDrillItem({required this.type, required this.text});

  factory LessonDrillItem.fromJson(Map<String, dynamic> j) =>
      LessonDrillItem(
          type: (j['type'] as String?) ?? '',
          text: (j['text'] as String?) ?? '');
}

class LessonPlan {
  final String recommendedSoundId;
  final String topicId;
  final String intro;
  final List<String> tips;
  final List<LessonDrillItem> drills;
  final Map<String, dynamic> meta;

  const LessonPlan({
    required this.recommendedSoundId,
    required this.topicId,
    required this.intro,
    required this.tips,
    required this.drills,
    this.meta = const {},
  });

  factory LessonPlan.fromJson(Map<String, dynamic> j) => LessonPlan(
        recommendedSoundId: j['recommended_sound_id'] as String? ?? '',
        topicId: j['topic_id'] as String? ?? '',
        intro: j['intro'] as String? ?? '',
        tips: (j['tips'] as List<dynamic>?)?.cast<String>() ?? [],
        drills: (j['drills'] as List<dynamic>?)
                ?.map((e) => LessonDrillItem.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
        meta: j['meta'] as Map<String, dynamic>? ?? {},
      );
}

class RoadmapTopic {
  final String topicId;
  final String name;
  final String level; // not_started | in_progress | proficient | completed
  final int order;

  const RoadmapTopic({
    required this.topicId,
    required this.name,
    required this.level,
    required this.order,
  });

  factory RoadmapTopic.fromJson(Map<String, dynamic> j) => RoadmapTopic(
        topicId: j['topic_id'] as String,
        name: j['name'] as String,
        level: j['level'] as String? ?? 'not_started',
        order: j['order'] as int? ?? 0,
      );

  double get progress {
    switch (level) {
      case 'in_progress':
        return 0.35;
      case 'proficient':
        return 0.65;
      case 'completed':
        return 1.0;
      default:
        return 0.0;
    }
  }

  String get levelLabel {
    switch (level) {
      case 'in_progress':
        return 'En proceso';
      case 'proficient':
        return 'Competente';
      case 'completed':
        return 'Completado';
      default:
        return 'Sin iniciar';
    }
  }
}

class RoadmapState {
  final String userId;
  final String lang;
  final List<RoadmapTopic> topics;

  const RoadmapState({
    required this.userId,
    required this.lang,
    required this.topics,
  });

  factory RoadmapState.fromJson(Map<String, dynamic> j) => RoadmapState(
        userId: j['user_id'] as String,
        lang: j['lang'] as String,
        topics: (j['topics'] as List<dynamic>?)
                ?.map((e) => RoadmapTopic.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
      );
}

// ── State ─────────────────────────────────────────────────────────────────────

class LessonPlanState {
  final bool isLoading;
  final LessonPlan? plan;
  final RoadmapState? roadmap;
  final String? error;

  const LessonPlanState({
    this.isLoading = false,
    this.plan,
    this.roadmap,
    this.error,
  });

  LessonPlanState copyWith({
    bool? isLoading,
    LessonPlan? plan,
    RoadmapState? roadmap,
    String? error,
    bool clearError = false,
  }) =>
      LessonPlanState(
        isLoading: isLoading ?? this.isLoading,
        plan: plan ?? this.plan,
        roadmap: roadmap ?? this.roadmap,
        error: clearError ? null : (error ?? this.error),
      );
}

// ── Notifier ──────────────────────────────────────────────────────────────────

class LessonPlanNotifier extends StateNotifier<LessonPlanState> {
  final Ref _ref;
  String _userId;
  String _lang;

  LessonPlanNotifier(this._ref, {String userId = 'demo', String lang = 'es'})
      : _userId = userId,
        _lang = lang,
        super(const LessonPlanState());

  Future<void> loadAll() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final ds = _ref.read(remoteDataSourceProvider);
      final results = await Future.wait([
        ds.getRoadmapProgress(_userId, _lang),
        ds.getLessonPlan(_userId, _lang),
      ]);
      state = state.copyWith(
        isLoading: false,
        roadmap: RoadmapState.fromJson(results[0] as Map<String, dynamic>),
        plan: LessonPlan.fromJson(results[1] as Map<String, dynamic>),
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadPlanForSound(String soundId) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final ds = _ref.read(remoteDataSourceProvider);
      final result =
          await ds.getLessonPlan(_userId, _lang, soundId: soundId);
      state = state.copyWith(
        isLoading: false,
        plan: LessonPlan.fromJson(result as Map<String, dynamic>),
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void setUser(String userId) {
    _userId = userId;
    state = const LessonPlanState();
  }

  void setLang(String lang) {
    _lang = lang;
    state = const LessonPlanState();
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

final lessonPlanProvider =
    StateNotifierProvider<LessonPlanNotifier, LessonPlanState>(
  (ref) => LessonPlanNotifier(ref),
);
