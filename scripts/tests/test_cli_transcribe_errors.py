"""Pruebas AAA de CLI en escenarios de error."""
from __future__ import annotations

import pytest

from ipa_core.interfaces import cli


def test_cli_transcribe_requires_audio_or_mic():
    with pytest.raises(ValueError):
        cli.cli_transcribe(None, use_mic=False)


def test_cli_transcribe_passes_textref_to_service(monkeypatch, tmp_path):
    called = {}

    from ipa_core.interfaces import cli
    from ipa_core.plugins import registry

    orig_resolve = registry.resolve_textref

    def mock_resolve(name, params=None):
        called["textref"] = name
        return orig_resolve("grapheme", params) # Fallback a uno que funcione

    monkeypatch.setattr(registry, "resolve_textref", mock_resolve)
    
    # Mock asr para evitar ejecución real
    class FakeASR:
        async def setup(self): pass
        async def teardown(self): pass
        async def transcribe(self, audio, *, lang=None, **kw):
            called["lang"] = lang
            return {"tokens": ["i", "p", "a"]}

    monkeypatch.setattr(registry, "resolve_asr", lambda *a, **k: FakeASR())

    audio = tmp_path / "dummy.wav"
    audio.write_bytes(b"\x00")

    tokens = cli.cli_transcribe(str(audio), lang="es", textref="espeak")

    assert tokens == ["i", "p", "a"]
    assert called["textref"] == "espeak"
    assert called["lang"] == "es"
