import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/ipa_learning_provider.dart';
import '../providers/progress_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';
import '../widgets/audio_player_button.dart';
import '../widgets/progress_indicator_widget.dart';
import 'sound_lesson_page.dart';

/// IPA Learning page - teaches users about IPA symbols and pronunciation
class IpaLearnPage extends ConsumerStatefulWidget {
  const IpaLearnPage({super.key});

  @override
  ConsumerState<IpaLearnPage> createState() => _IpaLearnPageState();
}

class _IpaLearnPageState extends ConsumerState<IpaLearnPage> {
  String _selectedLang = 'en';
  
  @override
  Widget build(BuildContext context) {
    final learningState = ref.watch(ipaLearningProvider);
    final progress = ref.watch(progressProvider);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('Learn IPA'),
        centerTitle: true,
        actions: [
          // Language selector
          PopupMenuButton<String>(
            icon: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(_selectedLang.toUpperCase(), 
                  style: const TextStyle(fontWeight: FontWeight.bold)),
                const Icon(Icons.arrow_drop_down),
              ],
            ),
            onSelected: (lang) {
              setState(() => _selectedLang = lang);
              ref.read(ipaLearningProvider.notifier).loadContent(lang);
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'en', child: Text('🇺🇸 English')),
              const PopupMenuItem(value: 'es', child: Text('🇪🇸 Español')),
            ],
          ),
        ],
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: learningState.isLoading
                ? const Center(child: CircularProgressIndicator())
                : learningState.error != null
                    ? _buildError(context, learningState.error!)
                    : _buildContent(context, ref, learningState, progress),
          ),
        ],
      ),
    );
  }

  Widget _buildError(BuildContext context, String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(error, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                ref.read(ipaLearningProvider.notifier).loadContent(_selectedLang);
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, IpaLearningState state, LearningProgressState progress) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Progress summary card
          ProgressSummaryCard(progress: progress),
          const SizedBox(height: 20),

          // Introduction section
          _buildIntroCard(context),
          const SizedBox(height: 24),

          // Inventory overview
          if (state.inventory.isNotEmpty) ...[
            _buildInventoryCard(context, state.inventory),
            const SizedBox(height: 24),
          ],

          // Learning modules
          if (state.modules.isNotEmpty) ...[
            _buildSectionHeader('Learning Modules', Icons.menu_book),
            const SizedBox(height: 12),
            ...state.modules.map((m) => _buildModuleCard(context, m, progress)),
            const SizedBox(height: 24),
          ],

          // Sound lessons
          _buildSectionHeader('Sound Lessons', Icons.record_voice_over),
          const SizedBox(height: 12),
          
          // Group by difficulty
          _buildDifficultySection(context, ref, state.sounds, progress, 1, 'Beginner', Colors.green),
          _buildDifficultySection(context, ref, state.sounds, progress, 2, 'Elementary', Colors.lightGreen),
          _buildDifficultySection(context, ref, state.sounds, progress, 3, 'Intermediate', Colors.orange),
          _buildDifficultySection(context, ref, state.sounds, progress, 4, 'Advanced', Colors.deepOrange),
          _buildDifficultySection(context, ref, state.sounds, progress, 5, 'Expert', Colors.red),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 24, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildDifficultySection(
    BuildContext context,
    WidgetRef ref,
    List<SoundLesson> allSounds,
    LearningProgressState progress,
    int difficulty,
    String label,
    Color color,
  ) {
    final sounds = allSounds.where((s) => s.difficulty == difficulty).toList();
    if (sounds.isEmpty) return const SizedBox.shrink();
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: color.withOpacity(0.5)),
                ),
                child: Text(
                  '$label (${sounds.length})',
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ),
        ...sounds.map((s) => _buildSoundCard(context, s, progress)),
      ],
    );
  }

  Widget _buildIntroCard(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primary.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.school, size: 32),
              ),
              const SizedBox(width: 16),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'What is IPA?',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      'International Phonetic Alphabet',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Text(
            'IPA uses unique symbols for each sound. Unlike regular spelling, '
            'each symbol represents exactly ONE sound.\n\n'
            'For example, "th" in English represents TWO different sounds:\n'
            '• /θ/ as in "think" (voiceless)\n'
            '• /ð/ as in "this" (voiced)',
            style: TextStyle(fontSize: 14, height: 1.5),
          ),
        ],
      ),
    );
  }

  Widget _buildInventoryCard(BuildContext context, Map<String, int> inventory) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'English Sound Inventory',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildInventoryStat(
                context,
                inventory['consonants']?.toString() ?? '24',
                'Consonants',
                Icons.mic,
              ),
              _buildInventoryStat(
                context,
                inventory['vowels']?.toString() ?? '14',
                'Vowels',
                Icons.record_voice_over,
              ),
              _buildInventoryStat(
                context,
                inventory['diphthongs']?.toString() ?? '5',
                'Diphthongs',
                Icons.swap_horiz,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInventoryStat(
    BuildContext context,
    String value,
    String label,
    IconData icon,
  ) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, size: 24),
        ),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Colors.grey,
          ),
        ),
      ],
    );
  }

  Widget _buildModuleCard(BuildContext context, IpaModule module, LearningProgressState progress) {
    final isCompleted = progress.completedModules.contains(module.id);
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        padding: EdgeInsets.zero,
        child: ListTile(
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: isCompleted 
                  ? Colors.green.withOpacity(0.2)
                  : Colors.blue.withOpacity(0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              isCompleted ? Icons.check_circle : Icons.menu_book, 
              color: isCompleted ? Colors.green : Colors.blue,
            ),
          ),
          title: Text(module.title),
          subtitle: module.description != null
              ? Text(
                  module.description!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                )
              : null,
          trailing: isCompleted 
              ? const Icon(Icons.check, color: Colors.green)
              : const Icon(Icons.arrow_forward_ios, size: 16),
          onTap: () {
            _showModuleContent(context, module);
          },
        ),
      ),
    );
  }

  void _showModuleContent(BuildContext context, IpaModule module) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        minChildSize: 0.5,
        builder: (context, scrollController) => Container(
          decoration: BoxDecoration(
            color: Theme.of(context).scaffoldBackgroundColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              Container(
                margin: const EdgeInsets.only(top: 12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade400,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        module.title,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  controller: scrollController,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Text(
                    module.content ?? module.description ?? '',
                    style: const TextStyle(fontSize: 16, height: 1.6),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(20),
                child: SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {
                      ref.read(progressProvider.notifier).completeModule(module.id);
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Module "${module.title}" completed! +50 XP'),
                          backgroundColor: Colors.green,
                        ),
                      );
                    },
                    child: const Text('Mark as Complete'),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSoundCard(BuildContext context, SoundLesson sound, LearningProgressState progress) {
    final soundProgress = progress.soundProgress[sound.id];
    final masteryLevel = soundProgress?.masteryLevel ?? 0;
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: GlassCard(
        padding: EdgeInsets.zero,
        child: ListTile(
          leading: Stack(
            children: [
              CircleAvatar(
                backgroundColor: _getDifficultyColor(sound.difficulty),
                radius: 24,
                child: Text(
                  sound.ipa,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
              if (masteryLevel > 0)
                Positioned(
                  right: -2,
                  bottom: -2,
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      color: Theme.of(context).scaffoldBackgroundColor,
                      shape: BoxShape.circle,
                    ),
                    child: MasteryIndicator(level: masteryLevel, size: 20),
                  ),
                ),
            ],
          ),
          title: Text(
            sound.commonName ?? sound.ipa,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          subtitle: Row(
            children: [
              ...List.generate(
                5,
                (i) => Icon(
                  i < sound.difficulty ? Icons.star : Icons.star_border,
                  size: 12,
                  color: i < sound.difficulty ? Colors.amber : Colors.grey.shade400,
                ),
              ),
              const SizedBox(width: 8),
              if (soundProgress != null && soundProgress.practiceCount > 0)
                Text(
                  '${soundProgress.practiceCount} practices • ${(soundProgress.accuracy * 100).toStringAsFixed(0)}%',
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                ),
            ],
          ),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              AudioPlayerButton(
                audioUrl: '/api/ipa-sounds/audio?sound_id=${sound.id}',
                iconSize: 20,
              ),
              const SizedBox(width: 4),
              const Icon(Icons.arrow_forward_ios, size: 16),
            ],
          ),
          onTap: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (context) => SoundLessonPage(
                  soundId: sound.id,
                  ipa: sound.ipa,
                  name: sound.commonName ?? sound.ipa,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Color _getDifficultyColor(int difficulty) {
    switch (difficulty) {
      case 1:
        return Colors.green;
      case 2:
        return Colors.lightGreen;
      case 3:
        return Colors.orange;
      case 4:
        return Colors.deepOrange;
      case 5:
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _getDifficultyLabel(int difficulty) {
    switch (difficulty) {
      case 1:
        return 'Easy';
      case 2:
        return 'Simple';
      case 3:
        return 'Moderate';
      case 4:
        return 'Challenging';
      case 5:
        return 'Advanced';
      default:
        return 'Unknown';
    }
  }
}
