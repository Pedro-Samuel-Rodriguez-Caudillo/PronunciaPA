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
import math
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


QUALITY_ISSUE_PRIORITY = [
    QualityIssue.NO_SPEECH,
    QualityIssue.TOO_QUIET,
    QualityIssue.CLIPPING,
    QualityIssue.LOW_SNR,
    QualityIssue.TOO_SHORT,
    QualityIssue.TOO_LONG,
]

QUALITY_ISSUE_ERROR_CODES = {
    QualityIssue.CLIPPING: "audio_clipping",
    QualityIssue.LOW_SNR: "audio_low_snr",
    QualityIssue.TOO_SHORT: "audio_too_short",
    QualityIssue.TOO_LONG: "audio_too_long",
    QualityIssue.TOO_QUIET: "audio_too_quiet",
    QualityIssue.NO_SPEECH: "audio_no_speech",
}


def _normalize_quality_issue(issue: QualityIssue | str) -> Optional[QualityIssue]:
    if isinstance(issue, QualityIssue):
        return issue
    try:
        return QualityIssue(str(issue))
    except ValueError:
        return None


def primary_quality_issue(issues: List[QualityIssue] | List[str]) -> Optional[QualityIssue]:
    """Retorna el issue prioritario para feedback y códigos estables."""
    normalized = {
        normalized_issue
        for issue in issues
        if (normalized_issue := _normalize_quality_issue(issue)) is not None
    }
    for priority_issue in QUALITY_ISSUE_PRIORITY:
        if priority_issue in normalized:
            return priority_issue
    return None


def quality_issue_error_code(issue: QualityIssue | str) -> Optional[str]:
    """Mapea un issue de calidad a un código de error estable."""
    normalized = _normalize_quality_issue(issue)
    if normalized is None:
        return None
    return QUALITY_ISSUE_ERROR_CODES.get(normalized)


def quality_gate_error_code(issues: List[QualityIssue] | List[str]) -> Optional[str]:
    """Retorna el código estable del issue prioritario."""
    priority_issue = primary_quality_issue(issues)
    if priority_issue is None:
        return None
    return QUALITY_ISSUE_ERROR_CODES.get(priority_issue)


