"""Captura de audio desde micrófono."""
from __future__ import annotations

import tempfile
from typing import Tuple

import wave

from ipa_core.errors import ValidationError


def record(seconds: float = 3.0, *, sample_rate: int = 16000, channels: int = 1) -> Tuple[str, dict]:
    """Graba audio del micro y devuelve ruta WAV y metadatos."""
    if seconds <= 0:
        raise ValidationError("La duración de grabación debe ser positiva")

    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:  # pragma: no cover
        raise ValidationError("sounddevice/numpy requeridos para captura desde micrófono") from exc

    frames = int(sample_rate * seconds)
    audio = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype="float32")
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_mic_", suffix=".wav", delete=False)
    samples = (audio * np.iinfo(np.int16).max).astype(np.int16)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    return tmp.name, {"sample_rate": sample_rate, "channels": channels, "duration": seconds}
