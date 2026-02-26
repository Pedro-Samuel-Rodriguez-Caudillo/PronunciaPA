"""Prosody / rhythm analysis — Step 10 del pipeline de pronunciación.

Calcula métricas de pausas, velocidad del habla y desviaciones de duración sin
requerir modelos pesados.  librosa es **opcional**: si está instalado, se extrae
F0 media y desviación; si no, esos campos quedan en None.

Métricas que devuelve ``ProsodyMetrics``:
    speech_rate_phones_per_sec  — fonemas observados por segundo de audio "activo"
    speech_rate_ratio           — tasa observada / tasa de referencia (1.0 = igual)
    pause_count                 — número de pausas internas
    avg_pause_ms                — duración media de pausas internas (ms)
    max_pause_ms                — pausa más larga (ms)
    voiced_ms                   — milisegundos totales con voz
    total_ms                    — duración total del audio (ms)
    speech_ratio                — voiced_ms / total_ms
    rhythm_score                — puntuación compuesta 0–100 (mayor = mejor ritmo)
    f0_mean_hz                  — F0 media en Hz (librosa); None si no disponible
    f0_std_hz                   — desviación estándar de F0 (librosa); None si no disponible

Pipeline Step 10: integrar al score con pesos del scoring_profile del pack.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parámetros por defecto
# ---------------------------------------------------------------------------

# Velocidad de habla típica en español: ~12–16 fonemas/s en habla fluida.
# Referencia si el caller no proporciona una.
DEFAULT_REF_SPEECH_RATE = 14.0  # fonemas/s

# Penalización por pausa: score se reduce si avg_pause_ms supera este umbral.
PAUSE_PENALTY_THRESHOLD_MS = 600  # ms


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

@dataclass
class ProsodyMetrics:
    """Resultado del análisis de prosodia / ritmo."""

    # Velocidad del habla
    speech_rate_phones_per_sec: float = 0.0
    speech_rate_ratio: float = 1.0     # observada / referencia

    # Pausas internas
    pause_count: int = 0
    avg_pause_ms: float = 0.0
    max_pause_ms: float = 0.0

    # Duración
    voiced_ms: int = 0
    total_ms: int = 0
    speech_ratio: float = 0.0          # voiced/total

    # Puntuación compuesta (0–100)
    rhythm_score: float = 100.0

    # F0 (solo si librosa está disponible)
    f0_mean_hz: Optional[float] = None
    f0_std_hz: Optional[float] = None

    # Meta
    meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def analyze_prosody(
    audio_path: str,
    *,
    observed_phones: Optional[Sequence[str]] = None,
    ref_speech_rate: float = DEFAULT_REF_SPEECH_RATE,
    vad_speech_segments: Optional[List[Tuple[int, int]]] = None,
    vad_internal_pauses: Optional[List[Tuple[int, int]]] = None,
    vad_duration_ms: Optional[int] = None,
    extract_f0: bool = True,
) -> ProsodyMetrics:
    """Analizar prosodia y ritmo de un archivo WAV.

    Args:
        audio_path: Ruta al archivo WAV (16-bit mono o estéreo PCM).
        observed_phones: Secuencia de fonemas IPA observados (para velocidad).
        ref_speech_rate: Velocidad de referencia en fonemas/s.
        vad_speech_segments: Segmentos de voz [(start_ms, end_ms)] del VAD.
            Si se omiten, el análisis usa la duración completa del audio.
        vad_internal_pauses: Pausas internas [(start_ms, end_ms)] del VAD.
        vad_duration_ms: Duración total en ms (si ya se calculó por VAD).
        extract_f0: Intentar extracción de F0 vía librosa (si está instalado).

    Returns:
        ProsodyMetrics con todas las métricas calculadas.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")

    # -- Duración total -------------------------------------------------------
    total_ms = vad_duration_ms or _get_wav_duration_ms(path)

    # -- Duración de voz activa -----------------------------------------------
    if vad_speech_segments:
        voiced_ms = sum(end - start for start, end in vad_speech_segments)
    else:
        # Sin VAD: usamos la duración completa como proxy
        voiced_ms = total_ms

    speech_ratio = voiced_ms / total_ms if total_ms > 0 else 0.0

    # -- Velocidad del habla --------------------------------------------------
    n_phones = len(observed_phones) if observed_phones else 0
    voiced_s = voiced_ms / 1000.0
    if n_phones > 0 and voiced_s > 0:
        speech_rate = n_phones / voiced_s
    else:
        speech_rate = 0.0

    rate_ratio = (speech_rate / ref_speech_rate) if ref_speech_rate > 0 and speech_rate > 0 else 1.0

    # -- Pausas internas ------------------------------------------------------
    pauses = vad_internal_pauses or []
    pause_count = len(pauses)
    avg_pause_ms: float = 0.0
    max_pause_ms: float = 0.0
    if pauses:
        durations = [float(end - start) for start, end in pauses]
        avg_pause_ms = sum(durations) / len(durations)
        max_pause_ms = max(durations)

    # -- F0 (opcional, requiere librosa) -------------------------------------
    f0_mean, f0_std = None, None
    if extract_f0:
        f0_mean, f0_std = _extract_f0(path)

    # -- Puntuación compuesta ------------------------------------------------
    rhythm_score = _compute_rhythm_score(
        rate_ratio=rate_ratio,
        pause_count=pause_count,
        avg_pause_ms=avg_pause_ms,
        speech_ratio=speech_ratio,
        total_ms=total_ms,
    )

    return ProsodyMetrics(
        speech_rate_phones_per_sec=round(speech_rate, 2),
        speech_rate_ratio=round(rate_ratio, 3),
        pause_count=pause_count,
        avg_pause_ms=round(avg_pause_ms, 1),
        max_pause_ms=round(max_pause_ms, 1),
        voiced_ms=voiced_ms,
        total_ms=total_ms,
        speech_ratio=round(speech_ratio, 3),
        rhythm_score=round(rhythm_score, 1),
        f0_mean_hz=round(f0_mean, 1) if f0_mean is not None else None,
        f0_std_hz=round(f0_std, 1) if f0_std is not None else None,
        meta={
            "ref_speech_rate": ref_speech_rate,
            "n_phones": n_phones,
            "vad_used": vad_speech_segments is not None,
        },
    )


