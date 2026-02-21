import 'package:flutter/material.dart';
import '../providers/progress_provider.dart';

/// Circular progress indicator for mastery level
class MasteryIndicator extends StatelessWidget {
  final int level; // 0-5
  final double size;
  final bool showLabel;

  const MasteryIndicator({
    super.key,
    required this.level,
    this.size = 40,
    this.showLabel = false,
  });

  @override
  Widget build(BuildContext context) {
    final progress = level / 5;
    final color = _getLevelColor(level);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: size,
          height: size,
          child: Stack(
            alignment: Alignment.center,
            children: [
              CircularProgressIndicator(
                value: progress,
                strokeWidth: 4,
                backgroundColor: Colors.grey.withOpacity(0.3),
                valueColor: AlwaysStoppedAnimation<Color>(color),
              ),
              Text(
                '$level',
                style: TextStyle(
                  fontSize: size * 0.35,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
        ),
        if (showLabel) ...[
          const SizedBox(height: 4),
          Text(
            _getLevelLabel(level),
            style: TextStyle(
              fontSize: 10,
              color: color,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ],
    );
  }

  Color _getLevelColor(int level) {
    switch (level) {
      case 0: return Colors.grey;
      case 1: return Colors.red;
      case 2: return Colors.orange;
      case 3: return Colors.amber;
      case 4: return Colors.lightGreen;
      case 5: return Colors.green;
      default: return Colors.grey;
    }
  }

  String _getLevelLabel(int level) {
    switch (level) {
      case 0: return 'New';
      case 1: return 'Started';
      case 2: return 'Learning';
      case 3: return 'Practiced';
      case 4: return 'Proficient';
      case 5: return 'Mastered';
      default: return '';
    }
  }
}

/// Streak flame indicator
class StreakIndicator extends StatelessWidget {
  final int streak;
  final bool compact;

  const StreakIndicator({
    super.key,
    required this.streak,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = streak > 0 ? Colors.orange : Colors.grey;
    
    if (compact) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.local_fire_department, color: color, size: 16),
          const SizedBox(width: 2),
          Text(
            '$streak',
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ],
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.local_fire_department, color: color, size: 20),
          const SizedBox(width: 4),
          Text(
            '$streak day${streak == 1 ? '' : 's'}',
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

/// XP display with level
class XpDisplay extends StatelessWidget {
  final int xp;
  final bool showLevel;

  const XpDisplay({
    super.key,
    required this.xp,
    this.showLevel = true,
  });

  int get level => (xp / 500).floor() + 1;
  int get xpInCurrentLevel => xp % 500;
  int get xpToNextLevel => 500;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.purple.shade400, Colors.purple.shade700],
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showLevel) ...[
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: Text(
                '$level',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          const Icon(Icons.star, color: Colors.amber, size: 16),
          const SizedBox(width: 4),
          Text(
            '$xp XP',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

/// Progress summary card
class ProgressSummaryCard extends StatelessWidget {
  final LearningProgressState progress;

  const ProgressSummaryCard({
    super.key,
    required this.progress,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Theme.of(context).colorScheme.primary.withOpacity(0.1),
              Theme.of(context).colorScheme.secondary.withOpacity(0.1),
            ],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Your Progress',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                XpDisplay(xp: progress.xp),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _StatItem(
                  icon: Icons.check_circle,
                  value: '${progress.soundsMastered}',
                  label: 'Mastered',
                  color: Colors.green,
                ),
                _StatItem(
                  icon: Icons.play_circle,
                  value: '${progress.soundsPracticed}',
                  label: 'Practiced',
                  color: Colors.blue,
                ),
                _StatItem(
                  icon: Icons.access_time,
                  value: '${progress.totalPracticeTime}m',
                  label: 'Time',
                  color: Colors.purple,
                ),
                StreakIndicator(streak: progress.currentStreak),
              ],
            ),
            if (progress.soundsPracticed > 0) ...[
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: progress.overallAccuracy,
                  minHeight: 8,
                  backgroundColor: Colors.grey.withOpacity(0.2),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Overall Accuracy: ${(progress.overallAccuracy * 100).toStringAsFixed(0)}%',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color color;

  const _StatItem({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }
}
