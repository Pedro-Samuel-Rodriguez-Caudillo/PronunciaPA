import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

@immutable
class AppGlassTheme extends ThemeExtension<AppGlassTheme> {
  final Color surface;
  final Color surfaceStrong;
  final Color panel;
  final Color border;
  final Color borderStrong;
  final Color shadow;
  final Color glow;
  final Color chipSurface;
  final Color chipBorder;
  final Color chipText;
  final Gradient auroraGradient;
  final Gradient primaryGradient;
  final Gradient accentGradient;
  final Gradient coolGradient;
  final double blurSigma;

  const AppGlassTheme({
    required this.surface,
    required this.surfaceStrong,
    required this.panel,
    required this.border,
    required this.borderStrong,
    required this.shadow,
    required this.glow,
    required this.chipSurface,
    required this.chipBorder,
    required this.chipText,
    required this.auroraGradient,
    required this.primaryGradient,
    required this.accentGradient,
    required this.coolGradient,
    required this.blurSigma,
  });

  @override
  AppGlassTheme copyWith({
    Color? surface,
    Color? surfaceStrong,
    Color? panel,
    Color? border,
    Color? borderStrong,
    Color? shadow,
    Color? glow,
    Color? chipSurface,
    Color? chipBorder,
    Color? chipText,
    Gradient? auroraGradient,
    Gradient? primaryGradient,
    Gradient? accentGradient,
    Gradient? coolGradient,
    double? blurSigma,
  }) {
    return AppGlassTheme(
      surface: surface ?? this.surface,
      surfaceStrong: surfaceStrong ?? this.surfaceStrong,
      panel: panel ?? this.panel,
      border: border ?? this.border,
      borderStrong: borderStrong ?? this.borderStrong,
      shadow: shadow ?? this.shadow,
      glow: glow ?? this.glow,
      chipSurface: chipSurface ?? this.chipSurface,
      chipBorder: chipBorder ?? this.chipBorder,
      chipText: chipText ?? this.chipText,
      auroraGradient: auroraGradient ?? this.auroraGradient,
      primaryGradient: primaryGradient ?? this.primaryGradient,
      accentGradient: accentGradient ?? this.accentGradient,
      coolGradient: coolGradient ?? this.coolGradient,
      blurSigma: blurSigma ?? this.blurSigma,
    );
  }

  @override
  AppGlassTheme lerp(ThemeExtension<AppGlassTheme>? other, double t) {
    if (other is! AppGlassTheme) {
      return this;
    }

    return AppGlassTheme(
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceStrong: Color.lerp(surfaceStrong, other.surfaceStrong, t)!,
      panel: Color.lerp(panel, other.panel, t)!,
      border: Color.lerp(border, other.border, t)!,
      borderStrong: Color.lerp(borderStrong, other.borderStrong, t)!,
      shadow: Color.lerp(shadow, other.shadow, t)!,
      glow: Color.lerp(glow, other.glow, t)!,
      chipSurface: Color.lerp(chipSurface, other.chipSurface, t)!,
      chipBorder: Color.lerp(chipBorder, other.chipBorder, t)!,
      chipText: Color.lerp(chipText, other.chipText, t)!,
      auroraGradient: Gradient.lerp(auroraGradient, other.auroraGradient, t)!,
      primaryGradient: Gradient.lerp(primaryGradient, other.primaryGradient, t)!,
      accentGradient: Gradient.lerp(accentGradient, other.accentGradient, t)!,
      coolGradient: Gradient.lerp(coolGradient, other.coolGradient, t)!,
      blurSigma: lerpDouble(blurSigma, other.blurSigma, t)!,
    );
  }
}

/// Tema Premium de PronunciaPA
class AppTheme {
  static const Color primaryStart = Color(0xFF6C7CFF);
  static const Color primaryEnd = Color(0xFF7A4CF2);

  static const Color accentStart = Color(0xFFF093FB);
  static const Color accentEnd = Color(0xFFF5576C);

