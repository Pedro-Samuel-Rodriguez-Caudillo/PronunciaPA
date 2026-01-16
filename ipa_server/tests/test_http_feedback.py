"""Tests for /v1/feedback endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from ipa_core.config.schema import AppConfig, PluginCfg
from ipa_server import main


def test_http_feedback_stub(monkeypatch) -> None:
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

    monkeypatch.setattr(main.loader, "load_config", lambda: cfg)
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
