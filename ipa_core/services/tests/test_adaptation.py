from __future__ import annotations

import pytest

from ipa_core.audio.quality_gates import QualityGateResult, QualityIssue
from ipa_core.services.adaptation import adapt_settings


def _quality(*issues: QualityIssue, passed: bool = False) -> QualityGateResult:
    return QualityGateResult(
        passed=passed,
        issues=list(issues),
        snr_db=12.0,
        rms_amplitude=0.01,
        duration_ms=1000,
    )


@pytest.mark.unit
@pytest.mark.functional
def test_adapt_settings_downgrades_phonetic_when_quality_is_weak(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRONUNCIAPA_ADAPT_QUALITY_DOWNGRADE", raising=False)
    monkeypatch.delenv("PRONUNCIAPA_FORCE_PHONETIC", raising=False)

    mode, level, meta = adapt_settings(
        requested_mode="phonetic",
        requested_level="phonetic",
        quality=_quality(QualityIssue.LOW_SNR),
    )

    assert mode == "objective"
    assert level == "phonemic"
    assert "downgrade_mode_quality" in meta["reasons"]
    assert "downgrade_level_quality" in meta["reasons"]
    assert meta["policy"]["allow_quality_downgrade"] is True


@pytest.mark.unit
@pytest.mark.functional
def test_adapt_settings_respects_disabled_quality_downgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRONUNCIAPA_ADAPT_QUALITY_DOWNGRADE", "false")
    monkeypatch.delenv("PRONUNCIAPA_FORCE_PHONETIC", raising=False)

    mode, level, meta = adapt_settings(
        requested_mode="phonetic",
        requested_level="phonetic",
        quality=_quality(QualityIssue.LOW_SNR),
    )

    assert mode == "phonetic"
    assert level == "phonetic"
    assert "quality_downgrade_disabled" in meta["reasons"]
    assert meta["policy"]["allow_quality_downgrade"] is False


@pytest.mark.unit
@pytest.mark.functional
def test_adapt_settings_force_phonetic_overrides_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRONUNCIAPA_FORCE_PHONETIC", "true")
    monkeypatch.setenv("PRONUNCIAPA_ADAPT_QUALITY_DOWNGRADE", "true")

    mode, level, meta = adapt_settings(
        requested_mode="objective",
        requested_level="phonemic",
        quality=_quality(QualityIssue.NO_SPEECH),
    )

    assert mode == "phonetic"
    assert level == "phonetic"
    assert "force_phonetic" in meta["reasons"]
    assert meta["policy"]["force_phonetic"] is True


@pytest.mark.unit
@pytest.mark.functional
def test_adapt_settings_explicit_args_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRONUNCIAPA_FORCE_PHONETIC", "true")
    monkeypatch.setenv("PRONUNCIAPA_ADAPT_QUALITY_DOWNGRADE", "false")

    mode, level, meta = adapt_settings(
        requested_mode="phonetic",
        requested_level="phonetic",
        quality=_quality(QualityIssue.LOW_SNR),
        force_phonetic=False,
        allow_quality_downgrade=True,
    )

    assert mode == "objective"
    assert level == "phonemic"
    assert meta["policy"]["force_phonetic"] is False
    assert meta["policy"]["allow_quality_downgrade"] is True
