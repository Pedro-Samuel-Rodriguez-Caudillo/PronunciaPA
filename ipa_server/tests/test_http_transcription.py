"""Tests para los endpoints de transcripción y comparación."""
from __future__ import annotations
import os
import pytest
from fastapi.testclient import TestClient
from ipa_server.main import get_app
from tests.utils.audio import write_sine_wave

@pytest.fixture
def client():
    return TestClient(get_app())

def test_http_transcribe_success(client, monkeypatch, tmp_path) -> None:
    """Verifica que /v1/transcribe funciona con ASR IPA de pruebas."""
    wav_path = write_sine_wave(tmp_path / "http_transcribe.wav")
    with open(wav_path, "rb") as f:
        audio_content = f.read()
    response = client.post(
        "/v1/transcribe",
        files={"audio": ("test.wav", audio_content, "audio/wav")},
        data={"lang": "es"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "ipa" in data
    assert data["tokens"] == ["h", "o", "l", "a"]
    assert data["meta"]["backend"] == "test_ipa"


def test_http_transcribe_uses_config_default_lang_when_missing(client, tmp_path) -> None:
    """Si no se envía lang, usa el default del config de test."""
    wav_path = write_sine_wave(tmp_path / "http_transcribe_default_lang.wav")
    with open(wav_path, "rb") as f:
        audio_content = f.read()

    response = client.post(
        "/v1/transcribe",
        files={"audio": ("test.wav", audio_content, "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["lang"] == "es"

def test_http_textref_success(client) -> None:
    """Verifica que /v1/textref convierte texto a IPA."""
    response = client.post(
        "/v1/textref",
        data={"text": "Hola", "lang": "es", "textref": "grapheme"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tokens"] == ["h", "o", "l", "a"]
    assert data["ipa"] == "h o l a"
    assert data["meta"]["method"] == "grapheme"

def test_http_compare_success(client, monkeypatch, tmp_path) -> None:
    """Verifica que /v1/compare funciona con ASR IPA de pruebas."""
    wav_path = write_sine_wave(tmp_path / "http_compare.wav")
    with open(wav_path, "rb") as f:
        audio_content = f.read()
    response = client.post(
        "/v1/compare",
        files={"audio": ("test.wav", audio_content, "audio/wav")},
        data={"text": "hola", "lang": "es"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "per" in data
    assert isinstance(data["per"], float)
    assert 0.0 <= data["per"] <= 1.0
    assert len(data["alignment"]) > 0


def test_http_transcribe_rejects_stub_backend(client, monkeypatch, tmp_path) -> None:
    """Bloquea /v1/transcribe cuando se activa StubASR."""
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    wav_path = write_sine_wave(tmp_path / "http_transcribe_stub.wav")
    with open(wav_path, "rb") as f:
        audio_content = f.read()

    response = client.post(
        "/v1/transcribe",
        files={"audio": ("test.wav", audio_content, "audio/wav")},
        data={"lang": "es"},
    )

    assert response.status_code == 503
    data = response.json()
    assert data["type"] == "asr_unavailable"
    assert data["backend"] == "StubASR"


def test_http_compare_rejects_stub_backend(client, monkeypatch, tmp_path) -> None:
    """Bloquea /v1/compare cuando se activa StubASR."""
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    wav_path = write_sine_wave(tmp_path / "http_compare_stub.wav")
    with open(wav_path, "rb") as f:
        audio_content = f.read()

    response = client.post(
        "/v1/compare",
        files={"audio": ("test.wav", audio_content, "audio/wav")},
        data={"text": "hola", "lang": "es"},
    )

    assert response.status_code == 503
    data = response.json()
    assert data["type"] == "asr_unavailable"
    assert data["backend"] == "StubASR"


def test_http_quick_compare_rejects_stub_backend(client, monkeypatch, tmp_path) -> None:
    """Bloquea /v1/quick-compare cuando se activa StubASR."""
    monkeypatch.setenv("PRONUNCIAPA_ASR", "stub")
    wav_path = write_sine_wave(tmp_path / "http_quick_compare_stub.wav")
    with open(wav_path, "rb") as f:
        audio_content = f.read()

    response = client.post(
        "/v1/quick-compare",
        files={"audio": ("test.wav", audio_content, "audio/wav")},
        data={"text": "hola", "lang": "es"},
    )

    assert response.status_code == 503
    data = response.json()
    assert data["type"] == "asr_unavailable"
    assert data["backend"] == "StubASR"

def test_http_validation_error(client, monkeypatch) -> None:
    """Verifica el manejo de ValidationError."""
    # Podríamos forzar un ValidationError si el kernel lo lanza
    # Por ahora, si no pasamos 'text' en compare, FastAPI lanzará un 422 (Pydantic de FastAPI)
    # Pero queremos probar nuestro handler de Kernel ValidationError.
    # Como los stubs no lanzan ValidationError fácilmente sin lógica extra,
    # probaremos el 422 de FastAPI o simularemos uno.
    response = client.post(
        "/v1/compare",
        files={"audio": ("test.wav", b"fake", "audio/wav")},
        data={"lang": "es"} # Missing 'text'
    )
    assert response.status_code == 422 # FastAPI default for missing form fields

def test_http_transcribe_unsupported_audio(client, monkeypatch) -> None:
    """Verifica el manejo de audio inválido con error 415."""
    response = client.post(
        "/v1/transcribe",
        files={"audio": ("bad.wav", b"not a wav", "audio/wav")},
        data={"lang": "es"},
    )
    assert response.status_code == 415
    data = response.json()
    assert data["type"] == "unsupported_format"
