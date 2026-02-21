import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Feedback level for evaluation explanations
enum FeedbackLevel {
  casual, // Simple, friendly explanations
  precise, // Technical, detailed explanations
}

/// Widget for selecting feedback level (casual vs precise)
class FeedbackLevelSelector extends StatelessWidget {
  final FeedbackLevel currentLevel;
  final ValueChanged<FeedbackLevel> onLevelChanged;

  const FeedbackLevelSelector({
    super.key,
    required this.currentLevel,
    required this.onLevelChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final glass = theme.extension<AppGlassTheme>();
    
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: glass?.surface ?? theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: glass?.border ?? theme.colorScheme.outlineVariant,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildLevelButton(
            context,
            level: FeedbackLevel.casual,
            label: '🎯 Simple',
            description: 'Para principiantes',
            isActive: currentLevel == FeedbackLevel.casual,
          ),
          const SizedBox(width: 4),
          _buildLevelButton(
            context,
            level: FeedbackLevel.precise,
            label: '🔬 Técnico',
            description: 'Análisis detallado',
            isActive: currentLevel == FeedbackLevel.precise,
          ),
        ],
      ),
    );
  }

  Widget _buildLevelButton(
    BuildContext context, {
    required FeedbackLevel level,
    required String label,
    required String description,
    required bool isActive,
  }) {
    final theme = Theme.of(context);

    return Expanded(
      child: GestureDetector(
        onTap: () => onLevelChanged(level),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 12,
          ),
          decoration: BoxDecoration(
            gradient: isActive ? AppTheme.coolGradient : null,
            color: isActive ? null : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            boxShadow: isActive
                ? [
                    BoxShadow(
                      color: AppTheme.coolStart.withOpacity(0.35),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    )
                  ]
                : null,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: isActive
                      ? Colors.white
                      : theme.colorScheme.onSurfaceVariant,
                  fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                  fontSize: 14,
                ),
              ),
              if (isActive) ...[
                const SizedBox(height: 4),
                Text(
                  description,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.8),
                    fontSize: 11,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