# ---------------------------------------------------------------------------
# Cálculo de puntuación compuesta
# ---------------------------------------------------------------------------

def _compute_rhythm_score(
    *,
    rate_ratio: float,
    pause_count: int,
    avg_pause_ms: float,
    speech_ratio: float,
    total_ms: int,
) -> float:
    """Puntuación 0–100. Penaliza velocidades muy alejadas de referencia,
    demasiadas pausas largas, y ratio de voz muy bajo.

    Pesos aproximados:
        60 pts — velocidad (ratio cercano a 1.0)
        25 pts — pausas
        15 pts — ratio de voz/silencio
    """
    # Velocidad: máximo 60 puntos
    # desviación tolerable: ±30 % sin penalización, lineal hasta 0 en ±100 %
    rate_dev = abs(rate_ratio - 1.0) if rate_ratio > 0 else 1.0
    rate_tolerance = 0.30
    rate_excess = max(0.0, rate_dev - rate_tolerance)
    rate_score = 60.0 * max(0.0, 1.0 - rate_excess / 0.70)

    # Pausas: máximo 25 puntos
    if total_ms > 0 and avg_pause_ms > PAUSE_PENALTY_THRESHOLD_MS:
        # Penalizar proporcionalmente al exceso sobre el umbral
        excess_ratio = (avg_pause_ms - PAUSE_PENALTY_THRESHOLD_MS) / PAUSE_PENALTY_THRESHOLD_MS
        pause_penalty = min(1.0, excess_ratio * 0.5 + pause_count * 0.05)
        pause_score = 25.0 * max(0.0, 1.0 - pause_penalty)
    else:
        pause_score = 25.0

    # Ratio de voz: máximo 15 puntos
    # Esperamos al menos 0.5 de speech_ratio para un buen intento
    ratio_score = 15.0 * min(1.0, speech_ratio / 0.5) if speech_ratio < 0.5 else 15.0

    return rate_score + pause_score + ratio_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_wav_duration_ms(path: Path) -> int:
    """Leer duración total de un WAV sin cargar todo el audio."""
    import wave as _wave  # stdlib

    try:
        with _wave.open(str(path), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if rate > 0:
                return int(frames * 1000 / rate)
    except Exception as exc:
        logger.warning("No se pudo leer duración de %s: %s", path, exc)
    return 0


def _extract_f0(path: Path) -> Tuple[Optional[float], Optional[float]]:
    """Extraer F0 media y desviación usando librosa (yin/pyin).

    Retorna (None, None) si librosa no está instalado o falla.
    """
    try:
        import librosa  # type: ignore[import]
        import numpy as np  # type: ignore[import]
    except ImportError:
        logger.debug("librosa no instalado; se omite extracción de F0")
        return None, None

    try:
        y, sr = librosa.load(str(path), sr=None, mono=True)
        # pyin es más robusto que yin para voces humanas
        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),   # ≈65 Hz
            fmax=librosa.note_to_hz("C7"),   # ≈2093 Hz
            sr=sr,
        )
        voiced_f0 = f0[voiced_flag]
        if len(voiced_f0) == 0:
            return None, None
        voiced_f0 = voiced_f0[~np.isnan(voiced_f0)]
        if len(voiced_f0) == 0:
            return None, None
        return float(np.mean(voiced_f0)), float(np.std(voiced_f0))
    except Exception as exc:
        logger.warning("Error al extraer F0 de %s: %s", path, exc)
        return None, None


# ---------------------------------------------------------------------------
# Integración de puntuación al pipeline global
# ---------------------------------------------------------------------------

def apply_prosody_weight(
    base_score: float,
    prosody: ProsodyMetrics,
    *,
    prosody_weight: float = 0.0,
) -> float:
    """Combinar puntuación base con puntuación de prosodia.

    Args:
        base_score: Puntuación fonética 0–100.
        prosody: Métricas de prosodia ya calculadas.
        prosody_weight: Peso de la prosodia en el score final (0.0–1.0).
            0.0 = ignorar prosodia (modo Casual)
            0.15 = peso suave (modo Objetivo)
            0.30 = peso alto (modo Fonético)

    Returns:
        Puntuación combinada 0–100.
    """
    if prosody_weight <= 0.0:
        return base_score
    phonetic_weight = 1.0 - prosody_weight
    return round(
        phonetic_weight * base_score + prosody_weight * prosody.rhythm_score, 1
    )


__all__ = [
    "ProsodyMetrics",
    "analyze_prosody",
    "apply_prosody_weight",
]
