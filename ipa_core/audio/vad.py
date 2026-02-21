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
import wave
from dataclasses import dataclass
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
    internal_pauses: List[Tuple[int, int]] = None
    
    def __post_init__(self):
        if self.internal_pauses is None:
            self.internal_pauses = []


def analyze_vad(
    audio_path: str,
    *,
    frame_ms: int = DEFAULT_FRAME_MS,
    energy_threshold: float = DEFAULT_ENERGY_THRESHOLD,
    min_speech_ms: int = DEFAULT_MIN_SPEECH_MS,
    silence_trim_ms: int = DEFAULT_SILENCE_TRIM_MS,
) -> VADResult:
    """Analizar audio para detectar segmentos de voz.
    
    Args:
        audio_path: Ruta al archivo WAV (16-bit PCM)
        frame_ms: Tamaño de frame en milisegundos
        energy_threshold: Umbral de energía relativa (0.0-1.0)
        min_speech_ms: Duración mínima de speech válido en ms
        silence_trim_ms: Silencio mínimo para sugerir recorte
        
    Returns:
        VADResult con segmentos de voz y métricas
    """
    p = Path(audio_path)
    if not p.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")
    
    # Leer audio WAV
    with wave.open(str(p), "rb") as w:
        sample_rate = w.getframerate()
        n_channels = w.getnchannels()
        sample_width = w.getsampwidth()
        n_frames = w.getnframes()
        raw_data = w.readframes(n_frames)
    
    if sample_width != 2:
        raise ValueError(f"Solo soporta WAV 16-bit, recibido: {sample_width * 8}-bit")
    
    # Calcular energía por frame
    samples_per_frame = int(sample_rate * frame_ms / 1000)
    bytes_per_frame = samples_per_frame * sample_width * n_channels
    
    frame_energies = []
    for i in range(0, len(raw_data) - bytes_per_frame, bytes_per_frame):
        frame = raw_data[i:i + bytes_per_frame]
        energy = _compute_frame_energy(frame, sample_width)
        frame_energies.append(energy)
    
    if not frame_energies:
        return VADResult(
            speech_segments=[],
            speech_ratio=0.0,
            duration_ms=int(n_frames * 1000 / sample_rate),
        )
    
    # Umbral absoluto de energía mínima (evita que silencio sea detectado como voz)
    # Para audio de 16-bit, RMS < 100 es efectivamente silencio
    ABSOLUTE_ENERGY_THRESHOLD = 100.0
    max_energy = max(frame_energies)
    
    # Si la energía máxima es muy baja, todo es silencio
    if max_energy < ABSOLUTE_ENERGY_THRESHOLD:
        return VADResult(
            speech_segments=[],
            speech_ratio=0.0,
            duration_ms=int(n_frames * 1000 / sample_rate),
        )
    
    # Normalizar energías y aplicar threshold
    normalized = [e / max_energy for e in frame_energies]
    is_speech = [e > energy_threshold for e in normalized]
    
    # Extraer segmentos de speech
    speech_segments = _extract_segments(is_speech, frame_ms)
    
    # Filtrar segmentos muy cortos
    speech_segments = [
        (start, end) for start, end in speech_segments
        if end - start >= min_speech_ms
    ]
    
    # Calcular métricas
    duration_ms = int(n_frames * 1000 / sample_rate)
    total_speech_ms = sum(end - start for start, end in speech_segments)
    speech_ratio = total_speech_ms / duration_ms if duration_ms > 0 else 0.0
    
    # Calcular sugerencia de recorte
    trim_suggestion = None
    if speech_segments:
        first_speech_start = speech_segments[0][0]
        last_speech_end = speech_segments[-1][1]
        
        # Sugerir recorte si hay silencio significativo al inicio o al final
        if first_speech_start > silence_trim_ms or (duration_ms - last_speech_end) > silence_trim_ms:
            # Margen generoso para no cortar consonantes iniciales sordas (/p/, /t/, /k/)
            # que tienen poca energía y pueden no ser detectadas como voz
            trim_start = max(0, first_speech_start - _PRE_SPEECH_MARGIN_MS)
            trim_end = min(duration_ms, last_speech_end + _POST_SPEECH_MARGIN_MS)
            trim_suggestion = (trim_start, trim_end)
    
    # Detectar pausas internas
    internal_pauses = []
    for i in range(1, len(speech_segments)):
        prev_end = speech_segments[i - 1][1]
        curr_start = speech_segments[i][0]
        pause_duration = curr_start - prev_end
        if pause_duration > 200:  # Pausa > 200ms
            internal_pauses.append((prev_end, curr_start))
    
    return VADResult(
        speech_segments=speech_segments,
        speech_ratio=speech_ratio,
        duration_ms=duration_ms,
        trim_suggestion=trim_suggestion,
        internal_pauses=internal_pauses,
    )


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
        if speech and not in_segment:
            in_segment = True
            start_frame = i
        elif not speech and in_segment:
            in_segment = False
            segments.append((start_frame * frame_ms, i * frame_ms))
    
    # Cerrar último segmento si quedó abierto
    if in_segment:
        segments.append((start_frame * frame_ms, len(is_speech) * frame_ms))
    
    return segments


# ──────────────────────────────────────────────────────────────────────────────
# Silero VAD backend (opcional, requiere `pip install silero-vad`)
# ──────────────────────────────────────────────────────────────────────────────

