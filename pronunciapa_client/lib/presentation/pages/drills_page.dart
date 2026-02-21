import 'package:flutter/material.dart';
import '../../domain/entities/feedback_result.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';

/// Page to display pronunciation drills and exercises
class DrillsPage extends StatelessWidget {
  final List<FeedbackDrill> drills;
  final String targetIpa;
  final String observedIpa;
  final String summary;

  const DrillsPage({
    super.key,
    required this.drills,
    required this.targetIpa,
    required this.observedIpa,
    required this.summary,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('Ejercicios de Práctica'),
        centerTitle: true,
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Summary card
                  GlassCard(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.lightbulb_outline,
                              color: Theme.of(context).colorScheme.primary,
                              size: 28,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'Resumen',
                                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          summary,
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const Divider(height: 32),
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Objetivo',
                                    style: Theme.of(context).textTheme.labelSmall,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    targetIpa,
                                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.success,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Tu pronunciación',
                                    style: Theme.of(context).textTheme.labelSmall,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    observedIpa,
                                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.warning,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Drills header
                  Text(
                    'Ejercicios Recomendados',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    'Practica estos ejemplos para mejorar',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Drills list
                  if (drills.isEmpty)
                    GlassCard(
                      padding: const EdgeInsets.all(20),
                      child: Center(
                        child: Column(
                          children: [
                            Icon(
                              Icons.check_circle_outline,
                              size: 48,
                              color: AppTheme.success,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              '¡Excelente pronunciación!',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'No hay ejercicios adicionales necesarios.',
                              style: Theme.of(context).textTheme.bodyMedium,
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    ...drills.asMap().entries.map((entry) {
                      final index = entry.key;
                      final drill = entry.value;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: _buildDrillCard(context, index + 1, drill),
                      );
                    }),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDrillCard(BuildContext context, int number, FeedbackDrill drill) {
    IconData icon;
    Color iconColor;

    switch (drill.type.toLowerCase()) {
      case 'minimal_pair':
        icon = Icons.compare_arrows;
        iconColor = AppTheme.info;
        break;
      case 'repetition':
        icon = Icons.repeat;
        iconColor = AppTheme.warning;
        break;
      case 'listening':
        icon = Icons.hearing;
        iconColor = AppTheme.success;
        break;
      case 'articulation':
        icon = Icons.record_voice_over;
        iconColor = AppTheme.primaryStart;
        break;
      default:
        icon = Icons.school;
        iconColor = Theme.of(context).colorScheme.primary;
    }

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: iconColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: Text(
                    '$number',
                    style: TextStyle(
                      color: iconColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(icon, size: 20, color: iconColor),
                        const SizedBox(width: 8),
                        Text(
                          _getDrillTypeLabel(drill.type),
                          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: iconColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            drill.text,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }

  String _getDrillTypeLabel(String type) {
    switch (type.toLowerCase()) {
      case 'minimal_pair':
        return 'Par Mínimo';
      case 'repetition':
        return 'Repetición';
      case 'listening':
        return 'Escucha';
      case 'articulation':
        return 'Articulación';
      default:
        return 'Ejercicio';
    }
  }
}
