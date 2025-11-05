"""Pruebas de contrato para tipos compartidos.

Propósito
---------
Verificar que los tipos públicos existen y exponen las claves esperadas.
"""
from __future__ import annotations

from ipa_core import types as T


def test_compare_result_contract_keys() -> None:
    cr = T.CompareResult(per=0.0, ops=[], alignment=[], meta={})
    assert set(cr.keys()) >= {"per", "ops", "alignment", "meta"}


def test_asr_result_contract_keys() -> None:
    ar = T.ASRResult(tokens=[], raw_text="", time_stamps=[], meta={})
    assert set(ar.keys()) >= {"tokens", "raw_text"}

