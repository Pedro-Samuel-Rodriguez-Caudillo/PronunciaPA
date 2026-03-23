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


def _resolve_policies(
    force_phonetic: Optional[bool], allow_quality_downgrade: Optional[bool]
) -> Tuple[bool, bool]:
    resolved_force = force_phonetic
    if resolved_force is None:
        resolved_force = _env_flag("PRONUNCIAPA_FORCE_PHONETIC", False)

    resolved_allow_downgrade = allow_quality_downgrade
    if resolved_allow_downgrade is None:
        resolved_allow_downgrade = _env_flag("PRONUNCIAPA_ADAPT_QUALITY_DOWNGRADE", True)

    return resolved_force, resolved_allow_downgrade


def _get_quality_info(quality: Optional[QualityGateResult]) -> Tuple[set[QualityIssue], bool, bool]:
    issues = set(quality.issues) if quality else set()
    severe_set = {QualityIssue.NO_SPEECH, QualityIssue.TOO_QUIET, QualityIssue.CLIPPING}
    moderate_set = {QualityIssue.LOW_SNR, QualityIssue.TOO_SHORT, QualityIssue.TOO_LONG}
    
    severe = any(i in severe_set for i in issues)
    moderate = any(i in moderate_set for i in issues)
    return issues, severe, moderate


def _handle_auto_level(
    auto_level: bool, passed: bool, level: str, reasons: list[str]
) -> str:
    if not auto_level:
        return level
    reasons.append("auto_level")
    return "phonetic" if passed else "phonemic"


def _handle_auto_mode(
    auto_mode: bool, passed: bool, severe: bool, mode: str, reasons: list[str]
) -> str:
    if not auto_mode:
        return mode
    reasons.append("auto_mode")
    if passed:
        return "phonetic"
    return "casual" if severe else "objective"


def _downgrade_level(level: str, auto_level: bool, quality_fail: bool, reasons: list[str]) -> str:
    if auto_level or level != "phonetic":
        return level
    if quality_fail:
        reasons.append("downgrade_level_quality")
        return "phonemic"
    return level


def _downgrade_mode(mode: str, auto_mode: bool, severe: bool, moderate: bool, reasons: list[str]) -> str:
    if auto_mode or mode != "phonetic":
        return mode
    
    return _apply_mode_quality_downgrade(severe, moderate, reasons) or mode


def _apply_mode_quality_downgrade(severe: bool, moderate: bool, reasons: list[str]) -> Optional[str]:
    if not (severe or moderate):
        return None
    
    reasons.append("downgrade_mode_quality")
    return "casual" if severe else "objective"


def _apply_downgrades(
    allow_downgrade: bool,
    auto_level: bool,
    auto_mode: bool,
    level: str,
    mode: str,
    severe: bool,
    moderate: bool,
    reasons: list[str],
) -> Tuple[str, str]:
    if not allow_downgrade:
        reasons.append("quality_downgrade_disabled")
        return level, mode

    quality_fail = severe or moderate
    new_level = _downgrade_level(level, auto_level, quality_fail, reasons)
    new_mode = _downgrade_mode(mode, auto_mode, severe, moderate, reasons)

    return new_level, new_mode


def _check_profile_upgrade(profile: UserAudioProfile) -> bool:
    snr = profile.snr_ema or 0
    rms = profile.rms_ema or 0
    if snr < 20:
        return False
    return rms >= 0.02


def _check_upgrade_eligibility(auto_mode: bool, auto_level: bool, profile: Optional[UserAudioProfile]) -> bool:
    if not (auto_mode or auto_level):
        return False
    return bool(profile and profile.samples >= 5)


def _apply_profile_upgrade(
    auto_mode: bool,
    auto_level: bool,
    profile: Optional[UserAudioProfile],
    level: str,
    mode: str,
    reasons: list[str],
) -> Tuple[str, str]:
    if not _check_upgrade_eligibility(auto_mode, auto_level, profile):
        return level, mode

    if _check_profile_upgrade(profile): # type: ignore
        reasons.append("upgrade_profile_baseline")
        return "phonetic", "phonetic"

    return level, mode


def _normalize_mode(mode: str, reasons: list[str]) -> str:
    if mode in ("casual", "objective", "phonetic"):
        return mode
    reasons.append("normalize_mode_default")
    return "objective"


def _normalize_level(level: str, reasons: list[str]) -> str:
    if level in ("phonemic", "phonetic"):
        return level
    reasons.append("normalize_level_default")
    return "phonemic"


def _normalize_and_force(
    force_phonetic: bool, level: str, mode: str, reasons: list[str]
) -> Tuple[str, str]:
    if force_phonetic:
        reasons.append("force_phonetic")
        return "phonetic", "phonetic"

    final_mode = _normalize_mode(mode, reasons)
    final_level = _normalize_level(level, reasons)
    return final_level, final_mode


def _get_defaults(req_mode: Optional[str], req_level: Optional[str]) -> Tuple[str, str]:
    mode = (req_mode or "objective").lower()
    level = (req_level or "phonemic").lower()
    return mode, level


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
    force_p, allow_down = _resolve_policies(force_phonetic, allow_quality_downgrade)
    mode, level = _get_defaults(requested_mode, requested_level)
    auto_mode, auto_level = (mode == "auto"), (level == "auto")
    reasons: list[str] = []

    issues, severe, moderate = _get_quality_info(quality)
    passed = bool(quality and quality.passed)

    eff_level = _handle_auto_level(auto_level, passed, "phonemic" if auto_level else level, reasons)
    eff_mode = _handle_auto_mode(auto_mode, passed, severe, "objective" if auto_mode else mode, reasons)

    eff_level, eff_mode = _apply_downgrades(
        allow_down, auto_level, auto_mode, eff_level, eff_mode, severe, moderate, reasons
    )
    eff_level, eff_mode = _apply_profile_upgrade(
        auto_mode, auto_level, profile, eff_level, eff_mode, reasons
    )
    eff_level, eff_mode = _normalize_and_force(force_p, eff_level, eff_mode, reasons)

    meta = {
        "requested": {"mode": mode, "evaluation_level": level},
        "effective": {"mode": eff_mode, "evaluation_level": eff_level},
        "reasons": reasons,
        "issues": [i.value for i in issues],
        "policy": {"force_phonetic": force_p, "allow_quality_downgrade": allow_down},
    }
    return eff_mode, eff_level, meta


__all__ = ["adapt_settings"]
