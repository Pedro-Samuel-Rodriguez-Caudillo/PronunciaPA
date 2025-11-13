"""Tests para el endpoint /pronunciapa/transcribe."""
from __future__ import annotations

from fastapi.testclient import TestClient

from ipa_core.api.http import get_app
from tests.utils.audio import write_sine_wave


def test_transcribe_endpoint_with_file(monkeypatch, tmp_path):
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    client = TestClient(get_app())
    wav_path = write_sine_wave(tmp_path / "api.wav")

    with open(wav_path, "rb") as fh:
        response = client.post(
            "/pronunciapa/transcribe",
            files={"audio": ("api.wav", fh, "audio/wav")},
            data={"lang": "es"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ipa"] == "h o l a"
    assert data["tokens"] == ["h", "o", "l", "a"]


def test_transcribe_endpoint_requires_body():
    client = TestClient(get_app())

    response = client.post("/pronunciapa/transcribe")

    assert response.status_code == 400
    assert "cuerpo" in response.json()["detail"].lower()
