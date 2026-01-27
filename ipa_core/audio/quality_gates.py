"""Quality Gates - Validación de calidad de audio.

Implementación de gates de calidad según ipa_core/TODO.md paso 6:
- SNR (Signal-to-Noise Ratio) proxy
- Detección de clipping
- Validación de duración mínima/máxima
- Feedback operativo cuando falla validación

Si falla validación, se retorna feedback operativo en lugar de análisis fonético.
"""
from __future__ import annotations

import logging
import wave
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class QualityIssue(Enum):
    """Tipos de problemas de calidad."""
    
    CLIPPING = "clipping"
    LOW_SNR = "low_snr"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    TOO_QUIET = "too_quiet"
    NO_SPEECH = "no_speech"


@dataclass
class QualityGateResult:
    """Resultado de quality gates."""
    
    # ¿Pasó todas las validaciones?
    passed: bool
    
    # Lista de issues detectados
    issues: List[QualityIssue] = field(default_factory=list)
    
    # Métricas calculadas
    snr_db: Optional[float] = None
    clipping_ratio: Optional[float] = None
    duration_ms: Optional[int] = None
    peak_amplitude: Optional[float] = None
    rms_amplitude: Optional[float] = None
    
    # Feedback operativo para el usuario (si hay issues)
    user_feedback: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        return {
            "passed": self.passed,
            "issues": [i.value for i in self.issues],
            "snr_db": self.snr_db,
            "clipping_ratio": self.clipping_ratio,
            "duration_ms": self.duration_ms,
            "peak_amplitude": self.peak_amplitude,
            "rms_amplitude": self.rms_amplitude,
            "user_feedback": self.user_feedback,
        }


# Umbrales por defecto
DEFAULT_MIN_DURATION_MS = 500  # Mínimo 0.5 segundos
DEFAULT_MAX_DURATION_MS = 30000  # Máximo 30 segundos
DEFAULT_MIN_SNR_DB = 10.0  # SNR mínimo (dB)
DEFAULT_MAX_CLIPPING_RATIO = 0.01  # Máximo 1% de clipping
DEFAULT_MIN_RMS = 0.01  # RMS mínima (audio muy silencioso)


# Feedback operativo por tipo de issue
_FEEDBACK_MESSAGES = {
    QualityIssue.CLIPPING: "El audio tiene distorsión. Aléjate del micrófono o baja el volumen.",
    QualityIssue.LOW_SNR: "Hay mucho ruido de fondo. Busca un lugar más silencioso.",
    QualityIssue.TOO_SHORT: "La grabación es muy corta. Intenta hablar más tiempo.",
    QualityIssue.TOO_LONG: "La grabación es muy larga. Intenta frases más cortas.",
    QualityIssue.TOO_QUIET: "El audio es muy silencioso. Acércate al micrófono.",
    QualityIssue.NO_SPEECH: "No se detectó voz. Asegúrate de que el micrófono funcione.",
}


