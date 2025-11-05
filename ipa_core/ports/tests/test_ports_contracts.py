"""Pruebas de contrato para puertos (Protocol stubs).

Nota: se validan nombres de métodos esperados; no se instancian implementaciones.
"""
from __future__ import annotations

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider


def test_asr_backend_contract() -> None:
    assert hasattr(ASRBackend, "transcribe")


def test_textref_provider_contract() -> None:
    assert hasattr(TextRefProvider, "to_ipa")


def test_preprocessor_contract() -> None:
    assert hasattr(Preprocessor, "process_audio")
    assert hasattr(Preprocessor, "normalize_tokens")


def test_comparator_contract() -> None:
    assert hasattr(Comparator, "compare")

