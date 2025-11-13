"""Pruebas AAA de CLI en escenarios de error."""
from __future__ import annotations

import pytest

from ipa_core.api import cli


def test_cli_transcribe_requires_audio_or_mic():
    with pytest.raises(ValueError):
        cli.cli_transcribe(None, use_mic=False)


def test_cli_transcribe_passes_textref_to_service(monkeypatch, tmp_path):
    called = {}

    class FakeService:
        def __init__(self, *, textref_name=None, **_kw):
            called["textref"] = textref_name

        def transcribe_file(self, path, *, lang=None):
            called["path"] = path
            called["lang"] = lang
            payload = type("Payload", (), {})()
            payload.ipa = "ipa"
            payload.tokens = ["i", "p", "a"]
            payload.lang = lang or "es"
            payload.audio = {"path": path}
            return payload

    monkeypatch.setattr(cli, "TranscriptionService", FakeService)
    audio = tmp_path / "dummy.wav"
    audio.write_bytes(b"\x00")

    tokens = cli.cli_transcribe(str(audio), lang="es", textref="espeak")

    assert tokens == ["i", "p", "a"]
    assert called["textref"] == "espeak"
    assert called["lang"] == "es"
