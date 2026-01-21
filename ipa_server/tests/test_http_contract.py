"""Pruebas de contrato para la API HTTP."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from ipa_server.main import get_app
from tests.utils.audio import write_sine_wave


@pytest.fixture
def client():
    """Crea un cliente de test después de configurar el entorno."""
    return TestClient(get_app())


def test_health_check(client) -> None:
    """Verifica el endpoint de salud."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_transcribe_stub(tmp_path, monkeypatch, client) -> None:
    """Verifica el stub del endpoint de transcripción."""
    wav_path = write_sine_wave(tmp_path / "transcribe.wav")
    with open(wav_path, "rb") as handle:
        audio_content = handle.read()
    files = {"audio": ("test.wav", audio_content, "audio/wav")}
    data = {"lang": "es"}
    response = client.post("/v1/transcribe", files=files, data=data)
    assert response.status_code == 200
    assert "tokens" in response.json()

def test_compare_stub(tmp_path, monkeypatch, client) -> None:
    """Verifica el stub del endpoint de comparación."""
    wav_path = write_sine_wave(tmp_path / "compare.wav")
    with open(wav_path, "rb") as handle:
        audio_content = handle.read()
    files = {"audio": ("test.wav", audio_content, "audio/wav")}
    data = {"text": "hola", "lang": "es"}
    response = client.post("/v1/compare", files=files, data=data)
    assert response.status_code == 200
    assert "per" in response.json()
