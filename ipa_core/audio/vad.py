"""Voice Activity Detection (VAD) - Detección de actividad de voz.

Implementación ligera de VAD basada en energía para recortar silencios.
No requiere dependencias externas pesadas (webrtcvad es opcional).

Pasos del pipeline según ipa_core/TODO.md:
- Paso 5: VAD y segmentación
  - Recorte de silencios inicio/final
  - Detección de pausas internas
  - Cálculo de ratio voz/silencio
"""
from __future__ import annotations

import logging
import warnings
import wave
from dataclasses import dataclass, field
from pathlib import Path
import threading
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Constantes por defecto
DEFAULT_FRAME_MS = 30  # Tamaño de frame en milisegundos
DEFAULT_ENERGY_THRESHOLD = 0.005  # Umbral de energía relativa (bajado de 0.01 para capturar consonantes sordas)
DEFAULT_MIN_SPEECH_MS = 100  # Mínimo de speech para considerar válido
DEFAULT_SILENCE_TRIM_MS = 500  # Silencio mínimo para recortar al inicio/final
                               # (500 ms: evita cortar hesitaciones naturales antes de hablar)
_PRE_SPEECH_MARGIN_MS = 400   # Margen antes de primer segmento de voz — cubre clusters /pɾ/, /tr/, /kl/
_POST_SPEECH_MARGIN_MS = 200  # Margen después del último segmento de voz


@dataclass
class VADResult:
    """Resultado del análisis VAD."""
    
    # Timestamps de segmentos de voz [(start_ms, end_ms), ...]
    speech_segments: List[Tuple[int, int]]
    
    # Ratio de voz vs silencio (0.0 a 1.0)
    speech_ratio: float
    
    # Duración total del audio en ms
    duration_ms: int
    
    # Timestamps sugeridos para recorte (start_ms, end_ms)
    trim_suggestion: Optional[Tuple[int, int]] = None
    
    # Silencios internos detectados (pausas)
    internal_pauses: List[Tuple[int, int]] = field(default_factory=list)

    
def analyze_vad(
    audio_path: str,
    *,
    frame_ms: int = DEFAULT_FRAME_MS,
    energy_threshold: float = DEFAULT_ENERGY_THRESHOLD,
    min_speech_ms: int = DEFAULT_MIN_SPEECH_MS,
    silence_trim_ms: int = DEFAULT_SILENCE_TRIM_MS,
) -> VADResult:
    """Analizar audio para detectar segmentos de voz."""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")
    
    raw_data, sr, sw, nc, n_frames = _read_wav_raw(path)
    duration_ms = int(n_frames * 1000 / sr)
    
    frame_energies = _calculate_frame_energies(raw_data, sr, sw, nc, frame_ms)
    if not frame_energies or max(frame_energies) < 100.0:
        return VADResult(speech_segments=[], speech_ratio=0.0, duration_ms=duration_ms)
    
    segments = _detect_speech_segments(frame_energies, frame_ms, energy_threshold, min_speech_ms)
    return _build_vad_result(segments, duration_ms, silence_trim_ms)


def _read_wav_raw(path: Path) -> tuple[bytes, int, int, int, int]:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        sw = w.getsampwidth()
        nc = w.getnchannels()
        nf = w.getnframes()
        data = w.readframes(nf)
    
    if sw != 2:
        raise ValueError(f"Solo soporta WAV 16-bit, recibido: {sw * 8}-bit")
    return data, sr, sw, nc, nf


def _detect_speech_segments(energies: list[float], frame_ms: int, threshold: float, min_ms: int) -> list[tuple[int, int]]:
    max_e = max(energies)
    is_speech = [e / max_e > threshold for e in energies]
    segments = _extract_segments(is_speech, frame_ms)
    return [s for s in segments if s[1] - s[0] >= min_ms]


def _calculate_frame_energies(raw_data: bytes, sr: int, sw: int, nc: int, frame_ms: int) -> list[float]:
    samples_per_frame = int(sr * frame_ms / 1000)
    bytes_per_frame = samples_per_frame * sw * nc
    
    energies = []
    for i in range(0, len(raw_data) - bytes_per_frame, bytes_per_frame):
        frame = raw_data[i:i + bytes_per_frame]
        energies.append(_compute_frame_energy(frame, sw))
    return energies


