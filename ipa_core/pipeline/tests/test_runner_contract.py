"""Pruebas de contrato del runner del pipeline (stub)."""
from __future__ import annotations

import pytest

from ipa_core.pipeline import runner


@pytest.mark.asyncio
async def test_run_pipeline_orchestration() -> None:
    """Verifica que run_pipeline orquesta las llamadas correctamente."""
    from unittest.mock import Mock, AsyncMock
    from ipa_core.types import AudioInput

    pre = Mock()
    # Must return a valid PreprocessorResult shape: {"audio": ..., "meta": {}}
    # Returning {"path": "processed"} was wrong — runner.py does
    # pre_audio_res.get("audio", audio) which would fall back to the raw input,
    # meaning preprocessing was never exercised.
    pre.process_audio = AsyncMock(return_value={
        "audio": {"path": "processed", "sample_rate": 16000, "channels": 1},
        "meta": {"preprocessor": "basic", "audio_valid": True},
    })
    pre.normalize_tokens = AsyncMock(return_value={"tokens": ["a"]})  # Mock normalize too

    asr = Mock()
    asr.transcribe = AsyncMock(return_value={"tokens": ["a"]})

    textref = Mock()
    textref.to_ipa = AsyncMock(return_value={"tokens": ["a"]})

    comp = Mock()
    comp.compare = AsyncMock(return_value={"per": 0.0})

    res = await runner.run_pipeline(
        pre=pre,
        asr=asr,
        textref=textref,
        comp=comp,
        audio={"path": "raw", "sample_rate": 16000, "channels": 1},
        text="a",
        lang="es"
    )

    pre.process_audio.assert_called_once()
    asr.transcribe.assert_called_once()
    textref.to_ipa.assert_called_once()
    comp.compare.assert_called_once()
    assert res["per"] == 0.0
