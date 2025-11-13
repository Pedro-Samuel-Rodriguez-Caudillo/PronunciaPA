"""Helpers para generar archivos WAV en pruebas."""
from __future__ import annotations

import math
import wave
from pathlib import Path


def write_sine_wave(path: str | Path, seconds: float = 0.2, sample_rate: int = 16000) -> str:
    """Genera un archivo WAV mono con una onda senoidal simple."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * seconds)
    amplitude = 0.2

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(frames):
            value = int(amplitude * 32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            wf.writeframes(value.to_bytes(2, "little", signed=True))
    return str(path)
