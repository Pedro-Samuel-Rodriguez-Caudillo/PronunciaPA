import 'package:flutter/material.dart';

import '../../core/audio/audio_playback_controller.dart';
import '../../core/audio/audio_playback_support.dart';

/// Button widget that plays audio from a URL.
/// Pass [voice] to append `?voice=<id>` to TTS endpoint URLs.
class AudioPlayerButton extends StatefulWidget {
  final String? audioUrl;
  final String baseUrl;
  final String? voice;
  final IconData playIcon;
  final IconData loadingIcon;
  final double iconSize;

  const AudioPlayerButton({
    super.key,
    this.audioUrl,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.voice,
    this.playIcon = Icons.volume_up,
    this.loadingIcon = Icons.hourglass_empty,
    this.iconSize = 24.0,
  });

  @override
  State<AudioPlayerButton> createState() => _AudioPlayerButtonState();
}

class _AudioPlayerButtonState extends State<AudioPlayerButton> {
  late final AudioPlaybackController _audioPlayer;

  @override
  void initState() {
    super.initState();
    _audioPlayer = AudioPlaybackController();
    _audioPlayer.addListener(() {
      if (mounted) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }

  Future<void> _playAudio() async {
    if (widget.audioUrl == null) return;

    if (!_audioPlayer.isSupported) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(unsupportedAudioPlaybackMessage),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    try {
      final playbackState = _audioPlayer.state;

      // Stop if already playing
      if (playbackState.isPlaying) {
        await _audioPlayer.stop();
        return;
      }

      // Build full URL, appending voice param for TTS endpoints if selected.
      String fullUrl = widget.audioUrl!.startsWith('http')
          ? widget.audioUrl!
          : '${widget.baseUrl}${widget.audioUrl}';
      if (widget.voice != null && fullUrl.contains('/api/tts/speak')) {
        final separator = fullUrl.contains('?') ? '&' : '?';
        fullUrl = '$fullUrl${separator}voice=${Uri.encodeQueryComponent(widget.voice!)}';
      }

      // Play audio from URL
      await _audioPlayer.playUrl(fullUrl);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error al reproducir audio: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.audioUrl == null) {
      return const SizedBox.shrink();
    }

    final playbackState = _audioPlayer.state;
    final isLoading = playbackState.isLoading;
    final isPlaying = playbackState.isPlaying;
    final supportsPlayback = _audioPlayer.isSupported;

    return IconButton(
      icon: isLoading
          ? SizedBox(
              width: widget.iconSize,
              height: widget.iconSize,
              child: const CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(
              isPlaying ? Icons.stop : widget.playIcon,
              size: widget.iconSize,
              color: supportsPlayback ? null : Colors.grey,
            ),
      onPressed: isLoading ? null : _playAudio,
      tooltip: supportsPlayback
          ? (isPlaying ? 'Detener audio' : 'Reproducir audio')
          : unsupportedAudioPlaybackMessage,
    );
  }
}
