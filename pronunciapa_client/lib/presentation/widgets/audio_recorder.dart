import 'package:flutter/material.dart';

/// Web audio recorder widget using MediaRecorder API (web only)
class AudioRecorder extends StatefulWidget {
  final Function(String audioPath) onRecordingComplete;
  final Function(String error)? onError;

  const AudioRecorder({
    Key? key,
    required this.onRecordingComplete,
    this.onError,
  }) : super(key: key);

  @override
  State<AudioRecorder> createState() => _AudioRecorderState();
}

class _AudioRecorderState extends State<AudioRecorder> {
  bool _isRecording = false;
  bool _isProcessing = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text(
              _error!,
              style: const TextStyle(color: Colors.red),
            ),
          ),
        ElevatedButton.icon(
          onPressed: _isProcessing
              ? null
              : (_isRecording ? _stopRecording : _startRecording),
          icon: Icon(_isRecording ? Icons.stop : Icons.mic),
          label: Text(_isRecording ? 'Detener grabación' : 'Grabar audio'),
          style: ElevatedButton.styleFrom(
            backgroundColor: _isRecording ? Colors.red : Colors.blue,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          ),
        ),
        if (_isRecording)
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: Text('Grabando...', style: TextStyle(color: Colors.red)),
          ),
        if (_isProcessing)
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: CircularProgressIndicator(),
          ),
      ],
    );
  }

  Future<void> _startRecording() async {
    setState(() {
      _isRecording = true;
      _error = null;
    });
    
    // Note: Actual MediaRecorder implementation would go here
    // For Flutter mobile, use the 'record' package (already in dependencies)
    // This is a placeholder that should be replaced with platform-specific code
  }

  Future<void> _stopRecording() async {
    setState(() {
      _isRecording = false;
      _isProcessing = true;
    });

    try {
      // Note: Get the recorded audio file path here
      // For now, this is a placeholder
      final audioPath = '/path/to/recorded/audio.wav';
      widget.onRecordingComplete(audioPath);
    } catch (e) {
      setState(() {
        _error = 'Error al procesar grabación: $e';
      });
      widget.onError?.call(e.toString());
    } finally {
      setState(() {
        _isProcessing = false;
      });
    }
  }
}
