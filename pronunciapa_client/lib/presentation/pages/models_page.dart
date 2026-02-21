import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/model_installer_provider.dart';
import '../widgets/app_background.dart';

/// Página de gestión de modelos
class ModelsPage extends ConsumerStatefulWidget {
  const ModelsPage({super.key});

  @override
  ConsumerState<ModelsPage> createState() => _ModelsPageState();
}

class _ModelsPageState extends ConsumerState<ModelsPage> {
  bool _isInstalling = false;
  String? _installingModelId;

  @override
  void initState() {
    super.initState();
    // Cargar estado al iniciar
    Future.microtask(() {
      ref.read(modelsStateProvider.notifier).loadStatus();
    });
  }

  @override
  Widget build(BuildContext context) {
    final modelsState = ref.watch(modelsStateProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Gestión de Modelos'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(modelsStateProvider.notifier).loadStatus();
            },
          ),
        ],
      ),
      body: AppBackground(
        child: modelsState.isLoading
            ? const Center(child: CircularProgressIndicator())
            : modelsState.error != null
                ? _buildErrorView(modelsState.error!)
                : _buildContent(modelsState),
      ),
      floatingActionButton: !modelsState.summary.ready
          ? FloatingActionButton.extended(
              onPressed: _isInstalling ? null : _runQuickSetup,
              icon: _isInstalling
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.rocket_launch),
              label: Text(_isInstalling ? 'Instalando...' : 'Setup Rápido'),
            )
          : null,
    );
  }

  Widget _buildErrorView(String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              'Error al cargar modelos',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              error,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () {
                ref.read(modelsStateProvider.notifier).loadStatus();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(ModelsState state) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSummaryCard(state.summary),
          const SizedBox(height: 24),
          if (!state.summary.ready) ...[
            _buildSetupActions(),
            const SizedBox(height: 24),
          ],
          ...state.modelsByCategory.entries.map((entry) {
            return _buildCategorySection(entry.key, entry.value);
          }),
        ],
      ),
    );
  }

  Widget _buildSummaryCard(ModelsSummary summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  summary.ready ? Icons.check_circle : Icons.warning,
                  color: summary.ready ? Colors.green : Colors.orange,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        summary.ready
                            ? 'Sistema Listo'
                            : 'Configuración Incompleta',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      Text(
                        '${summary.installed}/${summary.total} modelos instalados',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (summary.requiredMissing.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: Colors.orange),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Faltan modelos requeridos: ${summary.requiredMissing.join(", ")}',
                        style: const TextStyle(color: Colors.orange),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSetupActions() {
    return Card(
      color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '🚀 Configuración Rápida',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Instala los modelos necesarios para que la aplicación funcione correctamente.',
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                ElevatedButton.icon(
                  onPressed: _isInstalling ? null : _runQuickSetup,
                  icon: const Icon(Icons.flash_on),
                  label: const Text('Setup Rápido'),
                ),
                OutlinedButton.icon(
                  onPressed: _isInstalling ? null : _installRecommended,
                  icon: const Icon(Icons.star),
                  label: const Text('Instalar Recomendados'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCategorySection(String category, List<ModelInfo> models) {
    final categoryNames = {
      'asr': '🎤 Reconocimiento de Voz (ASR)',
      'textref': '📝 Texto a IPA (TextRef)',
      'llm': '🤖 Modelos de Lenguaje (LLM)',
      'tts': '🔊 Síntesis de Voz (TTS)',
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(
            categoryNames[category] ?? category.toUpperCase(),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
        ),
        ...models.map((model) => _buildModelCard(model)),
        const SizedBox(height: 8),
      ],
    );
  }

  Widget _buildModelCard(ModelInfo model) {
    final isInstalling = _installingModelId == model.id;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: _buildStatusIcon(model),
        title: Row(
          children: [
            Expanded(child: Text(model.name)),
            if (model.isRequired)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'Requerido',
                  style: TextStyle(fontSize: 10, color: Colors.red),
                ),
              ),
            if (model.isRecommended && !model.isRequired)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'Recomendado',
                  style: TextStyle(fontSize: 10, color: Colors.blue),
                ),
              ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(model.description),
            const SizedBox(height: 4),
            Text(
              '~${model.sizeMb} MB',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (model.hasError && model.error != null)
              Text(
                model.error!,
                style: const TextStyle(color: Colors.red, fontSize: 12),
              ),
          ],
        ),
        trailing: _buildActionButton(model, isInstalling),
        isThreeLine: true,
      ),
    );
  }

  Widget _buildStatusIcon(ModelInfo model) {
    if (model.isInstalled) {
      return const CircleAvatar(
        backgroundColor: Colors.green,
        child: Icon(Icons.check, color: Colors.white),
      );
    } else if (model.isInstalling) {
      return const CircleAvatar(
        child: SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      );
    } else if (model.hasError) {
      return const CircleAvatar(
        backgroundColor: Colors.red,
        child: Icon(Icons.error, color: Colors.white),
      );
    } else {
      return CircleAvatar(
        backgroundColor: Colors.grey.shade300,
        child: const Icon(Icons.download, color: Colors.grey),
      );
    }
  }

  Widget? _buildActionButton(ModelInfo model, bool isInstalling) {
    if (model.isInstalled) {
      return const Icon(Icons.check, color: Colors.green);
    }

    return TextButton(
      onPressed: isInstalling || _isInstalling
          ? null
          : () => _installModel(model.id),
      child: isInstalling
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Text('Instalar'),
    );
  }

  Future<void> _runQuickSetup() async {
    setState(() => _isInstalling = true);
    
    try {
      final success = await ref.read(modelsStateProvider.notifier).quickSetup();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              success
                  ? '✅ Setup completado correctamente'
                  : '⚠️ Setup completado con algunos errores',
            ),
            backgroundColor: success ? Colors.green : Colors.orange,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isInstalling = false);
      }
    }
  }

  Future<void> _installRecommended() async {
    setState(() => _isInstalling = true);
    
    try {
      await ref.read(modelsStateProvider.notifier).installRecommended();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Modelos recomendados instalados'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isInstalling = false);
      }
    }
  }

  Future<void> _installModel(String modelId) async {
    setState(() {
      _isInstalling = true;
      _installingModelId = modelId;
    });
    
    try {
      final success = await ref
          .read(modelsStateProvider.notifier)
          .installModel(modelId);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              success ? '✅ Modelo instalado' : '⚠️ Error al instalar',
            ),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isInstalling = false;
          _installingModelId = null;
        });
      }
    }
  }
}
