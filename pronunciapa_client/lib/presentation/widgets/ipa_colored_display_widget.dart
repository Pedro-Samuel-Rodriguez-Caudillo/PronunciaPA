/// Widget de visualización dual de IPA con tokens coloreados.
///
/// Muestra cada fonema con su color semántico (verde/amarillo/rojo/gris)
/// y permite alternar entre modo técnico (IPA puro) y casual (transliteración).
///
/// Soporta nivel fonémico y fonético de forma transparente.
library;

import 'package:flutter/material.dart';
import '../../domain/entities/ipa_display.dart';

// ---------------------------------------------------------------------------
// Colores de tema
// ---------------------------------------------------------------------------

/// Mapeo de [TokenColor] a colores de Flutter.
extension TokenColorExt on TokenColor {
  Color toFlutterColor({double opacity = 1.0}) {
    switch (this) {
      case TokenColor.green:
        return Color.fromRGBO(34, 197, 94, opacity);   // Tailwind green-500
      case TokenColor.yellow:
        return Color.fromRGBO(234, 179, 8, opacity);   // Tailwind yellow-500
      case TokenColor.red:
        return Color.fromRGBO(239, 68, 68, opacity);   // Tailwind red-500
      case TokenColor.gray:
        return Color.fromRGBO(156, 163, 175, opacity); // Tailwind gray-400
    }
  }

  Color get background => toFlutterColor(opacity: 0.15);
  Color get foreground => toFlutterColor(opacity: 1.0);

  /// Icono de feedback accesible.
  IconData get icon {
    switch (this) {
      case TokenColor.green:
        return Icons.check_circle_outline;
      case TokenColor.yellow:
        return Icons.warning_amber_outlined;
      case TokenColor.red:
        return Icons.cancel_outlined;
      case TokenColor.gray:
        return Icons.help_outline;
    }
  }
}

// ---------------------------------------------------------------------------
// Widget principal
// ---------------------------------------------------------------------------

/// Visualización dual IPA con toggle técnico/casual y tokens coloreados.
///
/// Ejemplo de uso:
/// ```dart
/// IPAColoredDisplayWidget(
///   display: ipaDisplay,
///   onModeChanged: (newMode) => setState(() => _mode = newMode),
/// )
/// ```
class IPAColoredDisplayWidget extends StatefulWidget {
  /// Datos de visualización del backend.
  final IPADisplay display;

  /// Callback cuando el usuario cambia de modo técnico ↔ casual.
  final ValueChanged<DisplayMode>? onModeChanged;

  /// Si mostrar la leyenda de colores.
  final bool showLegend;

  /// Si mostrar la distancia articulatoria en el tooltip del token.
  final bool showArticulatoryDistance;

  const IPAColoredDisplayWidget({
    super.key,
    required this.display,
    this.onModeChanged,
    this.showLegend = true,
    this.showArticulatoryDistance = false,
  });

  @override
  State<IPAColoredDisplayWidget> createState() => _IPAColoredDisplayWidgetState();
}

class _IPAColoredDisplayWidgetState extends State<IPAColoredDisplayWidget> {
  late DisplayMode _currentMode;

  @override
  void initState() {
    super.initState();
    _currentMode = widget.display.mode;
  }

