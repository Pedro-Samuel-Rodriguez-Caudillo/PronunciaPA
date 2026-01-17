"""Pruebas de contrato para la API HTTP."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from ipa_server.main import get_app
from tests.utils.audio import write_sine_wave

client = TestClient(get_app())

def test_health_check() -> None:
    """Verifica el endpoint de salud."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_transcribe_stub(tmp_path, monkeypatch) -> None:
    """Verifica el stub del endpoint de transcripción."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    wav_path = write_sine_wave(tmp_path / "transcribe.wav")
    with open(wav_path, "rb") as handle:
        files = {"audio": ("test.wav", handle, "audio/wav")}
    data = {"lang": "es"}
    response = client.post("/v1/transcribe", files=files, data=data)
    assert response.status_code == 200
    assert "tokens" in response.json()

def test_compare_stub(tmp_path, monkeypatch) -> None:
    """Verifica el stub del endpoint de comparación."""
    monkeypatch.setenv("PRONUNCIAPA_BACKEND_NAME", "stub")
    wav_path = write_sine_wave(tmp_path / "compare.wav")
    with open(wav_path, "rb") as handle:
        files = {"audio": ("test.wav", handle, "audio/wav")}
    data = {"text": "hola", "lang": "es"}
    response = client.post("/v1/compare", files=files, data=data)
    assert response.status_code == 200
    assert "per" in response.json()
