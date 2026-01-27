"""Tests for FeedbackService using stub LLM."""
from __future__ import annotations

import pytest
from pathlib import Path

from ipa_core.config.schema import AppConfig, PluginCfg
from ipa_core.kernel.core import create_kernel
from ipa_core.services.feedback import FeedbackService


import yaml

@pytest.mark.asyncio
async def test_feedback_service_with_stub_llm(tmp_path: Path) -> None:
    # 1. Crear un model pack temporal
    pack_dir = tmp_path / "stub_model_pack"
    pack_dir.mkdir()
    
    manifest = {
        "id": "stub-pack",
        "version": "1.0.0",
        "runtime": {"kind": "stub", "params": {}},
        "files": [{"path": "model.bin"}],
        "prompt": {"path": "prompt.txt"},
        "output_schema": {"path": "schema.json"}
    }
    with open(pack_dir / "manifest.yaml", "w") as f:
        yaml.dump(manifest, f)
    
    (pack_dir / "model.bin").touch()
    (pack_dir / "prompt.txt").write_text("You are a pronunciation coach.")
    
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "advice_short": {"type": "string"},
            "advice_long": {"type": "string"},
            "drills": {"type": "array"}
        },
        "required": ["summary", "advice_short", "advice_long", "drills"]
    }
    import json
    with open(pack_dir / "schema.json", "w") as f:
        json.dump(schema, f)
    
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
        model_pack=str(pack_dir),
    )
    kernel = create_kernel(cfg)
    service = FeedbackService(kernel)
    audio = {"path": "dummy.wav", "sample_rate": 16000, "channels": 1}

    await kernel.setup()
    try:
        # Usar un mock para el preprocesador que retorne audio válido sin verificar archivo
        result = await service.analyze(audio=audio, text="hola", lang="es")
    finally:
        await kernel.teardown()

    assert result["feedback"]["summary"] == "ok"
    assert result["compare"]["per"] >= 0.0