def _build_vad_result(segments: list[tuple[int, int]], duration_ms: int, trim_ms: int) -> VADResult:
    total_speech_ms = sum(end - start for start, end in segments)
    speech_ratio = total_speech_ms / duration_ms if duration_ms > 0 else 0.0
    
    return VADResult(
        speech_segments=segments,
        speech_ratio=speech_ratio,
        duration_ms=duration_ms,
        trim_suggestion=_calculate_trim_suggestion(segments, duration_ms, trim_ms),
        internal_pauses=_detect_internal_pauses(segments),
    )


def _calculate_trim_suggestion(segments: list[tuple[int, int]], duration: int, trim_ms: int) -> Optional[tuple[int, int]]:
    if not segments:
        return None
    
    first_start, last_end = segments[0][0], segments[-1][1]
    if first_start <= trim_ms and (duration - last_end) <= trim_ms:
        return None
        
    return (
        max(0, first_start - _PRE_SPEECH_MARGIN_MS),
        min(duration, last_end + _POST_SPEECH_MARGIN_MS)
    )


def _detect_internal_pauses(segments: list[tuple[int, int]]) -> list[tuple[int, int]]:
    pauses = []
    for i in range(1, len(segments)):
        prev_end, curr_start = segments[i - 1][1], segments[i][0]
        if curr_start - prev_end > 200:
            pauses.append((prev_end, curr_start))
    return pauses


def _compute_frame_energy(frame: bytes, sample_width: int) -> float:
    """Calcular energía RMS de un frame de audio."""
    import struct
    
    if sample_width == 2:
        fmt = f"<{len(frame) // 2}h"
        samples = struct.unpack(fmt, frame)
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        return (sum_sq / len(samples)) ** 0.5
    return 0.0


def _extract_segments(
    is_speech: List[bool],
    frame_ms: int,
) -> List[Tuple[int, int]]:
    """Extraer segmentos continuos de speech."""
    segments = []
    in_segment = False
    start_frame = 0
    
    for i, speech in enumerate(is_speech):
        in_segment, start_frame = _process_segment_frame(
            i, speech, in_segment, start_frame, frame_ms, segments
        )
    
    if in_segment:
        segments.append((start_frame * frame_ms, len(is_speech) * frame_ms))
    
    return segments


def _process_segment_frame(i: int, speech: bool, in_seg: bool, start: int, ms: int, res: list) -> tuple[bool, int]:
    if speech and not in_seg:
        return True, i
    if not speech and in_seg:
        res.append((start * ms, i * ms))
        return False, start
    return in_seg, start


def _read_audio_wav(audio_path: str, sampling_rate: int = 16000) -> Any:
    """Leer WAV como tensor float32 sin depender de torchaudio."""
    import numpy as np
    import torch

    raw, sr, sw, nc = _read_wav_metadata(audio_path)
    samples = _raw_to_float32(raw, sw)

    if nc > 1:
        samples = samples.reshape(-1, nc).mean(axis=1).astype(np.float32)

    if sr != sampling_rate:
        samples = _resample_audio(samples, sr, sampling_rate)

    return torch.from_numpy(samples)


def _read_wav_metadata(path: str) -> tuple[bytes, int, int, int]:
    with wave.open(path, "rb") as wf:
        return wf.readframes(wf.getnframes()), wf.getframerate(), wf.getsampwidth(), wf.getnchannels()


def _raw_to_float32(raw: bytes, sw: int) -> Any:
    import numpy as np
    if sw == 2:
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if sw == 4:
        return np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2_147_483_648.0
    raise ValueError(f"Sample width {sw * 8}-bit no soportado")


