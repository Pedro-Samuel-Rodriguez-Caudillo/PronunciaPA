import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/ipa_learning_provider.dart';
import '../providers/progress_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/app_background.dart';
import '../widgets/audio_player_button.dart';
import '../widgets/progress_indicator_widget.dart';

/// Individual sound lesson page with articulation guide and drills
class SoundLessonPage extends ConsumerStatefulWidget {
  final String soundId;
  final String ipa;
  final String name;

  const SoundLessonPage({
    super.key,
    required this.soundId,
    required this.ipa,
    required this.name,
  });

  @override
  ConsumerState<SoundLessonPage> createState() => _SoundLessonPageState();
}

class _SoundLessonPageState extends ConsumerState<SoundLessonPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<Drill> _drills = [];
  bool _isLoading = true;
  int _sessionPracticeCount = 0;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadDrills();
  }

  Future<void> _loadDrills() async {
    final drills = await ref.read(ipaLearningProvider.notifier).loadDrills(widget.soundId);
    if (mounted) {
      setState(() {
        _drills = drills;
        _isLoading = false;
      });
    }
  }

  void _recordPractice({required bool correct}) {
    ref.read(progressProvider.notifier).recordPractice(
      soundId: widget.soundId,
      correct: correct,
    );
    setState(() => _sessionPracticeCount++);
    
    // Show feedback
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              correct ? Icons.check_circle : Icons.info_outline,
              color: Colors.white,
            ),
            const SizedBox(width: 8),
            Text(correct ? '+10 XP! Keep it up!' : '+2 XP for trying!'),
          ],
        ),
        backgroundColor: correct ? Colors.green : Colors.blue,
        duration: const Duration(seconds: 1),
      ),
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    // Record practice time
    if (_sessionPracticeCount > 0) {
      ref.read(progressProvider.notifier).addPracticeTime(1);
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircleAvatar(
              backgroundColor: Theme.of(context).colorScheme.primary,
              radius: 16,
              child: Text(
                widget.ipa,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Text(widget.name),
          ],
        ),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.info_outline), text: 'Learn'),
            Tab(icon: Icon(Icons.fitness_center), text: 'Practice'),
            Tab(icon: Icon(Icons.compare_arrows), text: 'Contrast'),
          ],
        ),
      ),
      body: Stack(
        children: [
          const AppBackground(),
          SafeArea(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildLearnTab(),
                _buildPracticeTab(),
                _buildContrastTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLearnTab() {
    final soundProgress = ref.watch(soundProgressProvider(widget.soundId));
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Progress indicator
          if (soundProgress != null && soundProgress.practiceCount > 0)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: GlassCard(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    Column(
                      children: [
                        MasteryIndicator(
                          level: soundProgress.masteryLevel,
                          size: 48,
                          showLabel: true,
                        ),
                      ],
                    ),
                    Column(
                      children: [
                        Text(
                          '${soundProgress.practiceCount}',
                          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                        ),
                        const Text('Practices', style: TextStyle(fontSize: 12, color: Colors.grey)),
                      ],
                    ),
                    Column(
                      children: [
                        Text(
                          '${(soundProgress.accuracy * 100).toStringAsFixed(0)}%',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: soundProgress.accuracy >= 0.8 ? Colors.green : Colors.orange,
                          ),
                        ),
                        const Text('Accuracy', style: TextStyle(fontSize: 12, color: Colors.grey)),
                      ],
                    ),
                    if (soundProgress.streak > 0)
                      Column(
                        children: [
                          StreakIndicator(streak: soundProgress.streak, compact: true),
                          const Text('Streak', style: TextStyle(fontSize: 12, color: Colors.grey)),
                        ],
                      ),
                  ],
                ),
              ),
            ),

          // Main sound card with audio
          GlassCard(
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      '/${widget.ipa}/',
                      style: const TextStyle(
                        fontSize: 64,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(width: 16),
                    AudioPlayerButton(
                      audioUrl: '/api/ipa-sounds/audio?sound_id=${widget.soundId}',
                      iconSize: 32,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  widget.name,
                  style: const TextStyle(
                    fontSize: 18,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // How to pronounce
          const Text(
            'How to Pronounce',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildArticulationItem(
                  Icons.language,
                  'Tongue Position',
                  _getTongueGuide(widget.ipa),
                ),
                const Divider(),
                _buildArticulationItem(
                  Icons.air,
                  'Airflow',
                  _getAirflowGuide(widget.ipa),
                ),
                const Divider(),
                _buildArticulationItem(
                  Icons.vibration,
                  'Voicing',
                  _getVoicingGuide(widget.ipa),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Common mistakes
          const Text(
            'Common Mistakes',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          ..._getCommonMistakes(widget.ipa).map((mistake) => 
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: GlassCard(
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber, color: Colors.orange),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            mistake['error']!,
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          Text(
                            mistake['tip']!,
                            style: const TextStyle(fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildArticulationItem(IconData icon, String label, String description) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 24, color: Colors.blue),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPracticeTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    final practicedrills = _drills.where((d) => 
      d.type.contains('word') || d.type == 'isolation' || d.type == 'syllable'
    ).toList();

    if (practicedrills.isEmpty) {
      return const Center(
        child: Text('No practice drills available'),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: practicedrills.length,
      itemBuilder: (context, index) {
        final drill = practicedrills[index];
        return _buildDrillCard(drill);
      },
    );
  }

  Widget _buildContrastTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    final contrastDrills = _drills.where((d) => 
      d.type.contains('contrast')
    ).toList();

    if (contrastDrills.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.compare_arrows, size: 64, color: Colors.grey),
              const SizedBox(height: 16),
              const Text(
                'Minimal Pairs Practice',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'Compare /${widget.ipa}/ with similar sounds',
                style: const TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: contrastDrills.length,
      itemBuilder: (context, index) {
        final drill = contrastDrills[index];
        return _buildContrastDrillCard(drill);
      },
    );
  }

  Widget _buildDrillCard(Drill drill) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.blue.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    drill.type.replaceAll('_', ' ').toUpperCase(),
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: Colors.blue,
                    ),
                  ),
                ),
              ],
            ),
            if (drill.instruction != null) ...[
              const SizedBox(height: 8),
              Text(
                drill.instruction!,
                style: const TextStyle(fontSize: 14),
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: drill.targetsWithAudio.isNotEmpty
                  ? drill.targetsWithAudio.map((t) => _buildTargetChip(t)).toList()
                  : drill.targets.map((t) => Chip(label: Text(t))).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTargetChip(DrillTarget target) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            AudioPlayerButton(
              audioUrl: target.audioUrl,
              iconSize: 20,
              playIcon: Icons.play_arrow,
            ),
            const SizedBox(width: 8),
            Text(target.text, style: const TextStyle(fontWeight: FontWeight.w500)),
            const SizedBox(width: 12),
            // Practice feedback buttons
            IconButton(
              icon: const Icon(Icons.thumb_up, size: 18),
              color: Colors.green,
              tooltip: 'I got it!',
              onPressed: () => _recordPractice(correct: true),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.thumb_down, size: 18),
              color: Colors.orange,
              tooltip: 'Need practice',
              onPressed: () => _recordPractice(correct: false),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContrastDrillCard(Drill drill) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (drill.instruction != null)
              Text(
                drill.instruction!,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            const SizedBox(height: 12),
            ...drill.pairsWithAudio.map((pair) => _buildPairRow(pair)),
          ],
        ),
      ),
    );
  }

  Widget _buildPairRow(DrillPair pair) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              icon: AudioPlayerButton(
                audioUrl: pair.audio1Url,
                iconSize: 18,
              ),
              label: Text(pair.word1),
              onPressed: () {},
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 8),
            child: Text('vs', style: TextStyle(color: Colors.grey)),
          ),
          Expanded(
            child: OutlinedButton.icon(
              icon: AudioPlayerButton(
                audioUrl: pair.audio2Url,
                iconSize: 18,
              ),
              label: Text(pair.word2),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }

  // Helper methods for articulation guides
  String _getTongueGuide(String ipa) {
    switch (ipa) {
      case 'θ':
      case 'ð':
        return 'Place your tongue tip between your upper and lower teeth, or just behind your upper teeth.';
      case 'ɹ':
        return 'Curl your tongue tip back without touching the roof of your mouth. Some speakers bunch the tongue instead.';
      case 'æ':
        return 'Keep your tongue low and forward in your mouth.';
      case 'ʃ':
        return 'Raise the front of your tongue toward the roof of your mouth, just behind the alveolar ridge.';
      default:
        return 'Position varies based on the sound type.';
    }
  }

  String _getAirflowGuide(String ipa) {
    switch (ipa) {
      case 'θ':
      case 'ð':
      case 'ʃ':
        return 'Let air flow continuously through the narrow gap. Do not stop the airflow.';
      case 'ɹ':
        return 'Air flows freely around the tongue without friction.';
      case 'æ':
        return 'Open vowel - air flows freely through the mouth.';
      default:
        return 'Varies based on manner of articulation.';
    }
  }

  String _getVoicingGuide(String ipa) {
    switch (ipa) {
      case 'θ':
      case 'ʃ':
        return 'VOICELESS - Your vocal cords should NOT vibrate. Put your hand on your throat to check.';
      case 'ð':
      case 'ɹ':
      case 'æ':
        return 'VOICED - Your vocal cords SHOULD vibrate. Put your hand on your throat to feel the vibration.';
      default:
        return 'Check if you feel vibration in your throat.';
    }
  }

  List<Map<String, String>> _getCommonMistakes(String ipa) {
    switch (ipa) {
      case 'θ':
        return [
          {'error': 'Saying /s/ instead', 'tip': 'Make sure your tongue touches your teeth'},
          {'error': 'Saying /t/ instead', 'tip': 'Don\'t stop the air - let it flow continuously'},
          {'error': 'Saying /f/ instead', 'tip': 'Use your tongue, not your lower lip'},
        ];
      case 'ð':
        return [
          {'error': 'Saying /d/ instead', 'tip': 'Keep the air flowing - don\'t stop it'},
          {'error': 'Saying /z/ instead', 'tip': 'Tongue between teeth, not behind them'},
        ];
      case 'ɹ':
        return [
          {'error': 'Tapping like Spanish /r/', 'tip': 'English R doesn\'t tap - tongue stays still'},
          {'error': 'Saying /l/ instead', 'tip': 'Don\'t let your tongue touch the roof'},
          {'error': 'Saying /w/ instead', 'tip': 'Pull your tongue back more'},
        ];
      default:
        return [];
    }
  }
}
