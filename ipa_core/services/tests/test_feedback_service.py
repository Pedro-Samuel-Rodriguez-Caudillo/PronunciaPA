"""Tests for FeedbackService using stub LLM."""
from __future__ import annotations

import pytest

from ipa_core.config.schema import AppConfig, PluginCfg
from ipa_core.kernel.core import create_kernel
from ipa_core.services.feedback import FeedbackService


@pytest.mark.asyncio
async def test_feedback_service_with_stub_llm() -> None:
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
    kernel = create_kernel(cfg)
    service = FeedbackService(kernel)
    audio = {"path": "dummy.wav", "sample_rate": 16000, "channels": 1}

    await kernel.setup()
    try:
        result = await service.analyze(audio=audio, text="hola", lang="es")
    finally:
        await kernel.teardown()

    assert result["feedback"]["summary"] == "ok"
    assert result["compare"]["per"] >= 0.0
