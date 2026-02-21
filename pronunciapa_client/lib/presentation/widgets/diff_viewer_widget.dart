import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

enum DiffTag { match, substitution, deletion, insertion }

class DiffToken {
  final String text;
  final DiffTag tag;

  DiffToken(this.text, this.tag);
}

class DiffViewerWidget extends StatelessWidget {
  final List<DiffToken> tokens;

  const DiffViewerWidget({super.key, required this.tokens});

  @override
  Widget build(BuildContext context) {
    final glass = Theme.of(context).extension<AppGlassTheme>();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: glass?.panel ?? Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: glass?.border ?? Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 12,
        alignment: WrapAlignment.center,
        children: tokens.map((token) => _buildToken(context, token)).toList(),
      ),
    );
  }

  Widget _buildToken(BuildContext context, DiffToken token) {
    Color baseColor;
    IconData? icon;

    switch (token.tag) {
      case DiffTag.match:
        baseColor = AppTheme.success;
        break;
      case DiffTag.substitution:
        baseColor = AppTheme.warning;
        break;
      case DiffTag.deletion: // Expected but missing
        baseColor = AppTheme.error;
        icon = Icons.remove_circle_outline;
        break;
      case DiffTag.insertion: // Unexpected addition
        baseColor = AppTheme.info;
        icon = Icons.add_circle_outline;
        break;
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = baseColor.withOpacity(isDark ? 0.18 : 0.12);
    final textColor = baseColor;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: textColor.withOpacity(0.35),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            token.text,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 22,
              fontWeight: FontWeight.w600,
              color: textColor,
            ),
          ),
          if (icon != null) ...[
            const SizedBox(width: 4),
            Icon(icon, size: 14, color: textColor.withOpacity(0.7)),
          ]
        ],
      ),
    );
  }
}
