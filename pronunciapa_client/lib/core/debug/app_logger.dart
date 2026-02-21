import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

/// Global structured logger for PronunciaPA.
///
/// Usage:
///   AppLogger.d('TAG', 'message');
///   AppLogger.i('TAG', 'message');
///   AppLogger.w('TAG', 'message');
///   AppLogger.e('TAG', 'message', error: e, stackTrace: st);
///
/// In release builds all output is silenced automatically.
class AppLogger {
  AppLogger._();

  static final Logger _logger = Logger(
    printer: PrettyPrinter(
      methodCount: 0,
      errorMethodCount: 8,
      lineLength: 100,
      colors: true,
      printEmojis: true,
      dateTimeFormat: DateTimeFormat.onlyTimeAndSinceStart,
    ),
    // Silence everything in release builds.
    output: kDebugMode ? ConsoleOutput() : _NullOutput(),
    level: kDebugMode ? Level.debug : Level.off,
  );

  static void d(String tag, String message) =>
      _logger.d('[$tag] $message');

  static void i(String tag, String message) =>
      _logger.i('[$tag] $message');

  static void w(String tag, String message) =>
      _logger.w('[$tag] $message');

  static void e(
    String tag,
    String message, {
    Object? error,
    StackTrace? stackTrace,
  }) =>
      _logger.e('[$tag] $message', error: error, stackTrace: stackTrace);
}

/// Output that discards all log records.
class _NullOutput extends LogOutput {
  @override
  void output(OutputEvent event) {}
}