  static const Color coolStart = Color(0xFF00C9FF);
  static const Color coolEnd = Color(0xFF92FE9D);

  static const Color success = Color(0xFF10B981);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFEF4444);
  static const Color info = Color(0xFF3B82F6);

  static const Color darkBg = Color(0xFF0B0F1A);
  static const Color darkSurface = Color(0xFF12162A);
  static const Color darkSurfaceHigh = Color(0xFF1A1F36);

  static const Color lightBg = Color(0xFFF4F6FF);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceHigh = Color(0xFFE9EEFF);

  static const Color darkTextPrimary = Color(0xFFF2F4FF);
  static const Color darkTextSecondary = Color(0xFFA3ABC7);
  static const Color darkTextMuted = Color(0xFF7E87A9);

  static const Color lightTextPrimary = Color(0xFF1A1E2E);
  static const Color lightTextSecondary = Color(0xFF4B516A);
  static const Color lightTextMuted = Color(0xFF7A8096);

  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primaryStart, primaryEnd],
  );

  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [accentStart, accentEnd],
  );

  static const LinearGradient coolGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [coolStart, coolEnd],
  );

  static const LinearGradient darkAuroraGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0B0F1A),
      Color(0xFF121A33),
      Color(0xFF0B0F1A),
    ],
    stops: [0.0, 0.5, 1.0],
  );

  static const LinearGradient lightAuroraGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFFF7F8FF),
      Color(0xFFEEF2FF),
      Color(0xFFF8FAFF),
    ],
    stops: [0.0, 0.5, 1.0],
  );

  static const AppGlassTheme darkGlass = AppGlassTheme(
    surface: Color(0x0FFFFFFF),
    surfaceStrong: Color(0x1AFFFFFF),
    panel: Color(0x14FFFFFF),
    border: Color(0x1FFFFFFF),
    borderStrong: Color(0x33FFFFFF),
    shadow: Color(0x66060B19),
    glow: Color(0x4D6C7CFF),
    chipSurface: Color(0x1AFFFFFF),
    chipBorder: Color(0x33FFFFFF),
    chipText: darkTextPrimary,
    auroraGradient: darkAuroraGradient,
    primaryGradient: primaryGradient,
    accentGradient: accentGradient,
    coolGradient: coolGradient,
    blurSigma: 18,
  );

  static const AppGlassTheme lightGlass = AppGlassTheme(
    surface: Color(0xCCFFFFFF),
    surfaceStrong: Color(0xE6FFFFFF),
    panel: Color(0xF2FFFFFF),
    border: Color(0x14000000),
    borderStrong: Color(0x22000000),
    shadow: Color(0x1A0B1020),
    glow: Color(0x336C7CFF),
    chipSurface: Color(0xF2FFFFFF),
    chipBorder: Color(0x22000000),
    chipText: lightTextPrimary,
    auroraGradient: lightAuroraGradient,
    primaryGradient: primaryGradient,
    accentGradient: accentGradient,
    coolGradient: coolGradient,
    blurSigma: 14,
  );

  static ThemeData get dark => _buildTheme(Brightness.dark);
  static ThemeData get light => _buildTheme(Brightness.light);

  static ThemeData _buildTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final glass = isDark ? darkGlass : lightGlass;
    final textTheme = _buildTextTheme(brightness);

    final scheme = ColorScheme.fromSeed(
      seedColor: primaryStart,
      brightness: brightness,
      surface: isDark ? darkSurface : lightSurface,
      background: isDark ? darkBg : lightBg,
    ).copyWith(
      secondary: coolStart,
      tertiary: accentStart,
      onSurface: isDark ? darkTextPrimary : lightTextPrimary,
      onSurfaceVariant: isDark ? darkTextSecondary : lightTextSecondary,
      surfaceContainerHighest: isDark ? darkSurfaceHigh : lightSurfaceHigh,
      surfaceContainerHigh: isDark ? const Color(0xFF151A30) : const Color(0xFFEFF2FF),
      surfaceContainer: isDark ? const Color(0xFF13172B) : const Color(0xFFF4F6FF),
      surfaceContainerLow: isDark ? const Color(0xFF101425) : const Color(0xFFF8FAFF),
      surfaceContainerLowest: isDark ? const Color(0xFF0C111E) : const Color(0xFFFFFFFF),
      outline: isDark ? const Color(0x33FFFFFF) : const Color(0x22000000),
      outlineVariant: isDark ? const Color(0x1FFFFFFF) : const Color(0x14000000),
      shadow: glass.shadow,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: isDark ? darkBg : lightBg,
      fontFamily: GoogleFonts.manrope().fontFamily,
      textTheme: textTheme,
      extensions: <ThemeExtension<dynamic>>[glass],
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          color: scheme.onSurface,
          fontWeight: FontWeight.w600,
        ),
        iconTheme: IconThemeData(color: scheme.onSurface),
      ),
      cardTheme: CardTheme(
        color: glass.surface,
        elevation: 0,
        shadowColor: glass.shadow,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: glass.border),
        ),
      ),
      dividerTheme: DividerThemeData(color: glass.border),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: glass.surfaceStrong,
        hintStyle: TextStyle(color: isDark ? darkTextMuted : lightTextMuted),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: glass.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: glass.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: primaryStart, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          elevation: 0,
          backgroundColor: primaryStart,
          foregroundColor: Colors.white,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          backgroundColor: primaryStart,
          foregroundColor: Colors.white,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          side: BorderSide(color: glass.borderStrong),
          foregroundColor: scheme.onSurface,
        ),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: ButtonStyle(
          backgroundColor: MaterialStateProperty.resolveWith<Color?>((states) {
            if (states.contains(MaterialState.selected)) {
              return scheme.primary;
            }
            return glass.surface;
          }),
          foregroundColor: MaterialStateProperty.resolveWith<Color?>((states) {
            if (states.contains(MaterialState.selected)) {
              return scheme.onPrimary;
            }
            return scheme.onSurfaceVariant;
          }),
          side: MaterialStateProperty.all(BorderSide(color: glass.border)),
          shape: MaterialStateProperty.all(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: MaterialStateProperty.resolveWith<Color?>((states) {
          if (states.contains(MaterialState.selected)) {
            return scheme.primary;
          }
          return scheme.surfaceContainerHighest;
        }),
        trackColor: MaterialStateProperty.resolveWith<Color?>((states) {
          if (states.contains(MaterialState.selected)) {
            return scheme.primary.withOpacity(0.35);
          }
          return glass.surfaceStrong;
        }),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: glass.chipSurface,
        selectedColor: scheme.primary.withOpacity(0.2),
        labelStyle: (textTheme.labelMedium ?? const TextStyle())
            .copyWith(color: scheme.onSurface),
        secondaryLabelStyle: (textTheme.labelMedium ?? const TextStyle())
            .copyWith(color: scheme.onSurface),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: BorderSide(color: glass.chipBorder),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: scheme.primary,
        foregroundColor: Colors.white,
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      dialogTheme: DialogTheme(
        backgroundColor: glass.surfaceStrong,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: isDark ? const Color(0xFF1D233A) : const Color(0xFFF0F2FF),
        contentTextStyle: textTheme.bodyMedium?.copyWith(color: scheme.onSurface),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  static TextTheme _buildTextTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final base = isDark ? ThemeData.dark().textTheme : ThemeData.light().textTheme;
    final textTheme = GoogleFonts.manropeTextTheme(base);
    final primary = isDark ? darkTextPrimary : lightTextPrimary;
    final secondary = isDark ? darkTextSecondary : lightTextSecondary;
    final muted = isDark ? darkTextMuted : lightTextMuted;

    return textTheme.copyWith(
      displayLarge: GoogleFonts.sora(
        fontSize: 48,
        fontWeight: FontWeight.w700,
        color: primary,
      ),
      displayMedium: GoogleFonts.sora(
        fontSize: 36,
        fontWeight: FontWeight.w700,
        color: primary,
      ),
      headlineLarge: GoogleFonts.sora(
        fontSize: 28,
        fontWeight: FontWeight.w600,
        color: primary,
      ),
      headlineMedium: GoogleFonts.sora(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        color: primary,
      ),
      titleLarge: GoogleFonts.sora(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: primary,
      ),
      titleMedium: GoogleFonts.sora(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: primary,
      ),
      titleSmall: GoogleFonts.sora(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: primary,
      ),
      bodyLarge: textTheme.bodyLarge?.copyWith(
        color: secondary,
        height: 1.5,
      ),
      bodyMedium: textTheme.bodyMedium?.copyWith(
        color: secondary,
        height: 1.5,
      ),
      bodySmall: textTheme.bodySmall?.copyWith(
        color: muted,
        height: 1.4,
      ),
      labelLarge: textTheme.labelLarge?.copyWith(
        color: primary,
        fontWeight: FontWeight.w600,
      ),
      labelMedium: textTheme.labelMedium?.copyWith(
        color: secondary,
      ),
      labelSmall: textTheme.labelSmall?.copyWith(
        color: muted,
      ),
    );
  }
}

/// Boton con gradiente
class GradientButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final Widget child;
  final LinearGradient gradient;
  final double borderRadius;

  const GradientButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.gradient = AppTheme.primaryGradient,
    this.borderRadius = 12,
  });

  @override
  Widget build(BuildContext context) {
    final glass = Theme.of(context).extension<AppGlassTheme>();

    return Container(
      decoration: BoxDecoration(
        gradient: onPressed != null ? gradient : null,
        color: onPressed == null ? Colors.grey : null,
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: onPressed != null
            ? [
                BoxShadow(
                  color: glass?.glow ?? AppTheme.primaryStart.withOpacity(0.4),
                  blurRadius: 24,
                  offset: const Offset(0, 12),
                ),
              ]
            : null,
      ),
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.transparent,
          shadowColor: Colors.transparent,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(borderRadius),
          ),
        ),
        child: child,
      ),
    );
  }
}

