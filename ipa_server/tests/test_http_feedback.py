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
            backend=PluginCfg(name="stub"),
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
            backend=PluginCfg(name="stub"),
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
            backend=PluginCfg(name="stub"),
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
            backend=PluginCfg(name="stub"),
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

    def test_feedback_without_llm_config_returns_503(self, monkeypatch) -> None:
        """Test that /v1/feedback returns 503 when LLM is not configured."""
        cfg = AppConfig(
            backend=PluginCfg(name="stub"),
            textref=PluginCfg(name="grapheme"),
            comparator=PluginCfg(name="levenshtein"),
            preprocessor=PluginCfg(name="basic"),
            # No LLM configured
        )

        monkeypatch.setattr(pipeline_router.loader, "load_config", lambda: cfg)
        client = TestClient(main.get_app())
        response = client.post(
            "/v1/feedback",
            files={"audio": ("test.wav", b"fake", "audio/wav")},
            data={"text": "hola", "lang": "es"},
        )

        assert response.status_code == 503
        assert "not_ready" in response.json().get("type", "")

