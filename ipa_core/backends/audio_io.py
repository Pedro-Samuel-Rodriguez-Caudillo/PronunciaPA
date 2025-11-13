"""Utilidades mínimas de I/O de audio para el MVP.

Solo WAV (PCM) soporte inicial:
- Lee sample rate y canales usando `wave` del stdlib.
- Emite `UnsupportedFormat` en otros formatos.
"""
from __future__ import annotations

import os
import wave
from dataclasses import dataclass

from ipa_core.errors import FileNotFound, UnsupportedFormat
from ipa_core.types import AudioInput


@dataclass(frozen=True)
class WavInfo:
    path: str
    sample_rate: int
    channels: int


def sniff_wav(path: str) -> WavInfo:
    """Leer metadatos básicos de un WAV.

    Lanza:
    - FileNotFound si no existe.
    - UnsupportedFormat si no es WAV PCM válido.
    """
    if not os.path.exists(path):
        raise FileNotFound(f"Audio no encontrado: {path}")
    try:
        with wave.open(path, "rb") as w:
            sr = w.getframerate()
            ch = w.getnchannels()
            return WavInfo(path=path, sample_rate=sr, channels=ch)
    except wave.Error as e:  # type: ignore[no-redef]
        raise UnsupportedFormat(f"Formato no soportado o WAV inválido: {path}") from e


def to_audio_input(path: str) -> AudioInput:
    """Construir `AudioInput` desde un WAV PCM."""
    info = sniff_wav(path)
    return {"path": info.path, "sample_rate": info.sample_rate, "channels": info.channels}
