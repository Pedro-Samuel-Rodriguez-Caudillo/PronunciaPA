"""Pruebas de contrato para tipos compartidos.

Propósito
---------
Verificar que los tipos públicos existen y exponen las claves esperadas.
"""
from __future__ import annotations
import pytest
from ipa_core import types as T

def test_audio_input_contract() -> None:
    """Verifica la estructura de AudioInput."""
    # Debe ser instanciable como TypedDict
    ai = T.AudioInput(path="test.wav", sample_rate=16000, channels=1)
    assert ai["path"] == "test.wav"
    assert ai["sample_rate"] == 16000
    assert ai["channels"] == 1

def test_asr_result_contract() -> None:
    """Verifica la estructura de ASRResult."""
    ar = T.ASRResult(
        tokens=["a", "b"], 
        raw_text="ab", 
        time_stamps=[(0.0, 0.1)], 
        meta={"confidence": 0.9}
    )
    assert ar["tokens"] == ["a", "b"]
    assert ar["raw_text"] == "ab"
    assert ar["time_stamps"] == [(0.0, 0.1)]
    assert ar["meta"]["confidence"] == 0.9

def test_compare_result_contract() -> None:
    """Verifica la estructura de CompareResult y sus subtipos."""
    op: T.EditOp = {"op": "eq", "ref": "a", "hyp": "a"}
    
    cr = T.CompareResult(
        per=0.0, 
        ops=[op], 
        alignment=[("a", "a")], 
        meta={}
    )
    assert cr["per"] == 0.0
    assert cr["ops"][0]["op"] == "eq"
    assert cr["alignment"][0] == ("a", "a")