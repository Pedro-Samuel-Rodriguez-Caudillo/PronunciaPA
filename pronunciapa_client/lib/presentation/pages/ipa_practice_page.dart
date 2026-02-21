import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/ipa_practice_provider.dart';
import '../providers/preferences_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';
import '../widgets/audio_player_button.dart';
import 'practice_detail_page.dart';

// Language display names
const Map<String, String> languageNames = {
  'es': 'Español',
  'en': 'English',
  'fr': 'Français',
  'de': 'Deutsch',
  'it': 'Italiano',
  'pt': 'Português',
};

/// IPA Practice page - shows list of IPA sounds to practice
class IpaPracticePage extends ConsumerWidget {
  const IpaPracticePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final practiceState = ref.watch(ipaPracticeProvider);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('Práctica IPA'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(ipaPracticeProvider.notifier).retry();
            },
            tooltip: 'Recargar',
          ),
        ],
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: Column(
              children: [
                // Language selector
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: GlassCard(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    child: Row(
                      children: [
                        const Icon(Icons.language, size: 20),
                        const SizedBox(width: 12),
                        const Text(
                          'Idioma:',
                          style: TextStyle(fontWeight: FontWeight.w500),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: practiceState.selectedLang,
                            decoration: const InputDecoration(
                              isDense: true,
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                            items: availableLanguages.map((lang) {
                              final name = languageNames[lang] ?? lang;
                              return DropdownMenuItem(
                                value: lang,
                                child: Text(name),
                              );
                            }).toList(),
                            onChanged: (value) {
                              if (value != null) {
                                ref.read(ipaPracticeProvider.notifier).setLanguage(value);
                              }
                            },
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // Content area
                Expanded(
                  child: _buildContent(context, ref, practiceState),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, IpaPracticeState state) {
    if (state.isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Cargando sonidos IPA...'),
          ],
        ),
      );
    }

    if (state.error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: Colors.red),
              const SizedBox(height: 16),
              Text(
                state.error!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () {
                  ref.read(ipaPracticeProvider.notifier).retry();
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Reintentar'),
              ),
            ],
          ),
        ),
      );
    }

    if (state.sounds.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.info_outline, size: 64, color: Colors.blue),
              const SizedBox(height: 16),
              Text(
                'No hay sonidos IPA disponibles para ${languageNames[state.selectedLang] ?? state.selectedLang}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 8),
              const Text(
                'Intenta seleccionar otro idioma',
                style: TextStyle(fontSize: 14, color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: state.sounds.length,
      itemBuilder: (context, index) {
        final sound = state.sounds[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: 12.0),
          child: GlassCard(
            padding: EdgeInsets.zero,
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              leading: CircleAvatar(
                backgroundColor: Theme.of(context).colorScheme.primary,
                child: Text(
                  sound.ipa,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
              title: Text(
                sound.description,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              subtitle: Text(
                'Ejemplos: ${sound.examples}',
                style: const TextStyle(fontSize: 12),
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AudioPlayerButton(
                    audioUrl: sound.audioUrl,
                    iconSize: 20,
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.arrow_forward_ios, size: 16),
                ],
              ),
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) => PracticeDetailPage(
                      ipaSound: sound.ipa,
                      examples: sound.examples.split(',').map((e) => e.trim()).toList(),
                      description: sound.description,
                      lang: state.selectedLang,
                    ),
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}