def check_quality(
    audio_path: str,
    *,
    min_duration_ms: int = DEFAULT_MIN_DURATION_MS,
    max_duration_ms: int = DEFAULT_MAX_DURATION_MS,
    min_snr_db: float = DEFAULT_MIN_SNR_DB,
    max_clipping_ratio: float = DEFAULT_MAX_CLIPPING_RATIO,
    min_rms: float = DEFAULT_MIN_RMS,
    speech_ratio: Optional[float] = None,  # De VAD, si disponible
) -> QualityGateResult:
    """Validar calidad del audio.
    
    Args:
        audio_path: Ruta al archivo WAV (16-bit PCM)
        min_duration_ms: Duración mínima requerida
        max_duration_ms: Duración máxima permitida
        min_snr_db: SNR mínimo requerido en dB
        max_clipping_ratio: Ratio máximo de muestras clipeadas
        min_rms: RMS mínimo (audio muy silencioso)
        speech_ratio: Ratio de voz (de VAD), para detectar "no speech"
        
    Returns:
        QualityGateResult con métricas y feedback
    """
    p = Path(audio_path)
    if not p.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")
    
    # Leer audio
    with wave.open(str(p), "rb") as w:
        sample_rate = w.getframerate()
        sample_width = w.getsampwidth()
        n_frames = w.getnframes()
        raw_data = w.readframes(n_frames)
    
    duration_ms = int(n_frames * 1000 / sample_rate)
    issues = []
    
    # Validar duración
    if duration_ms < min_duration_ms:
        issues.append(QualityIssue.TOO_SHORT)
    if duration_ms > max_duration_ms:
        issues.append(QualityIssue.TOO_LONG)
    
    # Analizar samples
    import struct
    if sample_width == 2:
        fmt = f"<{len(raw_data) // 2}h"
        samples = struct.unpack(fmt, raw_data)
    else:
        samples = []
    
    if not samples:
        return QualityGateResult(
            passed=False,
            issues=[QualityIssue.TOO_SHORT],
            duration_ms=duration_ms,
            user_feedback=_FEEDBACK_MESSAGES[QualityIssue.TOO_SHORT],
        )
    
    # Calcular métricas de amplitud
    max_val = 32767  # Max para 16-bit signed
    peak = max(abs(s) for s in samples)
    peak_normalized = peak / max_val
    
    sum_sq = sum(s * s for s in samples)
    rms = (sum_sq / len(samples)) ** 0.5 / max_val
    
    # Detectar clipping
    clipping_threshold = int(max_val * 0.99)
    clipped_samples = sum(1 for s in samples if abs(s) >= clipping_threshold)
    clipping_ratio = clipped_samples / len(samples)
    
    if clipping_ratio > max_clipping_ratio:
        issues.append(QualityIssue.CLIPPING)
    
    # Validar RMS mínimo
    if rms < min_rms:
        issues.append(QualityIssue.TOO_QUIET)
    
    # Estimar SNR (proxy simple: ratio de pico a ruido de fondo)
    # Usamos el percentil 10 como estimación de ruido de fondo
    sorted_samples = sorted(abs(s) for s in samples)
    noise_floor = sorted_samples[len(sorted_samples) // 10] / max_val
    
    if noise_floor > 0.001:  # Evitar log(0)
        snr_db = 20 * (rms / noise_floor).__log10__() if hasattr((rms / noise_floor), '__log10__') else 20 * _log10(rms / noise_floor)
    else:
        snr_db = 60.0  # Asumimos bueno si el ruido es muy bajo
    
    if snr_db < min_snr_db:
        issues.append(QualityIssue.LOW_SNR)
    
    # Validar speech ratio (si viene de VAD)
    if speech_ratio is not None and speech_ratio < 0.1:
        issues.append(QualityIssue.NO_SPEECH)
    
    # Generar feedback
    user_feedback = None
    if issues:
        # Priorizar el issue más importante
        priority_order = [
            QualityIssue.NO_SPEECH,
            QualityIssue.TOO_QUIET,
            QualityIssue.CLIPPING,
            QualityIssue.LOW_SNR,
            QualityIssue.TOO_SHORT,
            QualityIssue.TOO_LONG,
        ]
        for priority_issue in priority_order:
            if priority_issue in issues:
                user_feedback = _FEEDBACK_MESSAGES[priority_issue]
                break
    
    return QualityGateResult(
        passed=len(issues) == 0,
        issues=issues,
        snr_db=snr_db,
        clipping_ratio=clipping_ratio,
        duration_ms=duration_ms,
        peak_amplitude=peak_normalized,
        rms_amplitude=rms,
        user_feedback=user_feedback,
    )


def _log10(x: float) -> float:
    """Log base 10 helper."""
    import math
    return math.log10(x) if x > 0 else 0.0


__all__ = ["QualityIssue", "QualityGateResult", "check_quality"]
