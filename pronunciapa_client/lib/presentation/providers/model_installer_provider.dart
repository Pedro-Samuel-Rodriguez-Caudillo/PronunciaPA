import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Información de un modelo
class ModelInfo {
  final String id;
  final String name;
  final String category;
  final String description;
  final int sizeMb;
  final String status;
  final double progress;
  final String? error;
  final bool isRequired;
  final bool isRecommended;

  ModelInfo({
    required this.id,
    required this.name,
    required this.category,
    required this.description,
    required this.sizeMb,
    required this.status,
    this.progress = 0,
    this.error,
    this.isRequired = false,
    this.isRecommended = false,
  });

  factory ModelInfo.fromJson(Map<String, dynamic> json) {
    return ModelInfo(
      id: json['id'] as String,
      name: json['name'] as String,
      category: json['category'] as String,
      description: json['description'] as String,
      sizeMb: json['size_mb'] as int,
      status: json['status'] as String,
      progress: (json['progress'] as num?)?.toDouble() ?? 0,
      error: json['error'] as String?,
      isRequired: json['is_required'] as bool? ?? false,
      isRecommended: json['is_recommended'] as bool? ?? false,
    );
  }

  bool get isInstalled => status == 'installed';
  bool get isInstalling => status == 'installing';
  bool get hasError => status == 'error';
}

/// Resumen del estado de modelos
class ModelsSummary {
  final int total;
  final int installed;
  final int missing;
  final List<String> requiredMissing;
  final bool ready;

  ModelsSummary({
    required this.total,
    required this.installed,
    required this.missing,
    required this.requiredMissing,
    required this.ready,
  });

  factory ModelsSummary.fromJson(Map<String, dynamic> json) {
    return ModelsSummary(
      total: json['total'] as int,
      installed: json['installed'] as int,
      missing: json['missing'] as int,
      requiredMissing: (json['required_missing'] as List).cast<String>(),
      ready: json['ready'] as bool,
    );
  }
}

/// Estado de todos los modelos
class ModelsState {
  final ModelsSummary summary;
  final Map<String, List<ModelInfo>> modelsByCategory;
  final bool isLoading;
  final String? error;

  ModelsState({
    required this.summary,
    required this.modelsByCategory,
    this.isLoading = false,
    this.error,
  });

  factory ModelsState.initial() {
    return ModelsState(
      summary: ModelsSummary(
        total: 0,
        installed: 0,
        missing: 0,
        requiredMissing: [],
        ready: false,
      ),
      modelsByCategory: {},
    );
  }

  ModelsState copyWith({
    ModelsSummary? summary,
    Map<String, List<ModelInfo>>? modelsByCategory,
    bool? isLoading,
    String? error,
  }) {
    return ModelsState(
      summary: summary ?? this.summary,
      modelsByCategory: modelsByCategory ?? this.modelsByCategory,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Servicio para gestionar modelos
class ModelInstallerService {
  final String baseUrl;

  ModelInstallerService({String? baseUrl})
      : baseUrl = baseUrl ?? _determineBaseUrl();

  static String _determineBaseUrl() {
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://127.0.0.1:8000';
  }

  void _log(String message) {
    developer.log(message, name: 'ModelInstallerService');
  }

  /// Obtener estado de todos los modelos
  Future<ModelsState> getModelsStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/models'),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        final summary = ModelsSummary.fromJson(data['summary']);
        final modelsData = data['models'] as Map<String, dynamic>;
        
        final modelsByCategory = <String, List<ModelInfo>>{};
        for (final entry in modelsData.entries) {
          final models = (entry.value as List)
              .map((m) => ModelInfo.fromJson(m))
              .toList();
          modelsByCategory[entry.key] = models;
        }

        return ModelsState(
          summary: summary,
          modelsByCategory: modelsByCategory,
        );
      } else {
        throw Exception('Error ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      _log('Error getting models status: $e');
      rethrow;
    }
  }

  /// Instalar un modelo específico
  Future<ModelInfo> installModel(String modelId) async {
    try {
      _log('Installing model: $modelId');
      
      final response = await http.post(
        Uri.parse('$baseUrl/api/models/$modelId/install'),
      ).timeout(const Duration(minutes: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          return ModelInfo.fromJson(data['model']);
        } else {
          throw Exception(data['error'] ?? 'Installation failed');
        }
      } else {
        final data = jsonDecode(response.body);
        throw Exception(data['error'] ?? 'Error ${response.statusCode}');
      }
    } catch (e) {
      _log('Error installing model $modelId: $e');
      rethrow;
    }
  }

  /// Instalar todos los modelos requeridos
  Future<Map<String, dynamic>> installRequired() async {
    try {
      _log('Installing required models...');
      
      final response = await http.post(
        Uri.parse('$baseUrl/api/models/install-required'),
      ).timeout(const Duration(minutes: 15));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Error ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      _log('Error installing required models: $e');
      rethrow;
    }
  }

  /// Instalar todos los modelos recomendados
  Future<Map<String, dynamic>> installRecommended() async {
    try {
      _log('Installing recommended models...');
      
      final response = await http.post(
        Uri.parse('$baseUrl/api/models/install-recommended'),
      ).timeout(const Duration(minutes: 30));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Error ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      _log('Error installing recommended models: $e');
      rethrow;
    }
  }

  /// Quick setup (Python packages)
  Future<Map<String, dynamic>> quickSetup() async {
    try {
      _log('Running quick setup...');
      
      final response = await http.post(
        Uri.parse('$baseUrl/api/quick-setup'),
      ).timeout(const Duration(minutes: 5));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Error ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      _log('Error in quick setup: $e');
      rethrow;
    }
  }
}

/// Provider para el servicio de instalación
final modelInstallerServiceProvider = Provider<ModelInstallerService>((ref) {
  return ModelInstallerService();
});

/// Provider para el estado de modelos
final modelsStateProvider = StateNotifierProvider<ModelsStateNotifier, ModelsState>((ref) {
  final service = ref.watch(modelInstallerServiceProvider);
  return ModelsStateNotifier(service);
});

class ModelsStateNotifier extends StateNotifier<ModelsState> {
  final ModelInstallerService _service;

  ModelsStateNotifier(this._service) : super(ModelsState.initial());

  /// Cargar estado de modelos
  Future<void> loadStatus() async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final newState = await _service.getModelsStatus();
      state = newState;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Instalar un modelo
  Future<bool> installModel(String modelId) async {
    try {
      await _service.installModel(modelId);
      await loadStatus(); // Recargar estado
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  /// Setup rápido
  Future<bool> quickSetup() async {
    state = state.copyWith(isLoading: true);
    
    try {
      await _service.quickSetup();
      await loadStatus();
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  /// Instalar requeridos
  Future<bool> installRequired() async {
    state = state.copyWith(isLoading: true);
    
    try {
      await _service.installRequired();
      await loadStatus();
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  /// Instalar recomendados
  Future<bool> installRecommended() async {
    state = state.copyWith(isLoading: true);
    
    try {
      await _service.installRecommended();
      await loadStatus();
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }
}
