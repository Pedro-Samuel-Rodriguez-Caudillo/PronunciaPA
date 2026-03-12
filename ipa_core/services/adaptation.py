"""Auto-adapt evaluation settings based on audio quality."""
from __future__ import annotations

import os
from typing import Optional, Tuple, Dict, Any

from ipa_core.audio.quality_gates import QualityGateResult, QualityIssue
from ipa_core.services.user_profile import UserAudioProfile


def _env_flag(name: str, default: bool) -> bool:
    """Read boolean environment flags in a tolerant/production-safe way."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def adapt_settings(
    *,
    requested_mode: Optional[str],
    requested_level: Optional[str],
    quality: Optional[QualityGateResult],
    profile: Optional[UserAudioProfile] = None,
    force_phonetic: Optional[bool] = None,
    allow_quality_downgrade: Optional[bool] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """Return effective (mode, evaluation_level) and adaptation metadata."""
    resolved_force_phonetic = (
        _env_flag("PRONUNCIAPA_FORCE_PHONETIC", False)
        if force_phonetic is None
        else force_phonetic
    )
    resolved_allow_quality_downgrade = (
        _env_flag("PRONUNCIAPA_ADAPT_QUALITY_DOWNGRADE", True)
        if allow_quality_downgrade is None
        else allow_quality_downgrade
    )

    mode = (requested_mode or "objective").lower()
    level = (requested_level or "phonemic").lower()
    auto_mode = mode == "auto"
    auto_level = level == "auto"

    effective_mode = "objective" if auto_mode else mode
    effective_level = "phonemic" if auto_level else level
    reasons: list[str] = []

    issues = set(quality.issues) if quality else set()
    severe = any(
        issue in (QualityIssue.NO_SPEECH, QualityIssue.TOO_QUIET, QualityIssue.CLIPPING)
        for issue in issues
    )
    moderate = any(
        issue in (QualityIssue.LOW_SNR, QualityIssue.TOO_SHORT, QualityIssue.TOO_LONG)
        for issue in issues
    )

    if auto_level:
        if quality and quality.passed:
            effective_level = "phonetic"
        else:
            effective_level = "phonemic"
        reasons.append("auto_level")

    if auto_mode:
        if quality and quality.passed:
            effective_mode = "phonetic"
        elif severe:
            effective_mode = "casual"
        else:
            effective_mode = "objective"
        reasons.append("auto_mode")

    # Quality downgrades can be disabled for high-fidelity evaluation workflows.
    if resolved_allow_quality_downgrade:
        if not auto_level and effective_level == "phonetic" and (severe or moderate):
            effective_level = "phonemic"
            reasons.append("downgrade_level_quality")

        if not auto_mode and effective_mode == "phonetic" and (severe or moderate):
            effective_mode = "objective" if not severe else "casual"
            reasons.append("downgrade_mode_quality")
    else:
        reasons.append("quality_downgrade_disabled")

    # If profile shows consistently strong audio, allow upgrade in auto.
    if auto_mode or auto_level:
        if profile and profile.samples >= 5:
            if (profile.snr_ema or 0) >= 20 and (profile.rms_ema or 0) >= 0.02:
                if auto_level:
                    effective_level = "phonetic"
                if auto_mode:
                    effective_mode = "phonetic"
                reasons.append("upgrade_profile_baseline")

    if resolved_force_phonetic:
        effective_mode = "phonetic"
        effective_level = "phonetic"
        reasons.append("force_phonetic")

    if effective_mode not in ("casual", "objective", "phonetic"):
        effective_mode = "objective"
        reasons.append("normalize_mode_default")
    if effective_level not in ("phonemic", "phonetic"):
        effective_level = "phonemic"
        reasons.append("normalize_level_default")

    meta = {
        "requested": {"mode": mode, "evaluation_level": level},
        "effective": {"mode": effective_mode, "evaluation_level": effective_level},
        "reasons": reasons,
        "issues": [i.value for i in issues],
        "policy": {
            "force_phonetic": resolved_force_phonetic,
            "allow_quality_downgrade": resolved_allow_quality_downgrade,
        },
    }
    return effective_mode, effective_level, meta


__all__ = ["adapt_settings"]