_SILERO_MODEL_LOCK = threading.Lock()
_SILERO_MODEL: Optional[Any] = None
_SILERO_AVAILABLE: Optional[bool] = None  # None = no comprobado aún


def _get_silero_model() -> Any:
    """Obtener (o cargar) el modelo Silero VAD (singleton thread-safe)."""
    global _SILERO_MODEL, _SILERO_AVAILABLE
    if _SILERO_AVAILABLE is False:
        raise ImportError("silero-vad no está disponible")
    with _SILERO_MODEL_LOCK:
        if _SILERO_MODEL is None:
            try:
                from silero_vad import load_silero_vad
                _SILERO_MODEL = load_silero_vad()
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
    """Analizar audio usando Silero VAD (modelo neural).

    Más robusto que el VAD basado en energía: no le afectan variaciones de
    amplitud, ruido de fondo ni consonantes sordas iniciales (/p/, /t/, /k/).
    El modelo es determinista para la misma entrada de audio, lo que garantiza
    **salidas consistentes** en evaluaciones repetidas.

    Requiere ``pip install 'pronunciapa[vad]'`` (instala silero-vad y torch).

    Args:
        audio_path: Ruta al archivo WAV (cualquier SR; se muestrea a 16 kHz).
        sampling_rate: Rate interno de Silero (debe ser 16000).
        threshold: Probabilidad mínima para considerar voz (0.0–1.0).
        min_speech_duration_ms: Duración mínima de segmento de voz en ms.
        min_silence_duration_ms: Silencio mínimo entre segmentos en ms.
        silence_trim_ms: Silencio mínimo al inicio/final para sugerir recorte.

    Returns:
        :class:`VADResult` compatible con :func:`analyze_vad`.

    Raises:
        ImportError: Si silero-vad/torch no están instalados.
        FileNotFoundError: Si audio_path no existe.
    """
    p = Path(audio_path)
    if not p.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")

    from silero_vad import get_speech_timestamps, read_audio

    model = _get_silero_model()
    wav = read_audio(str(p), sampling_rate=sampling_rate)
    duration_samples = len(wav)
    duration_ms = int(duration_samples * 1000 / sampling_rate)

    timestamps = get_speech_timestamps(
        wav,
        model,
        sampling_rate=sampling_rate,
        threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
        return_seconds=False,
    )

    def _to_ms(samples: int) -> int:
        return int(samples * 1000 / sampling_rate)

    speech_segments: List[Tuple[int, int]] = [
        (_to_ms(ts["start"]), _to_ms(ts["end"])) for ts in timestamps
    ]
    total_speech_ms = sum(e - s for s, e in speech_segments)
    speech_ratio = total_speech_ms / duration_ms if duration_ms > 0 else 0.0

    trim_suggestion: Optional[Tuple[int, int]] = None
    if speech_segments:
        first_start = speech_segments[0][0]
        last_end = speech_segments[-1][1]
        if first_start > silence_trim_ms or (duration_ms - last_end) > silence_trim_ms:
            trim_start = max(0, first_start - _PRE_SPEECH_MARGIN_MS)
            trim_end = min(duration_ms, last_end + _POST_SPEECH_MARGIN_MS)
            trim_suggestion = (trim_start, trim_end)

    internal_pauses: List[Tuple[int, int]] = []
    for i in range(1, len(speech_segments)):
        prev_end = speech_segments[i - 1][1]
        curr_start = speech_segments[i][0]
        if curr_start - prev_end > 200:
            internal_pauses.append((prev_end, curr_start))

    logger.debug(
        "Silero VAD: %d segmentos, ratio=%.2f, threshold=%.2f",
        len(speech_segments), speech_ratio, threshold,
    )
    return VADResult(
        speech_segments=speech_segments,
        speech_ratio=speech_ratio,
        duration_ms=duration_ms,
        trim_suggestion=trim_suggestion,
        internal_pauses=internal_pauses,
    )


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
    """Seleccionar automáticamente el mejor backend VAD disponible.

    Args:
        audio_path: Ruta al archivo WAV.
        backend: ``"auto"`` — Silero si disponible, si no energía;
                 ``"silero"`` — forzar Silero (error si no instalado);
                 ``"energy"`` — forzar VAD basado en energía.
        **kwargs: Parámetros del backend seleccionado.

    Returns:
        :class:`VADResult`.
    """
    if backend == "energy":
        return analyze_vad(audio_path, **{k: v for k, v in kwargs.items() if k in _ENERGY_KWARGS})
    if backend == "silero":
        return analyze_vad_silero(audio_path, **{k: v for k, v in kwargs.items() if k in _SILERO_KWARGS})
    # "auto"
    try:
        result = analyze_vad_silero(
            audio_path,
            **{k: v for k, v in kwargs.items() if k in _SILERO_KWARGS},
        )
        logger.debug("analyze_vad_best: usando Silero VAD")
        return result
    except ImportError:
        logger.debug("analyze_vad_best: Silero no disponible, usando VAD de energía")
        return analyze_vad(
            audio_path,
            **{k: v for k, v in kwargs.items() if k in _ENERGY_KWARGS},
        )


__all__ = ["VADResult", "analyze_vad", "analyze_vad_silero", "analyze_vad_best"]
