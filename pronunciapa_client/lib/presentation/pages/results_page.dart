import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';

/// Pantalla de resultados con diseño premium
class ResultsPage extends ConsumerWidget {
  final double score;
  final String targetIpa;
  final String observedIpa;
  final List<PhonemeResult> phonemes;
  final String? feedback;
  
  const ResultsPage({
    super.key,
    required this.score,
    required this.targetIpa,
    required this.observedIpa,
    required this.phonemes,
    this.feedback,
  });
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isGood = score >= 80;
    
    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('Resultados'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, kToolbarHeight + 24, 20, 20),
              child: Column(
                children: [
                  // Score Card
                  _buildScoreCard(context, isGood),
                  const SizedBox(height: 24),

                  // Phoneme Comparison
                  GlassCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Comparación Fonética',
                          style: theme.textTheme.titleLarge,
                        ),
                        const SizedBox(height: 16),

                        // Target
                        _buildPhonemeSection(
                          context,
                          label: 'Objetivo',
                          ipa: targetIpa,
                        ),
                        const SizedBox(height: 16),

                        // Observed
                        _buildPhonemeSection(
                          context,
                          label: 'Tu pronunciación',
                          ipa: observedIpa,
                        ),
                        const SizedBox(height: 24),

                        // Token by token comparison
                        Text(
                          'Detalle',
                          style: theme.textTheme.labelLarge?.copyWith(
                            color: theme.colorScheme.primary,
                          ),
                        ),
                        const SizedBox(height: 12),
                        _buildPhonemeTokens(),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Feedback Card
                  if (feedback != null) ...[
                    GlassCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                Icons.lightbulb_outline,
                                color: AppTheme.warning,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                'Sugerencias',
                                style: theme.textTheme.titleLarge,
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            feedback!,
                            style: theme.textTheme.bodyLarge,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],

                  // Action Buttons
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => Navigator.pop(context),
                          icon: const Icon(Icons.refresh),
                          label: const Text('Intentar de nuevo'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: GradientButton(
                          onPressed: () {
                            Navigator.pop(context);
                            // TODO: Navigate to next exercise
                          },
                          child: const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text('Siguiente', style: TextStyle(color: Colors.white)),
                              SizedBox(width: 8),
                              Icon(Icons.arrow_forward, color: Colors.white),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildScoreCard(BuildContext context, bool isGood) {
    final glass = Theme.of(context).extension<AppGlassTheme>();
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        gradient: isGood ? AppTheme.primaryGradient : AppTheme.accentGradient,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: glass?.glow ??
                (isGood ? AppTheme.primaryStart : AppTheme.accentStart)
                    .withOpacity(0.4),
            blurRadius: 30,
            offset: const Offset(0, 15),
          ),
        ],
      ),
      child: Column(
        children: [
          Icon(
            isGood ? Icons.celebration : Icons.trending_up,
            size: 48,
            color: Colors.white.withOpacity(0.9),
          ),
          const SizedBox(height: 16),
          Text(
            '${score.toStringAsFixed(0)}%',
            style: const TextStyle(
              fontSize: 64,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          Text(
            isGood ? '¡Excelente!' : 'Sigue practicando',
            style: TextStyle(
              fontSize: 18,
              color: Colors.white.withOpacity(0.9),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPhonemeSection(
    BuildContext context, {
    required String label,
    required String ipa,
  }) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.labelMedium?.copyWith(
            color: theme.textTheme.bodyMedium?.color?.withOpacity(0.6),
          ),
        ),
        const SizedBox(height: 4),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: Theme.of(context)
                    .extension<AppGlassTheme>()
                    ?.panel ??
                theme.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Theme.of(context)
                      .extension<AppGlassTheme>()
                      ?.border ??
                  theme.colorScheme.outlineVariant,
            ),
          ),
          child: Text(
            ipa,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 20,
              color: theme.colorScheme.onSurface,
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildPhonemeTokens() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: phonemes.map((p) {
        return PhonemeToken(
          phoneme: p.phoneme,
          operation: p.operation,
        );
      }).toList(),
    );
  }
}

/// Resultado de un fonema individual
class PhonemeResult {
  final String phoneme;
  final PhonemeOperation operation;
  
  const PhonemeResult({
    required this.phoneme,
    required this.operation,
  });
  
  factory PhonemeResult.fromJson(Map<String, dynamic> json) {
    final op = json['op'] as String? ?? 'correct';
    PhonemeOperation operation;
    switch (op) {
      case 'substitute':
      case 'sub':
        operation = PhonemeOperation.substitute;
        break;
      case 'insert':
      case 'ins':
        operation = PhonemeOperation.insert;
        break;
      case 'delete':
      case 'del':
        operation = PhonemeOperation.delete;
        break;
      default:
        operation = PhonemeOperation.correct;
    }
    return PhonemeResult(
      phoneme: json['phoneme'] as String? ?? json['ref'] as String? ?? '',
      operation: operation,
    );
  }
}
