import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

class IpaDisplayWidget extends StatelessWidget {
  final String ipa;
  final String label;

  const IpaDisplayWidget({
    super.key,
    required this.ipa,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final glass = theme.extension<AppGlassTheme>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.labelLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
        ),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: glass?.panel ?? theme.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: glass?.border ?? theme.colorScheme.outlineVariant,
            ),
          ),
          child: Text(
            ipa.isEmpty ? '...' : ipa,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 24,
              letterSpacing: 1.2,
              color: theme.colorScheme.onSurface,
            ),
          ),
        ),
      ],
    );
  }
}
