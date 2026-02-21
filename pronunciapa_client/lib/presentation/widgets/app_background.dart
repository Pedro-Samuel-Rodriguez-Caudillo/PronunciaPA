import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class AppBackground extends StatelessWidget {
  final Widget? child;

  const AppBackground({super.key, this.child});

  @override
  Widget build(BuildContext context) {
    final glass = Theme.of(context).extension<AppGlassTheme>();
    final baseColor = Theme.of(context).scaffoldBackgroundColor;
    final gradient = glass?.auroraGradient ?? AppTheme.darkAuroraGradient;

    return Stack(
      children: [
        IgnorePointer(
          child: Stack(
            children: [
              Positioned.fill(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: baseColor,
                    gradient: gradient,
                  ),
                ),
              ),
              Positioned(
                top: -120,
                left: -80,
                child: _GlowBlob(
                  size: 280,
                  color: AppTheme.primaryStart.withOpacity(0.35),
                ),
              ),
              Positioned(
                top: 140,
                right: -120,
                child: _GlowBlob(
                  size: 240,
                  color: AppTheme.accentStart.withOpacity(0.25),
                ),
              ),
              Positioned(
                bottom: -140,
                right: -80,
                child: _GlowBlob(
                  size: 320,
                  color: AppTheme.coolStart.withOpacity(0.25),
                ),
              ),
            ],
          ),
        ),
        if (child != null) child!,
      ],
    );
  }
}

class _GlowBlob extends StatelessWidget {
  final double size;
  final Color color;

  const _GlowBlob({
    required this.size,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            color,
            color.withOpacity(0.0),
          ],
          stops: const [0.0, 0.75],
        ),
      ),
    );
  }
}
