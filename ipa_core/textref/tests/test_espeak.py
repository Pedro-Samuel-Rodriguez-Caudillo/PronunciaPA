from __future__ import annotations

import pytest

from ipa_core.textref.espeak import EspeakTextRef


@pytest.mark.unit
@pytest.mark.functional
def test_resolve_voice_uses_specific_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRONUNCIAPA_ESPEAK_VOICE_EN", "en-us")
    provider = EspeakTextRef(binary="espeak")

    assert provider._resolve_voice("en") == "en-us"


@pytest.mark.unit
@pytest.mark.functional
def test_resolve_voice_supports_bcp47_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRONUNCIAPA_ESPEAK_VOICE_EN", raising=False)
    provider = EspeakTextRef(binary="espeak")

    # Falls back from en-gb to base language mapping.
    assert provider._resolve_voice("en-gb") == "en"


@pytest.mark.unit
@pytest.mark.functional
def test_resolve_voice_uses_global_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRONUNCIAPA_ESPEAK_VOICE", "en-us")
    provider = EspeakTextRef(binary="espeak")

    assert provider._resolve_voice("zz") == "en-us"
