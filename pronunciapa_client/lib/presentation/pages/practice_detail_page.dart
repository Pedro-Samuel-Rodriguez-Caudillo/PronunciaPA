import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import '../providers/repository_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';
import '../widgets/diff_viewer_widget.dart';
import '../widgets/feedback_level_selector.dart';

/// Practice detail page for a specific IPA sound
class PracticeDetailPage extends ConsumerStatefulWidget {
  final String ipaSound;
  final List<String> examples;
  final String description;
  final String lang;

  const PracticeDetailPage({
    super.key,
    required this.ipaSound,
    required this.examples,
    required this.description,
    required this.lang,
  });

  @override
  ConsumerState<PracticeDetailPage> createState() => _PracticeDetailPageState();
}

class _PracticeDetailPageState extends ConsumerState<PracticeDetailPage> {
  final _recorder = AudioRecorder();
  bool _isRecording = false;
  bool _isProcessing = false;
  String? _recordedFilePath;
  String _selectedExample = '';
  FeedbackLevel _feedbackLevel = FeedbackLevel.casual;

  @override
  void initState() {
    super.initState();
    if (widget.examples.isNotEmpty) {
      _selectedExample = widget.examples.first;
    }
  }

  @override
  void dispose() {
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _startRecording() async {
    if (await _recorder.hasPermission()) {
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/ipa_practice_${DateTime.now().millisecondsSinceEpoch}.wav';

      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        ),
        path: path,
      );

      setState(() {
        _isRecording = true;
        _recordedFilePath = path;
      });
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Permiso de micrófono denegado'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _stopRecording() async {
    final path = await _recorder.stop();
    setState(() {
      _isRecording = false;
      _recordedFilePath = path;
    });
  }

