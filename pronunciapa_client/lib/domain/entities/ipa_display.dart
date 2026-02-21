/// Entidades de dominio para la visualización dual de IPA.
///
/// Corresponde a los modelos [IPADisplay] e [IPADisplayToken] del backend
/// (`ipa_server/models.py`).
///
/// Soporta:
/// - Nivel fonémico (`phonemic`) y fonético (`phonetic`).
/// - Modo técnico (IPA puro) y casual (transliteración coloquial).
/// - Tokens coloreados según distancia articulatoria.

// ---------------------------------------------------------------------------
// Color semántico de token
// ---------------------------------------------------------------------------

/// Color semántico de un token IPA según el resultado de la comparación.
enum TokenColor {
  /// Fonema correcto — pronunciación exacta.
  green,

  /// Fonema cercano — distancia articulatoria < 0.3 (sustitución válida).
  yellow,

  /// Error fonémico — distancia articulatoria ≥ 0.3 o inserción/borrado.
  red,

  /// Token fuera del inventario del pack (OOV).
  gray;

  /// Construir desde string de la API.
  static TokenColor fromString(String s) {
    switch (s.toLowerCase()) {
      case 'green':
        return TokenColor.green;
      case 'yellow':
        return TokenColor.yellow;
      case 'red':
        return TokenColor.red;
      case 'gray':
        return TokenColor.gray;
      default:
        return TokenColor.gray;
    }
  }
}

// ---------------------------------------------------------------------------
// Modo de display
// ---------------------------------------------------------------------------

/// Modo de visualización seleccionado por el aprendiz.
enum DisplayMode {
  /// IPA puro — para perfil técnico / avanzado.
  technical,

  /// Transliteración coloquial — para perfil principiante / casual.
  casual;

  static DisplayMode fromString(String s) =>
      s == 'casual' ? DisplayMode.casual : DisplayMode.technical;

  String toApiString() => name;
}

// ---------------------------------------------------------------------------
// Nivel de representación
// ---------------------------------------------------------------------------

/// Nivel de evaluación fonológica.
enum RepresentationLevel {
  /// Nivel fonémico — representación abstracta /p/, /t/, …
  phonemic,

  /// Nivel fonético — alófonos concretos [β], [ð], …
  phonetic;

  static RepresentationLevel fromString(String s) =>
      s == 'phonetic' ? RepresentationLevel.phonetic : RepresentationLevel.phonemic;
}

// ---------------------------------------------------------------------------
// IPADisplayToken
// ---------------------------------------------------------------------------

/// Un token IPA individual con color semántico y transliteración coloquial.
class IPADisplayToken {
  /// Símbolo IPA canónico (modo técnico).
  final String ipa;

  /// Transliteración coloquial legible (modo casual).
  final String casual;

  /// Color semántico del token.
  final TokenColor color;

  /// Operación de edición: `eq`, `sub`, `ins`, `del`.
  final String op;

  /// Token de referencia (IPA objetivo). Null para inserciones.
  final String? ref;

  /// Token observado (IPA hipótesis). Null para borrados.
  final String? hyp;

  /// Distancia articulatoria [0, 1]. Null si no aplica.
  final double? articulatoryDistance;

  /// Nivel de representación de este token.
  final RepresentationLevel level;

  const IPADisplayToken({
    required this.ipa,
    required this.casual,
    required this.color,
    required this.op,
    this.ref,
    this.hyp,
    this.articulatoryDistance,
    this.level = RepresentationLevel.phonemic,
  });

  factory IPADisplayToken.fromJson(Map<String, dynamic> json) {
    return IPADisplayToken(
      ipa: json['ipa'] as String? ?? '',
      casual: json['casual'] as String? ?? '',
      color: TokenColor.fromString(json['color'] as String? ?? 'gray'),
      op: json['op'] as String? ?? 'eq',
      ref: json['ref'] as String?,
      hyp: json['hyp'] as String?,
      articulatoryDistance: (json['articulatory_distance'] as num?)?.toDouble(),
      level: RepresentationLevel.fromString(json['level'] as String? ?? 'phonemic'),
    );
  }

  /// Texto a mostrar según el [mode] activo.
  String displayText(DisplayMode mode) =>
      mode == DisplayMode.casual ? casual : ipa;

  /// True si este token fue pronunciado correctamente.
  bool get isCorrect => color == TokenColor.green;

  /// True si fue un error significativo.
  bool get isError => color == TokenColor.red;
}

// ---------------------------------------------------------------------------
// IPADisplay
// ---------------------------------------------------------------------------

/// Resultado completo de la visualización dual de IPA.
///
/// Contiene todos los tokens coloreados y las cadenas completas en ambos
/// modos (técnico y casual) para la referencia y la hipótesis.
class IPADisplay {
  /// Modo de display activo.
  final DisplayMode mode;

  /// Nivel de representación.
  final RepresentationLevel level;

  /// IPA objetivo completo en modo técnico.
  final String refTechnical;

  /// IPA objetivo en transliteración coloquial.
  final String refCasual;

  /// IPA observado completo en modo técnico.
  final String hypTechnical;

  /// IPA observado en transliteración coloquial.
  final String hypCasual;

  /// Color global del score: green ≥ 80, yellow 50-79, red < 50.
  final TokenColor scoreColor;

  /// Leyenda de colores para mostrar al aprendiz.
  final Map<String, String> legend;

  /// Tokens individuales con color y transliteración.
  final List<IPADisplayToken> tokens;

  const IPADisplay({
    required this.mode,
    required this.level,
    required this.refTechnical,
    required this.refCasual,
    required this.hypTechnical,
    required this.hypCasual,
    required this.scoreColor,
    required this.legend,
    required this.tokens,
  });

  factory IPADisplay.fromJson(Map<String, dynamic> json) {
    final rawTokens = json['tokens'] as List<dynamic>? ?? [];
    return IPADisplay(
      mode: DisplayMode.fromString(json['mode'] as String? ?? 'technical'),
      level: RepresentationLevel.fromString(json['level'] as String? ?? 'phonemic'),
      refTechnical: json['ref_technical'] as String? ?? '',
      refCasual: json['ref_casual'] as String? ?? '',
      hypTechnical: json['hyp_technical'] as String? ?? '',
      hypCasual: json['hyp_casual'] as String? ?? '',
      scoreColor: TokenColor.fromString(json['score_color'] as String? ?? 'green'),
      legend: Map<String, String>.from(json['legend'] as Map? ?? {}),
      tokens: rawTokens
          .whereType<Map<String, dynamic>>()
          .map(IPADisplayToken.fromJson)
          .toList(),
    );
  }

  /// Texto de referencia según el [mode] activo.
  String get refText => mode == DisplayMode.casual ? refCasual : refTechnical;

  /// Texto observado según el [mode] activo.
  String get hypText => mode == DisplayMode.casual ? hypCasual : hypTechnical;

  /// Crear copia con modo cambiado.
  IPADisplay withMode(DisplayMode newMode) => IPADisplay(
        mode: newMode,
        level: level,
        refTechnical: refTechnical,
        refCasual: refCasual,
        hypTechnical: hypTechnical,
        hypCasual: hypCasual,
        scoreColor: scoreColor,
        legend: legend,
        tokens: tokens,
      );

  /// Estadísticas rápidas de tokens.
  int get correctCount => tokens.where((t) => t.isCorrect).length;
  int get errorCount => tokens.where((t) => t.isError).length;
  int get totalCount => tokens.length;
}
