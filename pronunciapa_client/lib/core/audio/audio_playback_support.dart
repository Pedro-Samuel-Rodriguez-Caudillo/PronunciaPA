import 'package:flutter/foundation.dart';

bool get supportsJustAudioPlayback {
  if (kIsWeb) {
    return true;
  }

  switch (defaultTargetPlatform) {
    case TargetPlatform.android:
    case TargetPlatform.iOS:
    case TargetPlatform.macOS:
      return true;
    case TargetPlatform.fuchsia:
      return false;
    case TargetPlatform.linux:
    case TargetPlatform.windows:
      return false;
  }
}

bool get supportsDesktopAudioPlayback {
  if (kIsWeb) {
    return false;
  }

  switch (defaultTargetPlatform) {
    case TargetPlatform.linux:
    case TargetPlatform.windows:
      return true;
    case TargetPlatform.android:
    case TargetPlatform.iOS:
    case TargetPlatform.macOS:
    case TargetPlatform.fuchsia:
      return false;
  }
}

bool get supportsAudioPlayback =>
    supportsJustAudioPlayback || supportsDesktopAudioPlayback;

const String unsupportedAudioPlaybackMessage =
    'La reproduccion de audio no esta disponible en esta plataforma.';