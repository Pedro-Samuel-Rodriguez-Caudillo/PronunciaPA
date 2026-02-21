import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import '../../core/debug/app_logger.dart';
import '../../core/debug/audio_debug_utils.dart';

const _tag = 'Recorder';

class RecorderState {
  final bool isRecording;
  final String? lastPath;

  RecorderState({this.isRecording = false, this.lastPath});

  RecorderState copyWith({bool? isRecording, String? lastPath}) {
    return RecorderState(
      isRecording: isRecording ?? this.isRecording,
      lastPath: lastPath ?? this.lastPath,
    );
  }
}

const _kMinRecordingMs = 1200; // mínimo 1.2 s para capturar todas las sílabas

class RecorderNotifier extends StateNotifier<RecorderState> {
  final _audioRecorder = AudioRecorder();
  DateTime? _recordingStart;

  RecorderNotifier() : super(RecorderState());

  Future<void> startRecording() async {
    try {
      if (await _audioRecorder.hasPermission()) {
        final directory = await getTemporaryDirectory();
        final path = p.join(directory.path, 'recording_${DateTime.now().millisecondsSinceEpoch}.wav');

        const config = RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        );

        await _audioRecorder.start(config, path: path);
        _recordingStart = DateTime.now();
        AppLogger.d(_tag, 'Started recording at: $path');
        state = state.copyWith(isRecording: true);
      }
    } catch (e) {
      AppLogger.e(_tag, 'Error starting recording: $e', error: e);
    }
  }

  Future<String?> stopRecording() async {
    try {
      // Enforce minimum recording duration so short taps don't cut off phonemes.
      if (_recordingStart != null) {
        final elapsed = DateTime.now().difference(_recordingStart!).inMilliseconds;
        if (elapsed < _kMinRecordingMs) {
          final remaining = _kMinRecordingMs - elapsed;
          AppLogger.d(_tag, 'Waiting ${remaining}ms to reach minimum recording duration');
          await Future.delayed(Duration(milliseconds: remaining));
        }
      }
      final path = await _audioRecorder.stop();
      _recordingStart = null;
      state = state.copyWith(isRecording: false, lastPath: path);
      if (kDebugMode) await AudioDebugUtils.inspect(path);
      return path;
    } catch (e, st) {
      AppLogger.e(_tag, 'Error stopping recording: $e', error: e, stackTrace: st);
      _recordingStart = null;
      state = state.copyWith(isRecording: false);
      return null;
    }
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    super.dispose();
  }
}

final recorderProvider = StateNotifierProvider<RecorderNotifier, RecorderState>((ref) {
  return RecorderNotifier();
});