  Future<void> _compareRecording() async {
    if (_recordedFilePath == null || _selectedExample.isEmpty) return;

    setState(() {
      _isProcessing = true;
    });

    try {
      final repository = ref.read(pronunciationRepositoryProvider);
      final result = await repository.compare(
        _recordedFilePath!,
        _selectedExample,
        evaluationLevel: 'phonemic', // Default to phonemic for practice
        mode: 'objective', // Default to objective mode
        lang: widget.lang,
      );

      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Resultado'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Score display
                  if (result.score != null)
                    Text(
                      'Puntuación: ${result.score!.toStringAsFixed(1)}%',
                      style: TextStyle(
                        color: _getScoreColor(result.score! / 100),
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                  const SizedBox(height: 12),
                  
                  // IPA comparison - Target vs Detected
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.check_circle, color: Colors.green, size: 16),
                            const SizedBox(width: 8),
                            const Text('Objetivo: ', style: TextStyle(fontWeight: FontWeight.bold)),
                            Expanded(
                              child: Text(
                                result.targetIpa ?? _selectedExample,
                                style: const TextStyle(fontFamily: 'monospace', fontSize: 16),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Icon(Icons.mic, color: Colors.blue, size: 16),
                            const SizedBox(width: 8),
                            const Text('Detectado: ', style: TextStyle(fontWeight: FontWeight.bold)),
                            Expanded(
                              child: Text(
                                result.ipa,
                                style: const TextStyle(fontFamily: 'monospace', fontSize: 16),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  
                  // Use DiffViewerWidget with ops
                  if (result.ops != null && result.ops!.isNotEmpty) ...[
                    const Text(
                      'Análisis detallado:',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    DiffViewerWidget(
                      tokens: result.ops!.map((op) {
                        DiffTag tag;
                        switch (op.op) {
                          case 'eq':
                            tag = DiffTag.match;
                            break;
                          case 'sub':
                            tag = DiffTag.substitution;
                            break;
                          case 'del':
                            tag = DiffTag.deletion;
                            break;
                          case 'ins':
                            tag = DiffTag.insertion;
                            break;
                          default:
                            tag = DiffTag.match;
                        }
                        return DiffToken(op.hyp ?? op.ref ?? '', tag);
                      }).toList(),
                    ),
                  ] else if (result.alignment != null && result.alignment!.isNotEmpty) ...[
                    // Fallback to alignment display
                    const Text(
                      'Alineamiento:',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    ...result.alignment!.map((pair) {
                      final ref = pair[0] ?? '-';
                      final hyp = pair[1] ?? '-';
                      final match = ref == hyp;
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Row(
                          children: [
                            Text(ref, style: const TextStyle(fontFamily: 'monospace')),
                            const SizedBox(width: 8),
                            Icon(
                              match ? Icons.check : Icons.close,
                              color: match ? Colors.green : Colors.red,
                              size: 16,
                            ),
                            const SizedBox(width: 8),
                            Text(hyp, style: const TextStyle(fontFamily: 'monospace')),
                          ],
                        ),
                      );
                    }),
                  ] else ...[
                    // No ops or alignment - show warning
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.orange.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.orange.withOpacity(0.3)),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.warning_amber, color: Colors.orange, size: 20),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'No se pudo analizar el audio en detalle. Intenta hablar más claro o cerca del micrófono.',
                              style: TextStyle(fontSize: 12, color: Colors.orange),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cerrar'),
              ),
              ElevatedButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  _startRecording();
                },
                child: const Text('Practicar de nuevo'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }

  Color _getScoreColor(double score) {
    if (score >= 0.9) return Colors.green;
    if (score >= 0.7) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: Text('Practicar [${widget.ipaSound}]'),
        centerTitle: true,
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // IPA Sound display
                  GlassCard(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      children: [
                        Text(
                          widget.ipaSound,
                          style: TextStyle(
                            fontSize: 72,
                            fontWeight: FontWeight.bold,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          widget.description,
                          style: const TextStyle(fontSize: 16),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Feedback level selector
                  GlassCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Nivel de explicaciones:',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 12),
                        FeedbackLevelSelector(
                          currentLevel: _feedbackLevel,
                          onLevelChanged: (level) {
                            setState(() {
                              _feedbackLevel = level;
                            });
                          },
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 24),

                  // Example selector
                  GlassCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Selecciona un ejemplo para practicar:',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 12),
                        ...widget.examples.map((example) {
                          final isSelected = example == _selectedExample;
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 8.0),
                            child: InkWell(
                              onTap: () {
                                setState(() {
                                  _selectedExample = example;
                                });
                              },
                              borderRadius: BorderRadius.circular(8),
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                                decoration: BoxDecoration(
                                  color: isSelected
                                      ? Theme.of(context).colorScheme.primary.withOpacity(0.2)
                                      : Colors.transparent,
                                  border: Border.all(
                                    color: isSelected
                                        ? Theme.of(context).colorScheme.primary
                                        : Colors.grey.withOpacity(0.3),
                                  ),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Row(
                                  children: [
                                    Icon(
                                      isSelected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                                      color: isSelected ? Theme.of(context).colorScheme.primary : Colors.grey,
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Text(
                                        example,
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          );
                        }),
                      ],
                    ),
                  ),

                  const Spacer(),

                  // Recording controls
                  GlassCard(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      children: [
                        if (_isRecording)
                          const Column(
                            children: [
                              Icon(Icons.mic, size: 48, color: Colors.red),
                              SizedBox(height: 8),
                              Text(
                                '🔴 Grabando...',
                                style: TextStyle(
                                  color: Colors.red,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 16,
                                ),
                              ),
                            ],
                          )
                        else
                          const Icon(Icons.mic_none, size: 48, color: Colors.grey),
                        
                        const SizedBox(height: 24),

                        if (!_isRecording && _recordedFilePath == null)
                          ElevatedButton.icon(
                            onPressed: _startRecording,
                            icon: const Icon(Icons.mic),
                            label: const Text('Grabar'),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                              textStyle: const TextStyle(fontSize: 18),
                            ),
                          ),

                        if (_isRecording)
                          ElevatedButton.icon(
                            onPressed: _stopRecording,
                            icon: const Icon(Icons.stop),
                            label: const Text('Detener'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                              textStyle: const TextStyle(fontSize: 18),
                            ),
                          ),

                        if (!_isRecording && _recordedFilePath != null)
                          Column(
                            children: [
                              const Text(
                                '✓ Audio grabado',
                                style: TextStyle(color: Colors.green, fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 16),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  ElevatedButton.icon(
                                    onPressed: _isProcessing ? null : _compareRecording,
                                    icon: _isProcessing
                                        ? const SizedBox(
                                            width: 16,
                                            height: 16,
                                            child: CircularProgressIndicator(strokeWidth: 2),
                                          )
                                        : const Icon(Icons.compare),
                                    label: const Text('Comparar'),
                                    style: ElevatedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  OutlinedButton.icon(
                                    onPressed: _startRecording,
                                    icon: const Icon(Icons.refresh),
                                    label: const Text('Volver a grabar'),
                                    style: OutlinedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
