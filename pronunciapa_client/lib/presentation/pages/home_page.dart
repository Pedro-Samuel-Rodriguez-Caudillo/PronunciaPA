import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import '../widgets/recorder_widget.dart';
import '../widgets/ipa_display_widget.dart';
import '../widgets/diff_viewer_widget.dart';
import '../providers/api_provider.dart';
import '../../domain/entities/ipa_cli.dart';
import 'settings_page.dart';
import 'results_page.dart';
import '../theme/app_theme.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final TextEditingController _textController = TextEditingController();
  IpaCliPayload? _ipaPayload;

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final apiState = ref.watch(apiNotifierProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('PronunciaPA'),
        actions: [
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
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
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
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showIpaImportDialog(context),
        child: const Icon(Icons.upload_file),
        tooltip: 'Import Practice Set',
      ),
    );
  }

  Widget _buildResultTrigger(BuildContext context, TranscriptionResult result) {
    // Si hay resultado, mostramos un botón para ver los detalles o navegamos automáticamente
    // Para simplificar, mostramos el botón de resultados aquí.
    return Padding(
      padding: const EdgeInsets.only(top: 24),
      child: ElevatedButton.icon(
        onPressed: () => _navigateToResults(context, result),
        icon: const Icon(Icons.insights),
        label: const Text('Ver Análisis Detallado'),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 16),
          backgroundColor: Theme.of(context).colorScheme.primaryContainer,
          foregroundColor: Theme.of(context).colorScheme.onPrimaryContainer,
        ),
      ),
    );
  }

  void _navigateToResults(BuildContext context, TranscriptionResult result) {
    // Convertir alignment a PhonemeResult si existe
    List<PhonemeResult> phonemes = [];
    if (result.alignment != null) {
      for (var item in (result.alignment as List)) {
        if (item is List && item.length >= 2) {
          final ref = item[0]?.toString();
          final hyp = item[1]?.toString();
          
          PhonemeOperation op;
          String phoneme;
          
          if (ref == hyp) {
            op = PhonemeOperation.correct;
            phoneme = ref ?? '';
          } else if (ref == null) {
            op = PhonemeOperation.insert;
            phoneme = hyp ?? '';
          } else if (hyp == null) {
            op = PhonemeOperation.delete;
            phoneme = ref ?? '';
          } else {
            op = PhonemeOperation.substitute;
            phoneme = hyp ?? ''; // Mostramos lo que dijo el usuario
          }
          
          phonemes.add(PhonemeResult(phoneme: phoneme, operation: op));
        }
      }
    }

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ResultsPage(
          score: result.score != null ? (1.0 - result.score!) * 100 : 0.0,
          targetIpa: result.meta?['target_ipa'] ?? '',
          observedIpa: result.ipa,
          phonemes: phonemes,
          feedback: result.meta?['feedback']?['summary'],
        ),
      ),
    );
  }

  Widget _buildTargetCard(ThemeData theme) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "Target Phrase",
              style: theme.textTheme.labelMedium?.copyWith(
                color: theme.colorScheme.primary,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _textController,
              style: theme.textTheme.headlineSmall,
              decoration: const InputDecoration(
                hintText: 'Type what to say...',
                border: InputBorder.none,
                hintStyle: TextStyle(color: Colors.black26),
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
    return Card(
      color: theme.colorScheme.errorContainer,
      child: Padding(
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
      ),
    );
  }

  Widget _buildResultCard(ThemeData theme, TranscriptionResult result) {
    final score = result.score != null ? ((1 - result.score!) * 100) : 0.0;
    final isGood = score > 80;

    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Result", style: theme.textTheme.titleMedium),
                    if (result.score != null)
                      Text(
                        "${score.toStringAsFixed(0)}% Match",
                        style: theme.textTheme.headlineMedium?.copyWith(
                          color: isGood ? Colors.green : Colors.orange,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                  ],
                ),
                Icon(
                  isGood ? Icons.check_circle : Icons.warning_amber,
                  size: 48,
                  color: isGood ? Colors.green.shade300 : Colors.orange.shade300,
                ),
              ],
            ),
            const SizedBox(height: 24),
            Text("Phonetic Breakdown", style: theme.textTheme.labelLarge),
            const SizedBox(height: 12),
            
            if (result.alignment != null)
              DiffViewerWidget(
                tokens: (result.alignment as List).map((item) {
                  final text = item[0].toString();
                  final tagStr = item[1].toString();
                  DiffTag tag;
                  if (tagStr == 'correct' || tagStr == 'match') {
                    tag = DiffTag.match;
                  } else if (tagStr == 'substitute') {
                    tag = DiffTag.substitution;
                  } else if (tagStr == 'delete') {
                    tag = DiffTag.deletion;
                  } else {
                    tag = DiffTag.insertion;
                  }
                  return DiffToken(text, tag);
                }).toList(),
              )
            else
               IpaDisplayWidget(label: "Raw IPA", ipa: result.ipa),
          ],
        ),
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

    if (result != null && result.isNotEmpty) {
      try {
        final payload = parseIpaCliPayload(result);
        setState(() => _ipaPayload = payload);
      } catch (e) {
        if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text("Invalid JSON: $e")),
            );
        }
      }
    }
  }
}
