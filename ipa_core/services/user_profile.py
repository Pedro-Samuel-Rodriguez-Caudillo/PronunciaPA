"""User profile store for adaptive audio quality."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Union

from ipa_core.audio.quality_gates import QualityGateResult, DEFAULT_MIN_RMS, DEFAULT_MIN_SNR_DB


DEFAULT_PROFILE_PATH = Path("outputs") / "user_profiles.json"
_EMA_ALPHA = 0.2


def _ema(prev: Optional[float], value: Optional[float]) -> Optional[float]:
    if value is None:
        return prev
    if prev is None:
        return value
    return (value * _EMA_ALPHA) + (prev * (1.0 - _EMA_ALPHA))


@dataclass
class UserAudioProfile:
    user_id: str
    samples: int = 0
    rms_ema: Optional[float] = None
    snr_ema: Optional[float] = None
    clipping_ema: Optional[float] = None
    last_seen: Optional[str] = None

    def update(self, quality: QualityGateResult) -> None:
        self.samples += 1
        self.rms_ema = _ema(self.rms_ema, quality.rms_amplitude)
        self.snr_ema = _ema(self.snr_ema, quality.snr_db)
        self.clipping_ema = _ema(self.clipping_ema, quality.clipping_ratio)
        self.last_seen = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserAudioProfile":
        return cls(
            user_id=str(data.get("user_id", "")),
            samples=int(data.get("samples", 0)),
            rms_ema=data.get("rms_ema"),
            snr_ema=data.get("snr_ema"),
            clipping_ema=data.get("clipping_ema"),
            last_seen=data.get("last_seen"),
        )


class UserProfileStore:
    """Persist user audio profiles to a JSON file."""

    def __init__(self, path: Optional[Union[Path, str]] = None) -> None:
        self._path = Path(path) if path else DEFAULT_PROFILE_PATH

    def load(self) -> Dict[str, UserAudioProfile]:
        if not self._path.exists():
            return {}
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        profiles: Dict[str, UserAudioProfile] = {}
        if isinstance(raw, dict):
            for user_id, payload in raw.items():
                if isinstance(payload, dict):
                    profiles[user_id] = UserAudioProfile.from_dict(payload)
        return profiles

    def save(self, profiles: Dict[str, UserAudioProfile]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {uid: profile.to_dict() for uid, profile in profiles.items()}
        self._path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def get(self, user_id: str) -> Optional[UserAudioProfile]:
        profiles = self.load()
        return profiles.get(user_id)

    def update(self, user_id: str, quality: QualityGateResult) -> UserAudioProfile:
        profiles = self.load()
        profile = profiles.get(user_id) or UserAudioProfile(user_id=user_id)
        profile.update(quality)
        profiles[user_id] = profile
        self.save(profiles)
        return profile


def adaptive_thresholds(profile: Optional[UserAudioProfile]) -> dict[str, float]:
    """Adjust thresholds using user baseline to avoid punishing weak mics."""
    min_rms = DEFAULT_MIN_RMS
    min_snr_db = DEFAULT_MIN_SNR_DB

    if profile and profile.samples >= 3:
        if profile.rms_ema is not None:
            min_rms = min(min_rms, max(0.003, profile.rms_ema * 0.5))
        if profile.snr_ema is not None:
            min_snr_db = min(min_snr_db, max(5.0, profile.snr_ema * 0.7))

    return {
        "min_rms": min_rms,
        "min_snr_db": min_snr_db,
    }


__all__ = [
    "UserAudioProfile",
    "UserProfileStore",
    "adaptive_thresholds",
    "DEFAULT_PROFILE_PATH",
]
