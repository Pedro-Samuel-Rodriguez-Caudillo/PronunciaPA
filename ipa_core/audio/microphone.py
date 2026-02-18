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


def record_with_vad(
    max_seconds: float = 10.0,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
    silence_timeout_ms: int = 1500,
    energy_threshold: float = 0.01,
    min_speech_ms: int = 200,
) -> Tuple[str, dict]:
    """Graba audio del micrófono con auto-stop tras silencio post-voz.

    Graba hasta ``max_seconds`` pero se detiene automáticamente cuando detecta
    ``silence_timeout_ms`` ms de silencio después de haber captado al menos
    ``min_speech_ms`` ms de voz.

    Parameters
    ----------
    max_seconds : float
        Duración máxima de grabación.
    sample_rate : int
        Frecuencia de muestreo (Hz).
    channels : int
        Número de canales.
    silence_timeout_ms : int
        Milisegundos de silencio continuo después de voz para detener.
    energy_threshold : float
        Umbral de energía relativa para detectar voz (0.0–1.0).
    min_speech_ms : int
        Ms mínimos de voz requeridos antes de aplicar el timeout de silencio.

    Returns
    -------
    tuple[str, dict]
        Ruta WAV temporal y metadatos de la grabación.
    """
    if max_seconds <= 0:
        raise ValidationError("La duración máxima debe ser positiva")

    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:  # pragma: no cover
        raise ValidationError("sounddevice/numpy requeridos para captura desde micrófono") from exc

    frame_ms = 30  # ms por frame de análisis
    frame_size = int(sample_rate * frame_ms / 1000)
    max_frames = int(max_seconds * 1000 / frame_ms)
    silence_frames_threshold = int(silence_timeout_ms / frame_ms)
    min_speech_frames = int(min_speech_ms / frame_ms)

    all_samples: list = []
    speech_frames = 0
    silence_frames_after_speech = 0
    stopped_early = False
    max_energy_seen = 0.0

    for _ in range(max_frames):
        chunk = sd.rec(frame_size, samplerate=sample_rate, channels=channels, dtype="float32")
        sd.wait()
        all_samples.append(chunk)

        # Calcular energía RMS del frame
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        if rms > max_energy_seen:
            max_energy_seen = rms

        # Normalizar energía respecto al máximo visto
        norm_energy = rms / max_energy_seen if max_energy_seen > 1e-6 else 0.0
        is_voice = norm_energy > energy_threshold

        if is_voice:
            speech_frames += 1
            silence_frames_after_speech = 0
        elif speech_frames >= min_speech_frames:
            silence_frames_after_speech += 1
            if silence_frames_after_speech >= silence_frames_threshold:
                stopped_early = True
                break

    if not all_samples:
        raise ValidationError("No se capturó audio del micrófono")

    audio_array = np.concatenate(all_samples, axis=0)
    actual_duration = len(audio_array) / sample_rate
    samples_int16 = (audio_array * np.iinfo(np.int16).max).astype(np.int16)

    tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_mic_vad_", suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples_int16.tobytes())

    meta = {
        "sample_rate": sample_rate,
        "channels": channels,
        "duration": actual_duration,
        "max_seconds": max_seconds,
        "stopped_early": stopped_early,
        "speech_frames": speech_frames,
        "vad": True,
    }
    return tmp.name, meta
