import 'dart:async';

/// A single captured HTTP call entry displayed in the debug overlay.
class HttpLogEntry {
  final String method;
  final String url;
  final int? statusCode;
  final int durationMs;
  final String? requestInfo; // fields / file names for multipart
  final String? responseBody;
  final String? error;
  final DateTime timestamp;

  const HttpLogEntry({
    required this.method,
    required this.url,
    this.statusCode,
    required this.durationMs,
    this.requestInfo,
    this.responseBody,
    this.error,
    required this.timestamp,
  });

  bool get isSuccess => statusCode != null && statusCode! >= 200 && statusCode! < 300;
  bool get isFailure => statusCode == null || statusCode! >= 400;
}

/// A single application event (provider change, audio event, etc.) for display.
class AppLogEntry {
  final String tag;
  final String message;
  final AppLogLevel level;
  final DateTime timestamp;

  const AppLogEntry({
    required this.tag,
    required this.message,
    required this.level,
    required this.timestamp,
  });
}

enum AppLogLevel { debug, info, warning, error }

/// Singleton in-memory store for the debug overlay.
/// Holds the last [maxEntries] HTTP calls and app events.
class DebugLogStore {
  DebugLogStore._();
  static final DebugLogStore instance = DebugLogStore._();

  static const int maxEntries = 100;

  final List<HttpLogEntry> _httpEntries = [];
  final List<AppLogEntry> _appEntries = [];

  final _httpController =
      StreamController<List<HttpLogEntry>>.broadcast();
  final _appController =
      StreamController<List<AppLogEntry>>.broadcast();

  // ── HTTP calls ────────────────────────────────────────────────────────────

  void addHttp(HttpLogEntry entry) {
    _httpEntries.insert(0, entry);
    if (_httpEntries.length > maxEntries) _httpEntries.removeLast();
    _httpController.add(List.unmodifiable(_httpEntries));
  }

  Stream<List<HttpLogEntry>> get httpStream => _httpController.stream;
  List<HttpLogEntry> get httpEntries => List.unmodifiable(_httpEntries);

  // ── App events ────────────────────────────────────────────────────────────

  void addApp(AppLogEntry entry) {
    _appEntries.insert(0, entry);
    if (_appEntries.length > maxEntries) _appEntries.removeLast();
    _appController.add(List.unmodifiable(_appEntries));
  }

  Stream<List<AppLogEntry>> get appStream => _appController.stream;
  List<AppLogEntry> get appEntries => List.unmodifiable(_appEntries);

  void clear() {
    _httpEntries.clear();
    _appEntries.clear();
    _httpController.add([]);
    _appController.add([]);
  }
}
