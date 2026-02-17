"""Tests for learning/lesson endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ipa_server.main import get_app
from ipa_server.routers import ipa_catalog as ipa_catalog_router


class _DummyTTS:
    async def setup(self) -> None:
        return None

    async def teardown(self) -> None:
        return None

    async def synthesize(self, text: str, *, lang: str, output_path: str, **kw) -> dict:
        # Minimal WAV header so FileResponse has a valid file.
        wav_bytes = (
            b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little")
            + (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
            + (16000).to_bytes(4, "little") + (32000).to_bytes(4, "little")
            + (2).to_bytes(2, "little") + (16).to_bytes(2, "little")
            + b"data" + (0).to_bytes(4, "little")
        )
        Path(output_path).write_bytes(wav_bytes)
        return {"audio": {"path": output_path, "sample_rate": 16000, "channels": 1}, "meta": {"backend": "dummy"}}


def test_http_ipa_lesson_success() -> None:
    """Verifica que /api/ipa-lesson retorna una lección válida."""
    client = TestClient(get_app())
    response = client.get("/api/ipa-lesson/es/a?include_audio=true&generate=false")
    assert response.status_code == 200
    data = response.json()
    assert data["sound_id"] == "es/a"
    assert data["ipa"] == "a"
    assert data["drills"]
    if data.get("audio_examples"):
        assert "audio_url" in data["audio_examples"][0]


def test_http_ipa_lesson_fallback_drills() -> None:
    """Verifica que sonidos sin drills en learning usan contextos básicos."""
    client = TestClient(get_app())
    response = client.get("/api/ipa-lesson/es/i?generate=false")
    assert response.status_code == 200
    data = response.json()
    assert data["ipa"] == "i"
    assert data["drills"]
    assert data["drills"][0]["type"].startswith("word_")


def test_http_ipa_lesson_not_found() -> None:
    """Verifica que /api/ipa-lesson retorna 404 para sonidos inexistentes."""
    client = TestClient(get_app())
    response = client.get("/api/ipa-lesson/es/zzz")
    assert response.status_code == 404


def test_http_ipa_sound_audio_unicode_sound_id_headers_safe(monkeypatch) -> None:
    """Unicode IPA en sound_id no debe romper headers/filename."""
    monkeypatch.setattr(ipa_catalog_router.loader, "load_config", lambda: type("Cfg", (), {"tts": type("T", (), {"name": "dummy", "params": {}})()})())
    monkeypatch.setattr(ipa_catalog_router.registry, "resolve_tts", lambda *_args, **_kw: _DummyTTS())

    client = TestClient(get_app())
    response = client.get("/api/ipa-sounds/audio", params={"sound_id": "en/tʃ"})
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("audio/wav")
    assert "filename=" in response.headers.get("content-disposition", "")
