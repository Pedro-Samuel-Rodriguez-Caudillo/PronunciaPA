import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app_logger.dart';
import 'debug_log_store.dart';

const _tag = 'Riverpod';

/// A [ProviderObserver] that logs every provider state change and error to
/// [AppLogger] and [DebugLogStore] so they appear both in the console and in
/// the in-app debug overlay.
class DebugProviderObserver extends ProviderObserver {
  const DebugProviderObserver();

  @override
  void didAddProvider(
    ProviderBase<Object?> provider,
    Object? value,
    ProviderContainer container,
  ) {
    AppLogger.d(_tag, 'INIT  ${_name(provider)} → ${_preview(value)}');
  }

  @override
  void didUpdateProvider(
    ProviderBase<Object?> provider,
    Object? previousValue,
    Object? newValue,
    ProviderContainer container,
  ) {
    final msg =
        'UPDATE ${_name(provider)}\n  prev: ${_preview(previousValue)}\n  next: ${_preview(newValue)}';
    AppLogger.d(_tag, msg);
    DebugLogStore.instance.addApp(AppLogEntry(
      tag: _tag,
      message: msg,
      level: AppLogLevel.debug,
      timestamp: DateTime.now(),
    ));
  }

  @override
  void providerDidFail(
    ProviderBase<Object?> provider,
    Object error,
    StackTrace stackTrace,
    ProviderContainer container,
  ) {
    final msg = 'FAIL  ${_name(provider)}: $error';
    AppLogger.e(_tag, msg, error: error, stackTrace: stackTrace);
    DebugLogStore.instance.addApp(AppLogEntry(
      tag: _tag,
      message: msg,
      level: AppLogLevel.error,
      timestamp: DateTime.now(),
    ));
  }

  @override
  void didDisposeProvider(
    ProviderBase<Object?> provider,
    ProviderContainer container,
  ) {
    AppLogger.d(_tag, 'DISPOSE ${_name(provider)}');
  }

  // ── helpers ───────────────────────────────────────────────────────────────

  static String _name(ProviderBase<Object?> p) =>
      p.name ?? p.runtimeType.toString();

  static String _preview(Object? value) {
    if (value == null) return 'null';
    final raw = value.toString();
    return raw.length > 120 ? '${raw.substring(0, 120)}…' : raw;
  }
}