def _resample_audio(samples: Any, sr: int, target_sr: int) -> Any:
    import numpy as np
    try:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(target_sr, sr)
        return resample_poly(samples, target_sr // g, sr // g).astype(np.float32)
    except ImportError:
        logger.warning("scipy no disponible para resamplear %d→%d Hz", sr, target_sr)
        return samples

_SILERO_MODEL_LOCK = threading.Lock()
_SILERO_MODEL: Optional[Any] = None
_SILERO_AVAILABLE: Optional[bool] = None  # None = no comprobado aún


def _load_silero_vad_model() -> Any:
    """Cargar Silero VAD suprimiendo solo la deprecación transitoria de torch del proveedor."""
    from silero_vad import load_silero_vad

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"`torch\.jit\.load` is deprecated\. Please switch to `torch\.export`\.",
            category=DeprecationWarning,
        )
        return load_silero_vad()


def _get_silero_model() -> Any:
    """Obtener (o cargar) el modelo Silero VAD (singleton thread-safe)."""
    global _SILERO_MODEL, _SILERO_AVAILABLE
    if _SILERO_AVAILABLE is False:
        raise ImportError("silero-vad no está disponible")
    with _SILERO_MODEL_LOCK:
        if _SILERO_MODEL is None:
            try:
                _SILERO_MODEL = _load_silero_vad_model()
                _SILERO_AVAILABLE = True
                logger.info("Silero VAD model cargado")
            except ImportError:
                _SILERO_AVAILABLE = False
                raise ImportError(
                    "silero-vad no instalado. "
                    "Instálalo con: pip install 'pronunciapa[vad]'"
                )
        return _SILERO_MODEL


def analyze_vad_silero(
    audio_path: str,
    *,
    sampling_rate: int = 16000,
    threshold: float = 0.5,
    min_speech_duration_ms: int = 100,
    min_silence_duration_ms: int = 100,
    silence_trim_ms: int = DEFAULT_SILENCE_TRIM_MS,
) -> VADResult:
    """Analizar audio usando Silero VAD (modelo neural)."""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")

    from silero_vad import get_speech_timestamps

    model = _get_silero_model()
    wav = _read_audio_wav(str(path), sampling_rate=sampling_rate)
    duration_ms = int(len(wav) * 1000 / sampling_rate)

    timestamps = get_speech_timestamps(
        wav, model, sampling_rate=sampling_rate, threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
        return_seconds=False,
    )

    def _to_ms(samples: int) -> int:
        return int(samples * 1000 / sampling_rate)

    segments = [(_to_ms(ts["start"]), _to_ms(ts["end"])) for ts in timestamps]
    
    logger.debug("Silero VAD: %d segmentos, threshold=%.2f", len(segments), threshold)
    return _build_vad_result(segments, duration_ms, silence_trim_ms)


_SILERO_KWARGS = frozenset({
    "sampling_rate", "threshold", "min_speech_duration_ms",
    "min_silence_duration_ms", "silence_trim_ms",
})
_ENERGY_KWARGS = frozenset({"frame_ms", "energy_threshold", "min_speech_ms", "silence_trim_ms"})


def analyze_vad_best(
    audio_path: str,
    *,
    backend: str = "auto",
    **kwargs: Any,
) -> VADResult:
    """Seleccionar automáticamente el mejor backend VAD disponible."""
    if backend == "energy":
        return analyze_vad(audio_path, **_filter_kwargs(kwargs, _ENERGY_KWARGS))
    if backend == "silero":
        return analyze_vad_silero(audio_path, **_filter_kwargs(kwargs, _SILERO_KWARGS))
    
    return _dispatch_auto_vad(audio_path, **kwargs)


def _filter_kwargs(kwargs: dict, allowed: frozenset) -> dict:
    return {k: v for k, v in kwargs.items() if k in allowed}


def _dispatch_auto_vad(audio_path: str, **kwargs) -> VADResult:
    try:
        res = analyze_vad_silero(audio_path, **_filter_kwargs(kwargs, _SILERO_KWARGS))
        logger.debug("analyze_vad_best: usando Silero VAD")
        return res
    except ImportError:
        logger.debug("analyze_vad_best: Silero no disponible, usando VAD de energía")
        return analyze_vad(audio_path, **_filter_kwargs(kwargs, _ENERGY_KWARGS))


__all__ = ["VADResult", "analyze_vad", "analyze_vad_silero", "analyze_vad_best"]
