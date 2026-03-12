import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import '../widgets/recorder_widget.dart';
import '../providers/api_provider.dart';
import '../providers/preferences_provider.dart';
import '../../domain/entities/ipa_cli.dart';
import 'settings_page.dart';
import 'results_page.dart';
import 'ipa_practice_page.dart';
import 'ipa_learn_page.dart';
import 'models_page.dart';
import 'progress_roadmap_page.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final TextEditingController _textController = TextEditingController();
  final TextEditingController _targetIpaController = TextEditingController();
  IpaCliPayload? _ipaPayload;

  @override
  void dispose() {
    _textController.dispose();
    _targetIpaController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final apiState = ref.watch(apiNotifierProvider);
    final theme = Theme.of(context);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('PronunciaPA'),
        actions: [
          IconButton(
            icon: const Icon(Icons.school),
            onPressed: () {
               Navigator.of(context).push(
                 MaterialPageRoute(builder: (_) => const IpaLearnPage()),
               );
            },
            tooltip: 'Learn IPA',
          ),
          IconButton(
            icon: const Icon(Icons.psychology),
            onPressed: () {
               Navigator.of(context).push(
                 MaterialPageRoute(builder: (_) => const IpaPracticePage()),
               );
            },
            tooltip: 'Práctica IPA',
          ),
          IconButton(
            icon: const Icon(Icons.show_chart),
            onPressed: () {
               Navigator.of(context).push(
                 MaterialPageRoute(builder: (_) => const ProgressRoadmapPage()),
               );
            },
            tooltip: 'Mi progreso',
          ),
          IconButton(
            icon: const Icon(Icons.extension),
            onPressed: () {
               Navigator.of(context).push(
                 MaterialPageRoute(builder: (_) => const ModelsPage()),
               );
            },
            tooltip: 'Gestión de Modelos',
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
               Navigator.of(context).push(
                 MaterialPageRoute(builder: (_) => const SettingsPage()),
               );
            },
          )
        ],
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, kToolbarHeight + 24, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _buildTargetCard(theme),
                  const SizedBox(height: 24),

                  // Recorders & Actions
                  Center(
                    child: RecorderWidget(
                      referenceText: _textController.text.isNotEmpty
                          ? _textController.text
                          : null,
                      targetIpa: _targetIpaController.text.isNotEmpty
                          ? _targetIpaController.text
                          : null,
                    ),
                  ),

                  const SizedBox(height: 32),

                  // Results Section
                  if (apiState.isLoading)
                    const Center(
                      child: Padding(
                        padding: EdgeInsets.symmetric(vertical: 32),
                        child: CircularProgressIndicator(),
                      ),
                    )
                  else if (apiState.error != null)
                    _buildErrorCard(theme, apiState.error!)
                  else if (apiState.result != null)
                    _buildResultTrigger(context, apiState.result!),
                ],
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showIpaImportDialog(context),
        tooltip: 'Import Practice Set',
        child: const Icon(Icons.upload_file),
      ),
    );
  }

  Widget _buildResultTrigger(BuildContext context, TranscriptionResult result) {
    final theme = Theme.of(context);
    final apiState = ref.watch(apiNotifierProvider);
    final score = result.score ?? 0.0;
    final isGood = score > 80;

    return Padding(
      padding: const EdgeInsets.only(top: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Quick score preview
          GlassCard(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  isGood ? Icons.check_circle : Icons.warning_amber,
                  size: 40,
                  color: isGood ? AppTheme.success : AppTheme.warning,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${score.toStringAsFixed(0)}% Match',
                        style: theme.textTheme.headlineSmall?.copyWith(
                          color: isGood ? AppTheme.success : AppTheme.warning,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (apiState.isQuickResult)
                        Text(
                          'Revisión rápida',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                    ],
                  ),
                ),
                if (result.ipa.isNotEmpty)
                  Chip(
                    label: Text(
                      result.ipa.length > 20
                          ? '${result.ipa.substring(0, 20)}…'
                          : result.ipa,
                      style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          GradientButton(
            onPressed: () async {
              if (apiState.isQuickResult) {
                // Re-run with full analysis, then navigate
                final notifier = ref.read(apiNotifierProvider.notifier);
                final prefs = ref.read(preferencesProvider);
                await notifier.reprocessFull(
                  lang: prefs.langTarget,
                  langSource: prefs.langSource,
                  langTarget: prefs.langTarget,
                  targetIpa: _targetIpaController.text.trim().isEmpty
                      ? null
                      : _targetIpaController.text.trim(),
                  evaluationLevel: prefs.mode.name,
                  mode: prefs.comparisonMode,
                  forcePhonetic: prefs.forcePhonetic,
                  allowQualityDowngrade: prefs.allowQualityDowngrade,
                );
                if (!context.mounted) {
                  return;
                }
                final updatedState = ref.read(apiNotifierProvider);
                if (updatedState.result != null) {
                  _navigateToResults(context, updatedState.result!);
                }
              } else {
                _navigateToResults(context, result);
              }
            },
            gradient: AppTheme.coolGradient,
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.insights, color: Colors.white),
                SizedBox(width: 8),
                Text(
                  'Ver análisis detallado',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _navigateToResults(BuildContext context, TranscriptionResult result) {
    // Convertir ops a PhonemeResult si existe
    List<PhonemeResult> phonemes = [];
    if (result.ops != null) {
      for (var op in result.ops!) {
        PhonemeOperation operation;
        String phoneme;
        
        switch (op.op) {
          case 'eq':
            operation = PhonemeOperation.correct;
            phoneme = op.hyp ?? op.ref ?? '';
            break;
          case 'sub':
            operation = PhonemeOperation.substitute;
            phoneme = op.hyp ?? ''; // Mostramos lo que dijo el usuario
            break;
          case 'del':
            operation = PhonemeOperation.delete;
            phoneme = op.ref ?? '';
            break;
          case 'ins':
            operation = PhonemeOperation.insert;
            phoneme = op.hyp ?? '';
            break;
          default:
            operation = PhonemeOperation.correct;
            phoneme = op.hyp ?? op.ref ?? '';
        }
        
        phonemes.add(PhonemeResult(phoneme: phoneme, operation: operation));
      }
    }

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ResultsPage(
          score: result.score ?? 0.0, // Backend now returns 0-100
          targetIpa: result.targetIpa ?? result.meta?['target_ipa'] ?? '',
          observedIpa: result.ipa,
          phonemes: phonemes,
          feedbackPayload: result.meta?['feedback'] != null
              ? FeedbackPayload.fromJson(
                  Map<String, dynamic>.from(result.meta!['feedback'] as Map))
              : null,
        ),
      ),
    );
  }

  Widget _buildTargetCard(ThemeData theme) {
    final prefs = ref.watch(preferencesProvider);
    final prefsNotifier = ref.read(preferencesProvider.notifier);

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Lengua hablada y lengua objetivo',
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: prefs.langSource,
                  decoration: const InputDecoration(
                    labelText: 'Hablo',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: availableLanguages.map((lang) {
                    final tempPrefs = UserPreferences(lang: lang);
                    return DropdownMenuItem(
                      value: lang,
                      child: Text('${tempPrefs.langFlag} ${tempPrefs.langDisplayName}'),
                    );
                  }).toList(),
                  onChanged: (value) {
                    if (value != null) {
                      prefsNotifier.setLangSource(value);
                    }
                  },
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: prefs.langTarget,
                  decoration: const InputDecoration(
                    labelText: 'Quiero hablar',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: availableLanguages.map((lang) {
                    final tempPrefs = UserPreferences(lang: lang);
                    return DropdownMenuItem(
                      value: lang,
                      child: Text('${tempPrefs.langFlag} ${tempPrefs.langDisplayName}'),
                    );
                  }).toList(),
                  onChanged: (value) {
                    if (value != null) {
                      prefsNotifier.setLangTarget(value);
                    }
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Frase objetivo',
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _textController,
            style: theme.textTheme.headlineSmall,
            decoration: InputDecoration(
              hintText: 'Escribe lo que vas a decir...',
              hintStyle: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            maxLines: null,
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          Text(
            'IPA objetivo (opcional, manual)',
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _targetIpaController,
            style: theme.textTheme.titleMedium?.copyWith(fontFamily: 'monospace'),
            decoration: InputDecoration(
              hintText: 'Ej: h o l a',
              helperText: 'Si lo completas, se usara como IPA objetivo en la comparación.',
              hintStyle: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            maxLines: null,
            onChanged: (_) => setState(() {}),
          ),
          if (_ipaPayload != null) ...[
            const Divider(height: 32),
            _buildPayloadInfo(theme),
          ]
        ],
      ),
    );
  }

  Widget _buildPayloadInfo(ThemeData theme) {
    final examples = _ipaPayload is IpaPracticeSetPayload
        ? (_ipaPayload as IpaPracticeSetPayload).items
        : const <IpaExample>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text("Suggestions:", style: theme.textTheme.labelLarge),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: examples.take(5).map((ex) {
            return ActionChip(
              label: Text(ex.text ?? 'Unknown'),
              onPressed: () {
                if (ex.text != null) {
                  _textController.text = ex.text!;
                  setState(() {});
                }
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildErrorCard(ThemeData theme, String error) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: theme.colorScheme.error),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              error,
              style: TextStyle(color: theme.colorScheme.error),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showIpaImportDialog(BuildContext context) async {
    final controller = TextEditingController();
    final result = await showDialog<String?>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Import Practice Set'),
        content: TextField(
          controller: controller,
          maxLines: 5,
          decoration: const InputDecoration(
            hintText: 'Paste JSON from CLI...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () async {
              final data = await Clipboard.getData('text/plain');
              if (data?.text != null) {
                controller.text = data!.text!;
              }
            },
            child: const Text('Paste'),
          ),
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, controller.text),
              child: const Text('Import')),
        ],
      ),
    );
    if (!context.mounted) {
      return;
    }

    if (result != null && result.isNotEmpty) {
      try {
        final payload = parseIpaCliPayload(result);
        setState(() => _ipaPayload = payload);
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Invalid JSON: $e")),
        );
      }
    }
  }
}
