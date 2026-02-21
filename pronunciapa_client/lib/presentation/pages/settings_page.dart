import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/preferences_provider.dart';
import '../providers/game_stats_provider.dart';
import '../providers/repository_provider.dart';
import '../widgets/mode_selector_widget.dart';
import '../widgets/game_stats_widget.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';

/// Settings page with all user preferences
class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefs = ref.watch(preferencesProvider);
    final prefsNotifier = ref.read(preferencesProvider.notifier);
    final stats = ref.watch(gameStatsProvider);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('Configuración'),
        centerTitle: true,
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, kToolbarHeight + 16, 16, 16),
              children: [
                // Language Section
                _buildSectionHeader(context, '🌍 Idioma'),
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Idioma de práctica'),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        value: prefs.lang,
                        decoration: const InputDecoration(
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                        items: availableLanguages.map((lang) {
                          final tempPrefs = UserPreferences(lang: lang);
                          return DropdownMenuItem(
                            value: lang,
                            child:
                                Text('${tempPrefs.langFlag} ${tempPrefs.langDisplayName}'),
                          );
                        }).toList(),
                        onChanged: (value) {
                          if (value != null) {
                            prefsNotifier.setLang(value);
                          }
                        },
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Transcription Mode Section
                _buildSectionHeader(context, '📝 Modo de Transcripción'),
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ModeSelectorWidget(
                        currentMode: prefs.mode,
                        onModeChanged: prefsNotifier.setMode,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        prefs.mode == TranscriptionMode.phonemic
                            ? 'Modo fonémico (/.../) muestra sonidos distintivos del idioma.'
                            : 'Modo fonético ([...]) muestra detalles precisos de articulación.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Comparison Mode Section
                _buildSectionHeader(context, '🎯 Modo de comparación'),
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SegmentedButton<String>(
                        segments: const [
                          ButtonSegment(
                            value: 'casual',
                            label: Text('Casual'),
                          ),
                          ButtonSegment(
                            value: 'objective',
                            label: Text('Objetivo'),
                          ),
                          ButtonSegment(
                            value: 'phonetic',
                            label: Text('IPA general'),
                          ),
                        ],
                        selected: {prefs.comparisonMode},
                        onSelectionChanged: (values) {
                          prefsNotifier.setComparisonMode(values.first);
                        },
                      ),
                      const SizedBox(height: 12),
                      Text(
                        prefs.comparisonMode == 'casual'
                            ? 'Comparacion permisiva para practica diaria.'
                            : prefs.comparisonMode == 'objective'
                                ? 'Balance entre precision y consistencia.'
                                : 'IPA general para practicar sonidos en contexto. Sin pack puede tener baja confiabilidad.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Feedback Level Section
                _buildSectionHeader(context, '💬 Nivel de Feedback'),
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SegmentedButton<String>(
                        segments: const [
                          ButtonSegment(
                            value: 'casual',
                            label: Text('Básico'),
                            icon: Icon(Icons.sentiment_satisfied),
                          ),
                          ButtonSegment(
                            value: 'precise',
                            label: Text('Avanzado'),
                            icon: Icon(Icons.school),
                          ),
                        ],
                        selected: {prefs.feedbackLevel},
                        onSelectionChanged: (values) {
                          prefsNotifier.setFeedbackLevel(values.first);
                        },
                      ),
                      const SizedBox(height: 12),
                      Text(
                        prefs.feedbackLevel == 'casual'
                            ? 'Explicaciones sencillas y directas para principiantes.'
                            : 'Explicaciones técnicas y detalladas para usuarios avanzados.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Appearance Section
                _buildSectionHeader(context, '🎨 Apariencia'),
                GlassCard(
                  padding: EdgeInsets.zero,
                  child: Column(
                    children: [
                      SwitchListTile(
                        title: const Text('Modo oscuro'),
                        subtitle: const Text('Activar tema oscuro'),
                        value: prefs.darkMode,
                        onChanged: prefsNotifier.setDarkMode,
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Feedback Options Section
                _buildSectionHeader(context, '📳 Feedback'),
                GlassCard(
                  padding: EdgeInsets.zero,
                  child: Column(
                    children: [
                      SwitchListTile(
                        title: const Text('Vibración'),
                        subtitle: const Text('Vibrar al grabar/detener'),
                        value: prefs.hapticFeedback,
                        onChanged: prefsNotifier.setHapticFeedback,
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: const Text('Sonidos'),
                        subtitle: const Text('Reproducir sonidos de confirmación'),
                        value: prefs.audioFeedback,
                        onChanged: prefsNotifier.setAudioFeedback,
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Stats Section
                _buildSectionHeader(context, '📊 Estadísticas'),
                GameStatsWidget(stats: stats),

                const SizedBox(height: 24),

                // API URL Section
                _buildSectionHeader(context, '🔗 Servidor API'),
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: _buildApiUrlSection(context, ref),
                ),

                const SizedBox(height: 24),

                // About Section
                _buildSectionHeader(context, 'ℹ️ Acerca de'),
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'PronunciaPA',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Versión 1.0.0',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Practica tu pronunciación en cualquier idioma con feedback en tiempo real.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      OutlinedButton(
                        onPressed: () => _showResetDialog(context, ref),
                        child: const Text('Reiniciar estadísticas'),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 32),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.primary,
            ),
      ),
    );
  }

  Future<void> _showResetDialog(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('¿Reiniciar estadísticas?'),
        content: const Text(
          'Esta acción eliminará todo tu progreso, incluyendo nivel, XP, racha y logros. Esta acción no se puede deshacer.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Reiniciar'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      ref.read(gameStatsProvider.notifier).reset();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Estadísticas reiniciadas')),
        );
      }
    }
  }

  Widget _buildApiUrlSection(BuildContext context, WidgetRef ref) {
    final currentUrl = ref.watch(baseUrlProvider);
    final urlController = TextEditingController(text: currentUrl);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'URL del servidor backend',
          style: TextStyle(fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: urlController,
          decoration: const InputDecoration(
            hintText: 'http://10.0.2.2:8000',
            prefixIcon: Icon(Icons.link),
            border: OutlineInputBorder(),
            isDense: true,
          ),
          keyboardType: TextInputType.url,
          onSubmitted: (value) async {
            try {
              await ref.read(baseUrlProvider.notifier).setUrl(value);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('URL guardada correctamente'),
                    backgroundColor: Colors.green,
                  ),
                );
              }
            } catch (e) {
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('Error: ${e.toString()}'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            }
          },
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () async {
                  try {
                    await ref.read(baseUrlProvider.notifier).setUrl(urlController.text);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('URL guardada'),
                          backgroundColor: Colors.green,
                        ),
                      );
                    }
                  } catch (e) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Error: ${e.toString()}'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  }
                },
                icon: const Icon(Icons.save, size: 18),
                label: const Text('Guardar'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () async {
                  await ref.read(baseUrlProvider.notifier).resetToDefault();
                  urlController.text = ref.read(baseUrlProvider);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('URL restaurada')),
                    );
                  }
                },
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Por Defecto'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.blue.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Actual: $currentUrl',
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Emulador Android: 10.0.2.2:8000\nDispositivo físico: IP de tu PC',
                style: TextStyle(fontSize: 11),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
