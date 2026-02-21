import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Transcription mode: phonemic or phonetic
enum TranscriptionMode {
  phonemic, // /.../
  phonetic, // [...]
}

/// Widget for selecting transcription mode
class ModeSelectorWidget extends StatelessWidget {
  final TranscriptionMode currentMode;
  final ValueChanged<TranscriptionMode> onModeChanged;

  const ModeSelectorWidget({
    super.key,
    required this.currentMode,
    required this.onModeChanged,
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
          _buildModeButton(
            context,
            mode: TranscriptionMode.phonemic,
            label: '/fonémico/',
            isActive: currentMode == TranscriptionMode.phonemic,
          ),
          const SizedBox(width: 4),
          _buildModeButton(
            context,
            mode: TranscriptionMode.phonetic,
            label: '[fonético]',
            isActive: currentMode == TranscriptionMode.phonetic,
          ),
        ],
      ),
    );
  }

  Widget _buildModeButton(
    BuildContext context, {
    required TranscriptionMode mode,
    required String label,
    required bool isActive,
  }) {
    final theme = Theme.of(context);

    return GestureDetector(
      onTap: () => onModeChanged(mode),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
        decoration: BoxDecoration(
          gradient: isActive ? AppTheme.primaryGradient : null,
          color: isActive ? null : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          boxShadow: isActive
              ? [
                  BoxShadow(
                    color: AppTheme.primaryStart.withOpacity(0.35),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  )
                ]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isActive
                ? Colors.white
                : theme.colorScheme.onSurfaceVariant,
            fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}
