import 'dart:io' show Platform;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/pronuncia_remote_datasource.dart';
import '../../data/repositories/pronunciation_repository_impl.dart';
import '../../domain/repositories/pronunciation_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/debug/app_logger.dart';

const _tag = 'RepositoryProvider';

/// Provider for base URL configuration
final baseUrlProvider = StateNotifierProvider<BaseUrlNotifier, String>((ref) {
  return BaseUrlNotifier();
});

class BaseUrlNotifier extends StateNotifier<String> {
  static const String _key = 'api_base_url';

  /// Android emulator uses 10.0.2.2 to reach host loopback;
  /// desktop/iOS use localhost directly.
  static String get _defaultUrl =>
      Platform.isAndroid ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000';

  BaseUrlNotifier() : super(_defaultUrl) {
    _loadUrl();
  }

  Future<void> _loadUrl() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString(_key);
      if (savedUrl != null && savedUrl.isNotEmpty) {
        state = savedUrl;
      }
    } catch (e) {
      AppLogger.w(_tag, 'Failed to load base URL: $e');
    }
  }

  Future<void> setUrl(String url) async {
    try {
      // Validate URL format
      final uri = Uri.tryParse(url);
      if (uri == null || (!uri.scheme.startsWith('http'))) {
        throw Exception('Invalid URL format. Must start with http:// or https://');
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_key, url);
      state = url;
    } catch (e) {
      throw Exception('Failed to save base URL: $e');
    }
  }

  Future<void> resetToDefault() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_key);
      state = _defaultUrl;
    } catch (e) {
      AppLogger.w(_tag, 'Failed to reset base URL: $e');
    }
  }

  /// Current default for display purposes.
  String get defaultUrl => _defaultUrl;
}

/// Provider for remote data source
final remoteDataSourceProvider = Provider<PronunciaRemoteDataSource>((ref) {
  final baseUrl = ref.watch(baseUrlProvider);
  return PronunciaRemoteDataSource(
    baseUrl: baseUrl,
    requestTimeout: const Duration(seconds: 30),
  );
});

/// Provider for pronunciation repository
final pronunciationRepositoryProvider = Provider<PronunciationRepository>((ref) {
  final dataSource = ref.watch(remoteDataSourceProvider);
  return PronunciationRepositoryImpl(remoteDataSource: dataSource);
});
