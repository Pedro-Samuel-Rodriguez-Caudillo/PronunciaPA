import 'package:flutter/material.dart';
import '../providers/game_stats_provider.dart';
import '../theme/app_theme.dart';

/// Widget to display gamification stats (level, XP, streak)
class GameStatsWidget extends StatelessWidget {
  final GameStats stats;
  final bool compact;

  const GameStatsWidget({
    super.key,
    required this.stats,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return _buildCompact(context);
    }
    return _buildFull(context);
  }

  Widget _buildCompact(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Level badge
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            gradient: AppTheme.primaryGradient,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            'Lvl ${stats.level}',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
        const SizedBox(width: 8),
        // Streak badge
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            gradient: AppTheme.accentGradient,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            '🔥${stats.streak}',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFull(BuildContext context) {
    final theme = Theme.of(context);
    final glass = theme.extension<AppGlassTheme>();

    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '🏆 Tu Progreso',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),

          // Stats grid
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  context,
                  value: '${stats.level}',
                  label: stats.levelName,
                  sublabel: '${stats.xp}/${stats.xpToNextLevel} XP',
                  progress: stats.xpProgress,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStatCard(
                  context,
                  value: '${stats.totalPractices}',
                  label: 'Prácticas',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  context,
                  value: '${(stats.avgScore * 100).round()}%',
                  label: 'Promedio',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStatCard(
                  context,
                  value: '🔥${stats.streak}',
                  label: 'Racha',
                ),
              ),
            ],
          ),

          // Achievements
          if (stats.achievements.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Logros desbloqueados',
              style: theme.textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: stats.achievements.map((id) {
                final achievement = allAchievements.firstWhere(
                  (a) => a.id == id,
                  orElse: () => const Achievement(
                    id: '',
                    title: '',
                    description: '',
                    emoji: '🏆',
                  ),
                );
                return Tooltip(
                  message: achievement.title,
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: glass?.panel ??
                          theme.colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: glass?.border ??
                            theme.colorScheme.outlineVariant,
                      ),
                    ),
                    child: Text(
                      achievement.emoji,
                      style: const TextStyle(fontSize: 20),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatCard(
    BuildContext context, {
    required String value,
    required String label,
    String? sublabel,
    double? progress,
  }) {
    final theme = Theme.of(context);
    final glass = theme.extension<AppGlassTheme>();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: glass?.panel ??
            theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: glass?.border ?? theme.colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          if (sublabel != null) ...[
            const SizedBox(height: 4),
            Text(
              sublabel,
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant.withOpacity(0.7),
              ),
            ),
          ],
          if (progress != null) ...[
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 4,
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Dialog to show when achievement is unlocked
class AchievementDialog extends StatelessWidget {
  final Achievement achievement;

  const AchievementDialog({
    super.key,
    required this.achievement,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 16),
          Text(
            achievement.emoji,
            style: const TextStyle(fontSize: 64),
          ),
          const SizedBox(height: 16),
          Text(
            '¡Logro desbloqueado!',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            achievement.title,
            style: theme.textTheme.titleMedium?.copyWith(
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            achievement.description,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
      actions: [
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('¡Genial!'),
        ),
      ],
    );
  }

  static Future<void> show(BuildContext context, Achievement achievement) {
    return showDialog(
      context: context,
      builder: (ctx) => AchievementDialog(achievement: achievement),
    );
  }
}
