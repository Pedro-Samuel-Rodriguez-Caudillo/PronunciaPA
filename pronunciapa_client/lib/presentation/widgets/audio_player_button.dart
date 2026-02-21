import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';

/// Button widget that plays audio from a URL
class AudioPlayerButton extends StatefulWidget {
  final String? audioUrl;
  final String baseUrl;
  final IconData playIcon;
  final IconData loadingIcon;
  final double iconSize;

  const AudioPlayerButton({
    super.key,
    this.audioUrl,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.playIcon = Icons.volume_up,
    this.loadingIcon = Icons.hourglass_empty,
    this.iconSize = 24.0,
  });

  @override
  State<AudioPlayerButton> createState() => _AudioPlayerButtonState();
}

class _AudioPlayerButtonState extends State<AudioPlayerButton> {
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isPlaying = false;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    
    // Listen to player state changes
    _audioPlayer.onPlayerStateChanged.listen((state) {
      if (mounted) {
        setState(() {
          _isPlaying = state == PlayerState.playing;
          _isLoading = false;
        });
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

    try {
      setState(() {
        _isLoading = true;
      });

      // Stop if already playing
      if (_isPlaying) {
        await _audioPlayer.stop();
        setState(() {
          _isPlaying = false;
          _isLoading = false;
        });
        return;
      }

      // Build full URL
      final fullUrl = widget.audioUrl!.startsWith('http')
          ? widget.audioUrl!
          : '${widget.baseUrl}${widget.audioUrl}';

      // Play audio from URL
      await _audioPlayer.play(UrlSource(fullUrl));

    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isPlaying = false;
        });
        
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

    return IconButton(
      icon: _isLoading
          ? SizedBox(
              width: widget.iconSize,
              height: widget.iconSize,
              child: const CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(
              _isPlaying ? Icons.stop : widget.playIcon,
              size: widget.iconSize,
            ),
      onPressed: _isLoading ? null : _playAudio,
      tooltip: _isPlaying ? 'Detener audio' : 'Reproducir audio',
    );
  }
}