  @override
  void didUpdateWidget(IPAColoredDisplayWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.display.mode != widget.display.mode) {
      _currentMode = widget.display.mode;
    }
  }

  void _toggleMode() {
    final newMode = _currentMode == DisplayMode.technical
        ? DisplayMode.casual
        : DisplayMode.technical;
    setState(() => _currentMode = newMode);
    widget.onModeChanged?.call(newMode);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final display = widget.display;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Header con toggle ──────────────────────────────────────────
        _buildHeader(theme),
        const SizedBox(height: 12),

        // ── Línea de referencia (objetivo) ────────────────────────────
        _buildLabel(theme, 'Objetivo'),
        const SizedBox(height: 4),
        _buildRefRow(display),
        const SizedBox(height: 12),

        // ── Tokens coloreados (comparación) ───────────────────────────
        _buildLabel(theme, 'Tu pronunciación'),
        const SizedBox(height: 8),
        _buildTokensRow(display.tokens),

        // ── Leyenda ───────────────────────────────────────────────────
        if (widget.showLegend) ...[
          const SizedBox(height: 16),
          _buildLegend(theme, display.legend),
        ],
      ],
    );
  }

  // ------------------------------------------------------------------
  // Header
  // ------------------------------------------------------------------

  Widget _buildHeader(ThemeData theme) {
    return Row(
      children: [
        // Nivel fonémico / fonético
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: theme.colorScheme.secondaryContainer,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            widget.display.level == RepresentationLevel.phonetic
                ? 'Fonético'
                : 'Fonémico',
            style: theme.textTheme.labelSmall?.copyWith(
              color: theme.colorScheme.onSecondaryContainer,
            ),
          ),
        ),
        const Spacer(),
        // Toggle técnico / casual
        _ModeToggle(
          currentMode: _currentMode,
          onToggle: _toggleMode,
        ),
      ],
    );
  }

  // ------------------------------------------------------------------
  // Línea de referencia
  // ------------------------------------------------------------------

  Widget _buildRefRow(IPADisplay display) {
    final refText = _currentMode == DisplayMode.casual
        ? display.refCasual
        : display.refTechnical;
    return Text(
      refText,
      style: const TextStyle(
        fontFamily: 'monospace',
        fontSize: 16,
        color: Colors.blueGrey,
      ),
    );
  }

  // ------------------------------------------------------------------
  // Tokens coloreados
  // ------------------------------------------------------------------

  Widget _buildTokensRow(List<IPADisplayToken> tokens) {
    if (tokens.isEmpty) {
      return const Text('—', style: TextStyle(color: Colors.grey));
    }
    return Wrap(
      spacing: 6,
      runSpacing: 8,
      children: tokens.map((t) => _IPATokenChip(
        token: t,
        mode: _currentMode,
        showDistance: widget.showArticulatoryDistance,
      )).toList(),
    );
  }

  // ------------------------------------------------------------------
  // Leyenda
  // ------------------------------------------------------------------

  Widget _buildLabel(ThemeData theme, String text) {
    return Text(
      text,
      style: theme.textTheme.labelSmall?.copyWith(
        color: theme.colorScheme.onSurfaceVariant,
        fontWeight: FontWeight.w600,
      ),
    );
  }

  Widget _buildLegend(ThemeData theme, Map<String, String> legend) {
    return Wrap(
      spacing: 12,
      runSpacing: 6,
      children: TokenColor.values.map((c) {
        final text = legend[c.name] ?? c.name;
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: c.foreground,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              text,
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        );
      }).toList(),
    );
  }
}

// ---------------------------------------------------------------------------
// Token chip individual
// ---------------------------------------------------------------------------

class _IPATokenChip extends StatelessWidget {
  final IPADisplayToken token;
  final DisplayMode mode;
  final bool showDistance;

  const _IPATokenChip({
    required this.token,
    required this.mode,
    required this.showDistance,
  });

  @override
  Widget build(BuildContext context) {
    final text = token.displayText(mode);
    final chip = Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: token.color.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: token.color.foreground.withOpacity(0.5),
          width: 1,
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            text,
            style: TextStyle(
              fontFamily: 'monospace',
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: token.color.foreground,
            ),
          ),
          // Mostrar referencia debajo para sustituciones
          if (token.op == 'sub' && token.ref != null && token.ref != text)
            Text(
              mode == DisplayMode.casual
                  ? _ipaToDisplay(token.ref!)
                  : token.ref!,
              style: TextStyle(
                fontFamily: 'monospace',
                fontSize: 10,
                color: Colors.grey.shade500,
                decoration: TextDecoration.lineThrough,
              ),
            ),
        ],
      ),
    );

    // Tooltip con distancia articulatoria
    if (showDistance && token.articulatoryDistance != null) {
      return Tooltip(
        message: 'Distancia: ${token.articulatoryDistance!.toStringAsFixed(2)}',
        child: chip,
      );
    }
    return chip;
  }

  /// Placeholder — en producción usar la misma tabla _CASUAL_MAP del backend.
  String _ipaToDisplay(String ipa) => ipa;
}

// ---------------------------------------------------------------------------
// Toggle modo técnico / casual
// ---------------------------------------------------------------------------

class _ModeToggle extends StatelessWidget {
  final DisplayMode currentMode;
  final VoidCallback onToggle;

  const _ModeToggle({required this.currentMode, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isTechnical = currentMode == DisplayMode.technical;

    return GestureDetector(
      onTap: onToggle,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _ToggleOption(
              label: 'IPA',
              icon: Icons.science_outlined,
              isActive: isTechnical,
              theme: theme,
            ),
            _ToggleOption(
              label: 'ABC',
              icon: Icons.translate,
              isActive: !isTechnical,
              theme: theme,
            ),
          ],
        ),
      ),
    );
  }
}

class _ToggleOption extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isActive;
  final ThemeData theme;

  const _ToggleOption({
    required this.label,
    required this.icon,
    required this.isActive,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: isActive ? theme.colorScheme.primary : Colors.transparent,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: isActive
                ? theme.colorScheme.onPrimary
                : theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: isActive
                  ? theme.colorScheme.onPrimary
                  : theme.colorScheme.onSurfaceVariant,
              fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ],
      ),
    );
  }
}
