"""Tests for /v1/feedback endpoint."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from ipa_core.config.schema import AppConfig, PluginCfg
from ipa_server import main
from ipa_server.routers import pipeline as pipeline_router


# Check if model pack exists for integration tests
MODEL_PACK_PATH = "data/models/model_pack"
HAS_MODEL_PACK = os.path.exists(MODEL_PACK_PATH)


@pytest.mark.skipif(not HAS_MODEL_PACK, reason="Model pack not found - integration test requires real model_pack")
class TestFeedbackEndpointSuccess:
    """Tests for successful /v1/feedback requests."""

    def test_feedback_with_stub_llm_returns_200(self, monkeypatch) -> None:
        """Test that /v1/feedback returns 200 with valid stub LLM."""
        payload = {
            "summary": "ok",
            "advice_short": "short",
            "advice_long": "long",
            "drills": [{"type": "minimal_pair", "text": "la ra"}],
        }
        cfg = AppConfig(
            backend=PluginCfg(name="test_ipa"),
            textref=PluginCfg(name="grapheme"),
            comparator=PluginCfg(name="levenshtein"),
            preprocessor=PluginCfg(name="basic"),
            llm=PluginCfg(name="stub", params={"payload": payload}),
            model_pack="model/qwen2.5-7b-instruct",
        )

        monkeypatch.setattr(pipeline_router.loader, "load_config", lambda: cfg)
        client = TestClient(main.get_app())
        response = client.post(
            "/v1/feedback",
            files={"audio": ("test.wav", b"fake", "audio/wav")},
            data={"text": "hola", "lang": "es"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
        assert data["feedback"]["summary"] == "ok"
        assert "report" in data
        assert "compare" in data

    def test_feedback_response_structure(self, monkeypatch) -> None:
        """Test that /v1/feedback returns all expected fields."""
        payload = {
            "advice_short": "Good",
            "advice_long": "Very good",
            "drills": [],
        }
        cfg = AppConfig(
            backend=PluginCfg(name="test_ipa"),
            textref=PluginCfg(name="grapheme"),
            comparator=PluginCfg(name="levenshtein"),
            preprocessor=PluginCfg(name="basic"),
            llm=PluginCfg(name="stub", params={"payload": payload}),
            model_pack="model/qwen2.5-7b-instruct",
        )

        monkeypatch.setattr(pipeline_router.loader, "load_config", lambda: cfg)
        client = TestClient(main.get_app())
        response = client.post(
            "/v1/feedback",
            files={"audio": ("test.wav", b"fake", "audio/wav")},
            data={"text": "casa", "lang": "es"},
        )

        assert response.status_code == 200
        data = response.json()
        
        # Check report structure
        assert "target_text" in data["report"]
        assert "target_ipa" in data["report"]
        assert "observed_ipa" in data["report"]
        
        # Check compare structure
        assert "per" in data["compare"] or "ops" in data["compare"]


class TestFeedbackEndpointValidation:
    """Tests for /v1/feedback parameter validation."""

    def test_feedback_missing_text_returns_422(self, monkeypatch) -> None:
        """Test that /v1/feedback returns 422 when text is missing."""
        cfg = AppConfig(
            backend=PluginCfg(name="test_ipa"),
            textref=PluginCfg(name="grapheme"),
            comparator=PluginCfg(name="levenshtein"),
            preprocessor=PluginCfg(name="basic"),
            llm=PluginCfg(name="stub", params={"payload": {}}),
            model_pack="model/qwen2.5-7b-instruct",
        )

        monkeypatch.setattr(pipeline_router.loader, "load_config", lambda: cfg)
        client = TestClient(main.get_app())
        response = client.post(
            "/v1/feedback",
            files={"audio": ("test.wav", b"fake", "audio/wav")},
            data={"lang": "es"},  # missing text
        )

        assert response.status_code == 422

    def test_feedback_missing_audio_returns_422(self, monkeypatch) -> None:
        """Test that /v1/feedback returns 422 when audio is missing."""
        cfg = AppConfig(
            backend=PluginCfg(name="test_ipa"),
            textref=PluginCfg(name="grapheme"),
            comparator=PluginCfg(name="levenshtein"),
            preprocessor=PluginCfg(name="basic"),
            llm=PluginCfg(name="stub", params={"payload": {}}),
            model_pack="model/qwen2.5-7b-instruct",
        )

        monkeypatch.setattr(pipeline_router.loader, "load_config", lambda: cfg)
        client = TestClient(main.get_app())
        response = client.post(
            "/v1/feedback",
            data={"text": "hola", "lang": "es"},  # missing audio
        )

        assert response.status_code == 422


class TestFeedbackEndpointErrors:
    """Tests for /v1/feedback error handling."""

    def test_feedback_without_explicit_llm_uses_rule_based(self, monkeypatch) -> None:
        """Cuando no hay LLM explícito, el kernel usa rule_based como fallback
        para que /v1/feedback siempre genere consejos sin necesidad de un modelo
        descargado.  El endpoint debe llegar hasta el ASR (que con audio inválido
        devuelve 422 o 503/400 del quality gate) — nunca un 503 de 'LLM not ready'.
        """
        cfg = AppConfig(
            backend=PluginCfg(name="test_ipa"),
            textref=PluginCfg(name="grapheme"),
            comparator=PluginCfg(name="levenshtein"),
            preprocessor=PluginCfg(name="basic"),
            # LLM no especificado → kernel auto-selecciona rule_based
        )

        monkeypatch.setattr(pipeline_router.loader, "load_config", lambda: cfg)
        client = TestClient(main.get_app())
        response = client.post(
            "/v1/feedback",
            files={"audio": ("test.wav", b"fake", "audio/wav")},
            data={"text": "hola", "lang": "es"},
        )

        # El error puede ser de calidad de audio o de ASR, pero NO de LLM no configurado
        assert response.status_code != 503 or "not_ready" not in response.json().get("type", "llm")


def test_feedback_rejects_stub_backend(monkeypatch) -> None:
    """Test that /v1/feedback blocks StubASR with asr_unavailable."""
    cfg = AppConfig(
        backend=PluginCfg(name="stub"),
        textref=PluginCfg(name="grapheme"),
        comparator=PluginCfg(name="levenshtein"),
        preprocessor=PluginCfg(name="basic"),
    )

    monkeypatch.setattr(pipeline_router.loader, "load_config", lambda: cfg)
    client = TestClient(main.get_app())
    response = client.post(
        "/v1/feedback",
        files={"audio": ("test.wav", b"fake", "audio/wav")},
        data={"text": "hola", "lang": "es"},
    )

    assert response.status_code == 503
    data = response.json()
    assert data["type"] == "asr_unavailable"
    assert data["backend"] == "StubASR"