@dataclass
class QualityGateResult:
    """Resultado de quality gates.

    snr_db es una medición real cuando speech_segments están disponibles
    (calculado como RMS de voz / RMS de silencio). En caso contrario,
    es un proxy basado en el percentil 10 de amplitud.
    snr_method indica cuál método se usó: "real_vad" o "proxy".
    """

    # ¿Pasó todas las validaciones?
    passed: bool

    # Lista de issues detectados
    issues: List[QualityIssue] = field(default_factory=list)

    # Métricas calculadas
    snr_db: Optional[float] = None
    snr_method: str = "proxy"
    clipping_ratio: Optional[float] = None
    duration_ms: Optional[int] = None
    peak_amplitude: Optional[float] = None
    rms_amplitude: Optional[float] = None

    # Feedback operativo para el usuario (si hay issues)
    user_feedback: Optional[str] = None

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización."""
        priority_issue = primary_quality_issue(self.issues)
        return {
            "passed": self.passed,
            "issues": [i.value for i in self.issues],
            "primary_issue": priority_issue.value if priority_issue else None,
            "error_code": quality_gate_error_code(self.issues),
            "snr_db": self.snr_db,
            "snr_method": self.snr_method,
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


def _compute_snr(
    samples: tuple,
    sample_rate: int,
    speech_segments: Optional[List[tuple]],
    rms: float,
    max_val: int,
) -> tuple[float, str]:
    """Calcular SNR en dB (VAD o proxy)."""
    if speech_segments:
        res = _compute_real_vad_snr(samples, sample_rate, speech_segments, max_val)
        if res is not None:
            return res[0], "real_vad"

    return _compute_proxy_snr(samples, rms, max_val), "proxy"


def _compute_real_vad_snr(samples: tuple, sr: int, segments: list[tuple], max_val: int) -> Optional[tuple[float, str]]:
    speech_sq, silence_sq, speech_c, silence_c = _sum_squares_by_vad(samples, sr, segments)

    if silence_c < int(0.05 * len(samples)) or silence_c == 0:
        return None

    noise_rms = (silence_sq / silence_c) ** 0.5 / max_val
    signal_rms = (speech_sq / max(speech_c, 1)) ** 0.5 / max_val
    
    if noise_rms <= 0.0001:
        return 60.0, "real_vad"
        
    snr_db = 20.0 * math.log10(max(signal_rms, 1e-9) / noise_rms)
    return snr_db, "real_vad"


def _sum_squares_by_vad(samples: tuple, sr: int, segments: list[tuple]) -> tuple[float, float, int, int]:
    speech_sq, silence_sq, speech_c, silence_c = 0.0, 0.0, 0, 0
    for i, s in enumerate(samples):
        ms = i * 1000.0 / sr
        in_speech = any(start <= ms < end for start, end in segments)
        sq = s * s
        if in_speech:
            speech_sq += sq
            speech_c += 1
        else:
            silence_sq += sq
            silence_c += 1
    return speech_sq, silence_sq, speech_c, silence_c


def _compute_proxy_snr(samples: tuple, rms: float, max_val: int) -> float:
    sorted_abs = sorted(abs(s) for s in samples)
    noise_floor = sorted_abs[len(sorted_abs) // 10] / max_val
    if noise_floor > 0.001:
        return 20.0 * math.log10(rms / noise_floor)
    return 60.0


def check_quality(
    audio_path: str,
    *,
    min_duration_ms: int = DEFAULT_MIN_DURATION_MS,
    max_duration_ms: int = DEFAULT_MAX_DURATION_MS,
    min_snr_db: float = DEFAULT_MIN_SNR_DB,
    max_clipping_ratio: float = DEFAULT_MAX_CLIPPING_RATIO,
    min_rms: float = DEFAULT_MIN_RMS,
    speech_ratio: Optional[float] = None,
    speech_segments: Optional[List[tuple]] = None,
) -> QualityGateResult:
    """Validar calidad del audio."""
    samples, sr, duration_ms = _read_audio_data(audio_path)
    if not samples:
        return _empty_audio_result(duration_ms)
    
    issues = _collect_quality_issues(
        samples, sr, duration_ms, min_duration_ms, max_duration_ms,
        max_clipping_ratio, min_rms, speech_ratio
    )
    
    metrics = _calculate_audio_metrics(samples, sr, speech_segments)
    if metrics["snr_db"] < min_snr_db:
        issues.append(QualityIssue.LOW_SNR)
        
    return _build_quality_gate_result(issues, duration_ms, metrics)


def _read_audio_data(path: str) -> tuple[tuple, int, int]:
    import struct
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Audio no encontrado: {path}")
    
    with wave.open(str(p), "rb") as w:
        sr = w.getframerate()
        sw = w.getsampwidth()
        nf = w.getnframes()
        raw = w.readframes(nf)
    
    duration_ms = int(nf * 1000 / sr)
    if sw != 2:
        return (), sr, duration_ms
        
    fmt = f"<{len(raw) // 2}h"
    return struct.unpack(fmt, raw), sr, duration_ms


def _empty_audio_result(duration: int) -> QualityGateResult:
    return QualityGateResult(
        passed=False, issues=[QualityIssue.TOO_SHORT],
        duration_ms=duration, user_feedback=_FEEDBACK_MESSAGES[QualityIssue.TOO_SHORT]
    )


def _collect_quality_issues(samples, sr, duration, min_d, max_d, max_clip, min_rms, speech_ratio) -> list[QualityIssue]:
    issues = []
    _check_duration_issues(issues, duration, min_d, max_d)
    _check_amplitude_issues(issues, samples, min_rms, max_clip)
    
    if speech_ratio is not None and speech_ratio < 0.1:
        issues.append(QualityIssue.NO_SPEECH)
    return issues


def _check_duration_issues(issues: list, duration: int, min_d: int, max_d: int):
    if duration < min_d:
        issues.append(QualityIssue.TOO_SHORT)
    if duration > max_d:
        issues.append(QualityIssue.TOO_LONG)


def _check_amplitude_issues(issues: list, samples: tuple, min_rms: float, max_clip: float):
    if _calculate_rms(samples) < min_rms:
        issues.append(QualityIssue.TOO_QUIET)
    if _calculate_clipping_ratio(samples) > max_clip:
        issues.append(QualityIssue.CLIPPING)


def _calculate_rms(samples: tuple) -> float:
    max_val = 32767
    sum_sq = sum(s * s for s in samples)
    return (sum_sq / len(samples)) ** 0.5 / max_val


def _calculate_clipping_ratio(samples: tuple) -> float:
    threshold = int(32767 * 0.99)
    clipped = sum(1 for s in samples if abs(s) >= threshold)
    return clipped / len(samples)


def _calculate_audio_metrics(samples: tuple, sr: int, segments: Optional[list]) -> dict:
    max_val = 32767
    peak = max(abs(s) for s in samples)
    rms = _calculate_rms(samples)
    snr_db, snr_method = _compute_snr(samples, sr, segments, rms, max_val)
    
    return {
        "snr_db": snr_db, "snr_method": snr_method,
        "peak": peak / max_val, "rms": rms,
        "clipping": _calculate_clipping_ratio(samples)
    }


def _build_quality_gate_result(issues: list[QualityIssue], duration: int, metrics: dict) -> QualityGateResult:
    user_feedback = None
    if issues:
        priority = primary_quality_issue(issues)
        if priority:
            user_feedback = _FEEDBACK_MESSAGES[priority]
            
    return QualityGateResult(
        passed=not issues, issues=issues, duration_ms=duration,
        snr_db=metrics["snr_db"], snr_method=metrics["snr_method"],
        clipping_ratio=metrics["clipping"], peak_amplitude=metrics["peak"],
        rms_amplitude=metrics["rms"], user_feedback=user_feedback
    )


__all__ = [
    "QualityIssue",
    "QualityGateResult",
    "QUALITY_ISSUE_ERROR_CODES",
    "QUALITY_ISSUE_PRIORITY",
    "check_quality",
    "primary_quality_issue",
    "quality_gate_error_code",
    "quality_issue_error_code",
]
