import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'app_logger.dart';
import 'debug_log_store.dart';

const _tag = 'HTTP';

/// An [http.BaseClient] wrapper that, in debug mode, logs every request and
/// response to [AppLogger] (console) and [DebugLogStore] (overlay).
///
/// In release builds the wrapper is a transparent no-op passthrough.
class DebugHttpClient extends http.BaseClient {
  final http.Client _inner;

  DebugHttpClient([http.Client? inner]) : _inner = inner ?? http.Client();

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (!kDebugMode) return _inner.send(request);

    final sw = Stopwatch()..start();
    final method = request.method;
    final url = request.url.toString();

    // ── log request ───────────────────────────────────────────────────────
    AppLogger.d(_tag, '→ $method $url');
    String? requestInfo;
    if (request is http.Request) {
      final body = request.body;
      final preview =
          body.length > 300 ? '${body.substring(0, 300)}…' : body;
      requestInfo = 'body: $preview';
      AppLogger.d(_tag, '  $requestInfo');
    } else if (request is http.MultipartRequest) {
      final fields = request.fields.toString();
      final files = request.files
          .map((f) => '${f.field}=${f.filename ?? "?"} (${f.length}B)')
          .join(', ');
      requestInfo = 'fields=$fields  files=[$files]';
      AppLogger.d(_tag, '  fields: $fields');
      AppLogger.d(_tag, '  files:  $files');
    }

    // ── execute and buffer ────────────────────────────────────────────────
    try {
      final streamed = await _inner.send(request);
      sw.stop();

      // Buffer the body so we can inspect it AND still return it.
      final bytes = await streamed.stream.toBytes();
      final bodyStr = String.fromCharCodes(bytes);
      final preview =
          bodyStr.length > 500 ? '${bodyStr.substring(0, 500)}…' : bodyStr;

      AppLogger.d(_tag,
          '← ${streamed.statusCode} $url  (${sw.elapsedMilliseconds}ms)');
      AppLogger.d(_tag, '  $preview');

      DebugLogStore.instance.addHttp(HttpLogEntry(
        method: method,
        url: url,
        statusCode: streamed.statusCode,
        durationMs: sw.elapsedMilliseconds,
        requestInfo: requestInfo,
        responseBody: preview,
        timestamp: DateTime.now(),
      ));

      // Re-wrap the buffered bytes into a new StreamedResponse.
      return http.StreamedResponse(
        Stream.value(bytes),
        streamed.statusCode,
        headers: streamed.headers,
        reasonPhrase: streamed.reasonPhrase,
        contentLength: bytes.length,
        isRedirect: streamed.isRedirect,
        persistentConnection: streamed.persistentConnection,
        request: streamed.request,
      );
    } catch (e, st) {
      sw.stop();
      AppLogger.e(
        _tag,
        '✗ $method $url failed after ${sw.elapsedMilliseconds}ms: $e',
        error: e,
        stackTrace: st,
      );

      DebugLogStore.instance.addHttp(HttpLogEntry(
        method: method,
        url: url,
        durationMs: sw.elapsedMilliseconds,
        error: e.toString(),
        timestamp: DateTime.now(),
      ));

      rethrow;
    }
  }

  @override
  void close() => _inner.close();
}