/// Tarjeta con efecto glassmorphism
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  final double borderRadius;

  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.borderRadius = 16,
  });

  @override
  Widget build(BuildContext context) {
    final glass = Theme.of(context).extension<AppGlassTheme>();
    final scheme = Theme.of(context).colorScheme;

    final surface = glass?.surface ?? scheme.surface.withOpacity(0.2);
    final border = glass?.border ?? scheme.outlineVariant;
    final shadow = glass?.shadow ?? Colors.black.withOpacity(0.2);
    final blurSigma = glass?.blurSigma ?? 16;

    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: surface,
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(color: border),
            boxShadow: [
              BoxShadow(
                color: shadow,
                blurRadius: 24,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}

class PhonemeToken extends StatelessWidget {
  final String phoneme;
  final PhonemeOperation operation;

  const PhonemeToken({
    super.key,
    required this.phoneme,
    this.operation = PhonemeOperation.correct,
  });

  Color _baseColor() {
    switch (operation) {
      case PhonemeOperation.correct:
        return AppTheme.success;
      case PhonemeOperation.substitute:
        return AppTheme.warning;
      case PhonemeOperation.insert:
        return AppTheme.info;
      case PhonemeOperation.delete:
        return AppTheme.error;
    }
  }

  @override
  Widget build(BuildContext context) {
    final base = _baseColor();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: base.withOpacity(isDark ? 0.2 : 0.14),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: base.withOpacity(0.45)),
      ),
      child: Text(
        phoneme,
        style: GoogleFonts.jetBrainsMono(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: base,
          decoration:
              operation == PhonemeOperation.delete ? TextDecoration.lineThrough : null,
        ),
      ),
    );
  }
}

enum PhonemeOperation {
  correct,
  substitute,
  insert,
  delete,
}
