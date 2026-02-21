"""Helpers para diagnosticar calidad de audio."""
from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any

from ipa_core.audio.quality_gates import (
    check_quality,
    QualityGateResult,
    DEFAULT_MAX_CLIPPING_RATIO,
    DEFAULT_MIN_DURATION_MS,
    DEFAULT_MAX_DURATION_MS,
)
from ipa_core.services.user_profile import UserProfileStore, adaptive_thresholds


def assess_audio_quality(
    path: Optional[str],
    *,
    user_id: Optional[str] = None,
    speech_segments: Optional[List[tuple]] = None,
) -> Tuple[Optional[QualityGateResult], list[str], Optional[Dict[str, Any]]]:
    """Ejecutar quality gates si el path es válido y retornar warnings.

    Args:
        path: Ruta al archivo WAV.
        user_id: ID de usuario para perfiles adaptativos.
        speech_segments: Segmentos de voz [(start_ms, end_ms), ...] del VAD.
            Si se proveen, el SNR se calcula real en lugar del proxy.
    """
    if not path or not path.lower().endswith(".wav"):
        return None, [], None
    profile = None
    if user_id:
        store = UserProfileStore()
        profile = store.get(user_id)
    thresholds = adaptive_thresholds(profile)
    try:
        result = check_quality(
            path,
            min_duration_ms=DEFAULT_MIN_DURATION_MS,
            max_duration_ms=DEFAULT_MAX_DURATION_MS,
            min_snr_db=thresholds["min_snr_db"],
            max_clipping_ratio=DEFAULT_MAX_CLIPPING_RATIO,
            min_rms=thresholds["min_rms"],
            speech_segments=speech_segments,
        )
    except Exception:
        return None, [], None
    if user_id:
        store = UserProfileStore()
        profile = store.update(user_id, result)
    warnings: list[str] = []
    if not result.passed and result.user_feedback:
        warnings.append(result.user_feedback)
    meta = None
    if user_id:
        meta = {
            "user_id": user_id,
            "profile": profile.to_dict() if profile else None,
            "thresholds": thresholds,
        }
    return result, warnings, meta


__all__ = ["assess_audio_quality"]
