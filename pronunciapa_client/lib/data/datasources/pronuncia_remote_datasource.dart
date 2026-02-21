import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../../core/debug/debug_http_client.dart';

/// Remote data source for PronunciaPA API
/// Handles all HTTP communication with backend
class PronunciaRemoteDataSource {
  final String baseUrl;
  final Duration requestTimeout;
  final http.Client _client;

  PronunciaRemoteDataSource({
    required this.baseUrl,
    this.requestTimeout = const Duration(seconds: 30),
    http.Client? client,
  }) : _client = client ?? (kDebugMode ? DebugHttpClient() : http.Client());

  /// Transcribe audio file to IPA
  Future<Map<String, dynamic>> transcribe(
    String audioPath, {
    String? lang,
    String? asr,
    String? textref,
    bool persist = false,
  }) async {
    final file = File(audioPath);
    if (!file.existsSync()) {
      throw Exception('Audio file not found: $audioPath');
    }

    final uri = Uri.parse('$baseUrl/v1/transcribe');
    final request = http.MultipartRequest('POST', uri);
    
    request.files.add(
      await http.MultipartFile.fromPath('audio', file.path),
    );
    
    if (lang != null && lang.isNotEmpty) {
      request.fields['lang'] = lang;
    }
    if (asr != null && asr.isNotEmpty) {
      request.fields['backend'] = asr;  // El servidor espera 'backend', no 'asr'
    }
    if (textref != null && textref.isNotEmpty) {
      request.fields['textref'] = textref;
    }
    if (persist) {
      request.fields['persist'] = 'true';
    }

    final response = await _client.send(request).timeout(requestTimeout);
    final body = await response.stream.bytesToString();
    
    if (response.statusCode == 200) {
      return jsonDecode(body) as Map<String, dynamic>;
    } else {
      throw _parseError(response.statusCode, body);
    }
  }

  /// Compare audio transcription with reference text
  Future<Map<String, dynamic>> compare(
    String audioPath,
    String referenceText, {
    String lang = 'es',
    String? asr,
    String? textref,
    String? comparator,
    String? evaluationLevel,
    String? mode,
    String? pack,
    bool persist = false,
  }) async {
    final file = File(audioPath);
    if (!file.existsSync()) {
      throw Exception('Audio file not found: $audioPath');
    }

    final uri = Uri.parse('$baseUrl/v1/compare');
    final request = http.MultipartRequest('POST', uri);
    
    request.files.add(
      await http.MultipartFile.fromPath('audio', file.path),
    );
    request.fields['text'] = referenceText;
    
    if (lang.isNotEmpty) {
      request.fields['lang'] = lang;
    }
    if (asr != null && asr.isNotEmpty) {
      request.fields['backend'] = asr;  // El servidor espera 'backend', no 'asr'
    }
    if (textref != null && textref.isNotEmpty) {
      request.fields['textref'] = textref;
    }
    if (comparator != null && comparator.isNotEmpty) {
      request.fields['comparator'] = comparator;
    }
    if (evaluationLevel != null && evaluationLevel.isNotEmpty) {
      request.fields['evaluation_level'] = evaluationLevel;
    }
    if (mode != null && mode.isNotEmpty) {
      request.fields['mode'] = mode;
    }
    if (pack != null && pack.isNotEmpty) {
      request.fields['pack'] = pack;
    }
    if (persist) {
      request.fields['persist'] = 'true';
    }

    final response = await _client.send(request).timeout(requestTimeout);
    final body = await response.stream.bytesToString();
    
    if (response.statusCode == 200) {
      return jsonDecode(body) as Map<String, dynamic>;
    } else {
      throw _parseError(response.statusCode, body);
    }
  }

  /// Get detailed feedback on pronunciation
  Future<Map<String, dynamic>> feedback(
    String audioPath,
    String referenceText, {
    String lang = 'es',
    String? evaluationLevel,
    String? mode,
    String? feedbackLevel,
    bool persist = false,
  }) async {
    final file = File(audioPath);
    if (!file.existsSync()) {
      throw Exception('Audio file not found: $audioPath');
    }

    final uri = Uri.parse('$baseUrl/v1/feedback');
    final request = http.MultipartRequest('POST', uri);
    
    request.files.add(
      await http.MultipartFile.fromPath('audio', file.path),
    );
    request.fields['text'] = referenceText;
    
    if (lang.isNotEmpty) {
      request.fields['lang'] = lang;
    }
    if (evaluationLevel != null && evaluationLevel.isNotEmpty) {
      request.fields['evaluation_level'] = evaluationLevel;
    }
    if (mode != null && mode.isNotEmpty) {
      request.fields['mode'] = mode;
    }
    if (feedbackLevel != null && feedbackLevel.isNotEmpty) {
      request.fields['feedback_level'] = feedbackLevel;
    }
    if (persist) {
      request.fields['persist'] = 'true';
    }

    final response = await _client.send(request).timeout(requestTimeout);
    final body = await response.stream.bytesToString();
    
    if (response.statusCode == 200) {
      return jsonDecode(body) as Map<String, dynamic>;
    } else {
      throw _parseError(response.statusCode, body);
    }
  }

  /// Get text reference (convert text to IPA)
  Future<Map<String, dynamic>> textref(
    String text, {
    String lang = 'es',
    String? textref,
  }) async {
    final uri = Uri.parse('$baseUrl/v1/textref');
    final request = http.MultipartRequest('POST', uri);
    request.fields['text'] = text;
    request.fields['lang'] = lang;
    if (textref != null && textref.isNotEmpty) {
      request.fields['textref'] = textref;
    }
    
    final streamedResponse = await _client.send(request).timeout(requestTimeout);
    final response = await http.Response.fromStream(streamedResponse);
    final body = response.body;
    
    if (response.statusCode == 200) {
      return jsonDecode(body) as Map<String, dynamic>;
    } else {
      throw _parseError(response.statusCode, body);
    }
  }

  /// Check API health
  Future<Map<String, dynamic>> health() async {
    final uri = Uri.parse('$baseUrl/health');
    final response = await _client.get(uri).timeout(requestTimeout);
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Health check failed with status ${response.statusCode}');
    }
  }

  Exception _parseError(int statusCode, String body) {
    try {
      final data = jsonDecode(body);
      final errorType = data is Map ? data['type']?.toString() : null;
      final backendName = data is Map ? data['backend']?.toString() : null;
      if (errorType == 'asr_unavailable') {
        final backend = (backendName == null || backendName.isEmpty)
            ? 'stub'
            : backendName;
        return Exception(
          'ASR IPA no disponible (backend: $backend). '
          'Configura un ASR real en el servidor y desactiva PRONUNCIAPA_ASR=stub.',
        );
      }
      final detail = data['detail'];
      if (detail is String) {
        return Exception('API error ($statusCode): $detail');
      } else if (detail is Map) {
        final msg = detail['message'] ?? detail.toString();
        return Exception('API error ($statusCode): $msg');
      }
      return Exception('API error ($statusCode): ${data.toString()}');
    } catch (_) {
      return Exception('API error ($statusCode): $body');
    }
  }
}
