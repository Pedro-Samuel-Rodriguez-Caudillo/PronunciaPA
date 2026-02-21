import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../domain/repositories/pronunciation_repository.dart';
import 'repository_provider.dart';
import '../../core/debug/app_logger.dart';

const _ipaPracticeTag = 'IpaPractice';

/// Model for IPA sound item
class IpaSound {
  final String ipa;
  final String examples;
  final String description;
  final String? id;
  final String? label;
  final List<String>? tags;
  final String? audioUrl;

  IpaSound({
    required this.ipa,
    required this.examples,
    required this.description,
    this.id,
    this.label,
    this.tags,
    this.audioUrl,
  });

  factory IpaSound.fromJson(Map<String, dynamic> json) {
    // Adaptar formato del backend al formato del cliente
    final contexts = json['contexts'] as Map<String, dynamic>?;
    final examples = _extractExamples(contexts);
    
    return IpaSound(
      ipa: json['ipa'] as String,
      examples: examples,
      description: json['label'] as String? ?? '',
      id: json['id'] as String?,
      label: json['label'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.cast<String>(),
      audioUrl: json['audio_url'] as String?,
    );
  }
  
  static String _extractExamples(Map<String, dynamic>? contexts) {
    if (contexts == null) return '';
    
    final examples = <String>[];
    for (final entry in contexts.entries) {
      final context = entry.value as Map<String, dynamic>?;
      final seeds = context?['seeds'] as List<dynamic>?;
      if (seeds != null) {
        for (final seed in seeds.take(3)) {
          final text = seed['text'] as String?;
          if (text != null) examples.add(text);
        }
      }
    }
    
    return examples.join(', ');
  }
}

/// State for IPA practice
class IpaPracticeState {
  final List<IpaSound> sounds;
  final bool isLoading;
  final String? error;
  final String selectedLang;

  IpaPracticeState({
    this.sounds = const [],
    this.isLoading = false,
    this.error,
    this.selectedLang = 'en',
  });

  IpaPracticeState copyWith({
    List<IpaSound>? sounds,
    bool? isLoading,
    String? error,
    String? selectedLang,
  }) {
    return IpaPracticeState(
      sounds: sounds ?? this.sounds,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      selectedLang: selectedLang ?? this.selectedLang,
    );
  }
}

/// Provider for IPA practice state
class IpaPracticeNotifier extends StateNotifier<IpaPracticeState> {
  IpaPracticeNotifier(PronunciationRepository repository) : super(IpaPracticeState()) {
    loadSounds();
  }

  Future<void> loadSounds({String? lang}) async {
    final targetLang = lang ?? state.selectedLang;
    
    state = state.copyWith(isLoading: true, error: null);

    try {
      // Intentar cargar desde el backend real
      try {
        final sounds = await _fetchIpaSounds(targetLang);
        state = state.copyWith(
          sounds: sounds,
          isLoading: false,
          selectedLang: targetLang,
        );
        return;
      } catch (e) {
        // Si falla, usar mock data como fallback
        AppLogger.w(_ipaPracticeTag, 'Error fetching IPA sounds from API, using mock data: $e');
      }
      
      // Fallback a mock data
      final sounds = _getMockIpaSounds(targetLang);
      
      state = state.copyWith(
        sounds: sounds,
        isLoading: false,
        selectedLang: targetLang,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Error cargando sonidos IPA: $e',
      );
    }
  }

  Future<List<IpaSound>> _fetchIpaSounds(String lang) async {
    // Usar localhost para desarrollo
    const baseUrl = 'http://127.0.0.1:8000';
    final url = Uri.parse('$baseUrl/api/ipa-sounds?lang=$lang');
    
    final response = await http.get(url).timeout(
      const Duration(seconds: 5),
      onTimeout: () {
        throw Exception('Timeout connecting to backend');
      },
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to load IPA sounds: ${response.statusCode}');
    }
    
    final data = json.decode(response.body) as Map<String, dynamic>;
    final soundsList = data['sounds'] as List<dynamic>;
    
    return soundsList
        .map((s) => IpaSound.fromJson(s as Map<String, dynamic>))
        .toList();
  }

  List<IpaSound> _getMockIpaSounds(String lang) {
    if (lang == 'es') {
      return [
        IpaSound(
          ipa: 's',
          examples: 'casa, solo, este',
          description: 'Sonido [s] alveolar sordo',
        ),
        IpaSound(
          ipa: 'θ',
          examples: 'zapato, cielo, hace (España)',
          description: 'Sonido [θ] interdental sordo',
        ),
        IpaSound(
          ipa: 'x',
          examples: 'jota, gente, ajo',
          description: 'Sonido [x] velar fricativo sordo',
        ),
        IpaSound(
          ipa: 'r',
          examples: 'pero, caro, ahora',
          description: 'Vibrante simple alveolar',
        ),
        IpaSound(
          ipa: 'r̄',
          examples: 'perro, carro, rosa',
          description: 'Vibrante múltiple alveolar',
        ),
        IpaSound(
          ipa: 'ɲ',
          examples: 'año, niño, señor',
          description: 'Nasal palatal sonoro [ɲ]',
        ),
        IpaSound(
          ipa: 'ʎ',
          examples: 'llorar, calle, lluvia',
          description: 'Lateral palatal sonoro [ʎ]',
        ),
        IpaSound(
          ipa: 'ʧ',
          examples: 'chico, mucho, leche',
          description: 'Africada postalveolar sorda',
        ),
        IpaSound(
          ipa: 'β',
          examples: 'cabeza, libro, vino',
          description: 'Fricativa bilabial sonora [β]',
        ),
        IpaSound(
          ipa: 'ð',
          examples: 'cada, nada, lado',
          description: 'Fricativa dental sonora [ð]',
        ),
        IpaSound(
          ipa: 'ɣ',
          examples: 'agua, hago, luego',
          description: 'Fricativa velar sonora [ɣ]',
        ),
      ];
    } else if (lang == 'en') {
      return [
        IpaSound(
          ipa: 'θ',
          examples: 'think, bath, author',
          description: 'Voiceless dental fricative [θ]',
        ),
        IpaSound(
          ipa: 'ð',
          examples: 'this, bathe, father',
          description: 'Voiced dental fricative [ð]',
        ),
        IpaSound(
          ipa: 'ʃ',
          examples: 'ship, wash, nation',
          description: 'Voiceless postalveolar fricative [ʃ]',
        ),
        IpaSound(
          ipa: 'ʒ',
          examples: 'measure, vision, azure',
          description: 'Voiced postalveolar fricative [ʒ]',
        ),
        IpaSound(
          ipa: 'ŋ',
          examples: 'sing, ring, thing',
          description: 'Velar nasal [ŋ]',
        ),
        IpaSound(
          ipa: 'r',
          examples: 'red, car, far',
          description: 'Alveolar approximant [ɹ]',
        ),
        IpaSound(
          ipa: 'w',
          examples: 'wet, quick, twin',
          description: 'Labial-velar approximant [w]',
        ),
        IpaSound(
          ipa: 'j',
          examples: 'yes, you, onion',
          description: 'Palatal approximant [j]',
        ),
      ];
    }
    
    // Default empty list for other languages
    return [];
  }

  void setLanguage(String lang) {
    loadSounds(lang: lang);
  }

  void retry() {
    loadSounds();
  }
}

/// Provider instance
final ipaPracticeProvider = StateNotifierProvider<IpaPracticeNotifier, IpaPracticeState>((ref) {
  final repository = ref.watch(pronunciationRepositoryProvider);
  return IpaPracticeNotifier(repository);
});
