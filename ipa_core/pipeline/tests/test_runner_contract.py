"""Pruebas de contrato del runner del pipeline (stub)."""
from __future__ import annotations

import pytest

from ipa_core.pipeline import runner


def test_run_pipeline_orchestration() -> None:
    """Verifica que run_pipeline orquesta las llamadas correctamente."""
    from unittest.mock import Mock
    from ipa_core.types import AudioInput

    pre = Mock()
    pre.process_audio.return_value = {"path": "processed"}
    
    asr = Mock()
    asr.transcribe.return_value = {"tokens": ["a"]}
    
    textref = Mock()
    textref.to_ipa.return_value = ["a"]
    
    comp = Mock()
    comp.compare.return_value = {"per": 0.0}
    
    res = runner.run_pipeline(
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

