"""Tests para `TranscriptionService`."""
from __future__ import annotations

from ipa_core.services.transcription import TranscriptionService
from tests.utils.audio import write_sine_wave


def test_transcribe_file_with_stub(monkeypatch, tmp_path):
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    wav_path = write_sine_wave(tmp_path / "service.wav")

    service = TranscriptionService(default_lang="es")
    payload = service.transcribe_file(wav_path)

    assert payload.tokens == ["h", "o", "l", "a"]
    assert payload.ipa == "h o l a"
