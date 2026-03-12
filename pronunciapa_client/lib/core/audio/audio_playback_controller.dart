import 'dart:async';

import 'package:audioplayers/audioplayers.dart' as ap;
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:just_audio/just_audio.dart' as ja;

import 'audio_playback_support.dart';

enum AudioPlaybackStatus {
  idle,
  loading,
  playing,
  completed,
  unsupported,
  error,
}

class AudioPlaybackState {
  const AudioPlaybackState({
    required this.status,
    this.errorMessage,
  });

  final AudioPlaybackStatus status;
  final String? errorMessage;

  bool get isLoading => status == AudioPlaybackStatus.loading;
  bool get isPlaying => status == AudioPlaybackStatus.playing;
  bool get isCompleted => status == AudioPlaybackStatus.completed;

  AudioPlaybackState copyWith({
    AudioPlaybackStatus? status,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AudioPlaybackState(
      status: status ?? this.status,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  static const idle = AudioPlaybackState(status: AudioPlaybackStatus.idle);
  static const unsupported = AudioPlaybackState(
    status: AudioPlaybackStatus.unsupported,
    errorMessage: unsupportedAudioPlaybackMessage,
  );
}

class AudioPlaybackController extends ChangeNotifier {
  AudioPlaybackController() {
    if (!supportsAudioPlayback) {
      _state = AudioPlaybackState.unsupported;
      return;
    }

    if (supportsDesktopAudioPlayback) {
      _desktopPlayer = ap.AudioPlayer();
      _desktopStateSubscription =
          _desktopPlayer!.onPlayerStateChanged.listen(_handleDesktopStateChanged);
      _desktopCompleteSubscription =
          _desktopPlayer!.onPlayerComplete.listen((_) {
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.completed));
      });
      return;
    }

    final player = ja.AudioPlayer();
    _justAudioPlayer = player;
    _justAudioSubscription = player.playerStateStream.listen((playerState) {
      if (playerState.processingState == ja.ProcessingState.loading ||
          playerState.processingState == ja.ProcessingState.buffering) {
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.loading));
        return;
      }

      if (playerState.processingState == ja.ProcessingState.completed) {
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.completed));
        return;
      }

      if (playerState.playing) {
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.playing));
      } else {
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.idle));
      }
    });
  }

  ja.AudioPlayer? _justAudioPlayer;
  ap.AudioPlayer? _desktopPlayer;
  StreamSubscription<ja.PlayerState>? _justAudioSubscription;
  StreamSubscription<ap.PlayerState>? _desktopStateSubscription;
  StreamSubscription<void>? _desktopCompleteSubscription;
  AudioPlaybackState _state = AudioPlaybackState.idle;

  AudioPlaybackState get state => _state;
  bool get isSupported => supportsAudioPlayback;

  Future<void> playUrl(String url) async {
    if (!isSupported) {
      _setState(AudioPlaybackState.unsupported);
      return;
    }

    _setState(const AudioPlaybackState(status: AudioPlaybackStatus.loading));
    try {
      if (supportsDesktopAudioPlayback) {
        final player = _desktopPlayer!;
        await player.stop();
        await player.play(ap.UrlSource(url));
        return;
      }

      final player = _justAudioPlayer!;
      await player.stop();
      await player.setUrl(url);
      await player.play();
    } on MissingPluginException {
      _setError(unsupportedAudioPlaybackMessage);
    } catch (error) {
      _setError(error.toString());
    }
  }

  Future<void> playFile(String path) async {
    if (!isSupported) {
      _setState(AudioPlaybackState.unsupported);
      return;
    }

    _setState(const AudioPlaybackState(status: AudioPlaybackStatus.loading));
    try {
      if (supportsDesktopAudioPlayback) {
        final player = _desktopPlayer!;
        await player.stop();
        await player.play(ap.DeviceFileSource(path));
        return;
      }

      final player = _justAudioPlayer!;
      await player.stop();
      await player.setFilePath(path);
      await player.play();
    } on MissingPluginException {
      _setError(unsupportedAudioPlaybackMessage);
    } catch (error) {
      _setError(error.toString());
    }
  }

  Future<void> stop() async {
    if (!isSupported) {
      return;
    }

    if (supportsDesktopAudioPlayback) {
      await _desktopPlayer?.stop();
    } else {
      await _justAudioPlayer?.stop();
    }
    _setState(const AudioPlaybackState(status: AudioPlaybackStatus.idle));
  }

  void _handleDesktopStateChanged(ap.PlayerState playerState) {
    switch (playerState) {
      case ap.PlayerState.playing:
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.playing));
        break;
      case ap.PlayerState.stopped:
      case ap.PlayerState.paused:
      case ap.PlayerState.disposed:
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.idle));
        break;
      case ap.PlayerState.completed:
        _setState(const AudioPlaybackState(status: AudioPlaybackStatus.completed));
        break;
    }
  }

  void _setError(String message) {
    _setState(AudioPlaybackState(
      status: AudioPlaybackStatus.error,
      errorMessage: message,
    ));
  }

  void _setState(AudioPlaybackState nextState) {
    _state = nextState;
    notifyListeners();
  }

  @override
  void dispose() {
    unawaited(_justAudioSubscription?.cancel());
    unawaited(_desktopStateSubscription?.cancel());
    unawaited(_desktopCompleteSubscription?.cancel());
    unawaited(_justAudioPlayer?.dispose());
    unawaited(_desktopPlayer?.dispose());
    super.dispose();
  }
}