import 'dart:io';
import 'dart:typed_data';

import 'app_logger.dart';
import 'debug_log_store.dart';

const _tag = 'Audio';

/// Utilities for inspecting recorded WAV files before they are uploaded.
///
/// Call [AudioDebugUtils.inspect] immediately after `stopRecording()` resolves,
/// inside a `if (kDebugMode)` guard (already done in [RecorderNotifier]).
class AudioDebugUtils {
  AudioDebugUtils._();

  /// Reads and logs the WAV header (first 44 bytes) of [wavFile] and emits a
  /// summary to the console + debug overlay.
  static Future<void> inspect(String? filePath) async {
    if (filePath == null) {
      AppLogger.w(_tag, 'inspect: filePath is null — nothing to inspect');
      return;
    }

    final file = File(filePath);
    if (!await file.exists()) {
      AppLogger.w(_tag, 'inspect: file does not exist: $filePath');
      return;
    }

    final size = await file.length();

    if (size < 44) {
      final msg = 'WAV too small (${size}B, need ≥44B) — recording may be truncated: $filePath';
      AppLogger.w(_tag, msg);
      _store(msg, AppLogLevel.warning);
      return;
    }

    final header = await _readBytes(file, 44);
    final parsed = _parseWavHeader(header);

    final msg = [
      'WAV  ${file.path.split(Platform.pathSeparator).last}',
      '  file size : ${size}B',
      '  riff id   : ${parsed.riffId}',
      '  audio fmt : ${parsed.audioFormat == 1 ? "PCM" : parsed.audioFormat.toString()}',
      '  channels  : ${parsed.numChannels}',
      '  sample rate: ${parsed.sampleRate} Hz',
      '  bit depth : ${parsed.bitsPerSample} bit',
      '  data chunk : ${parsed.dataChunkSize}B',
    ].join('\n');

    AppLogger.i(_tag, msg);
    _store(msg, AppLogLevel.info);
  }

  // ── private helpers ───────────────────────────────────────────────────────

  static void _store(String msg, AppLogLevel level) {
    DebugLogStore.instance.addApp(AppLogEntry(
      tag: _tag,
      message: msg,
      level: level,
      timestamp: DateTime.now(),
    ));
  }

  static Future<Uint8List> _readBytes(File file, int count) async {
    final raf = await file.open();
    try {
      return await raf.read(count);
    } finally {
      await raf.close();
    }
  }

  static _WavHeader _parseWavHeader(Uint8List h) {
    // WAV header layout (little-endian):
    // 0-3   ChunkID       "RIFF"
    // 4-7   ChunkSize     (file size - 8)
    // 8-11  Format        "WAVE"
    // 12-15 Subchunk1ID   "fmt "
    // 16-19 Subchunk1Size 16 for PCM
    // 20-21 AudioFormat   1 = PCM
    // 22-23 NumChannels
    // 24-27 SampleRate
    // 28-31 ByteRate
    // 32-33 BlockAlign
    // 34-35 BitsPerSample
    // 36-39 Subchunk2ID   "data"
    // 40-43 Subchunk2Size data chunk size in bytes
    final bd = h.buffer.asByteData();
    return _WavHeader(
      riffId: String.fromCharCodes(h.sublist(0, 4)),
      audioFormat: bd.getUint16(20, Endian.little),
      numChannels: bd.getUint16(22, Endian.little),
      sampleRate: bd.getUint32(24, Endian.little),
      bitsPerSample: bd.getUint16(34, Endian.little),
      dataChunkSize: bd.getUint32(40, Endian.little),
    );
  }
}

class _WavHeader {
  final String riffId;
  final int audioFormat;
  final int numChannels;
  final int sampleRate;
  final int bitsPerSample;
  final int dataChunkSize;

  const _WavHeader({
    required this.riffId,
    required this.audioFormat,
    required this.numChannels,
    required this.sampleRate,
    required this.bitsPerSample,
    required this.dataChunkSize,
  });
}
