"""Pruebas de contrato para puertos (Protocol stubs).

Valida que los puertos definan los métodos asíncronos y el ciclo de vida
requerido por el microkernel.
"""
from __future__ import annotations

import inspect
from typing import Any

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.ports.tts import TTSProvider
from ipa_core.ports.llm import LLMAdapter


def _assert_async_method(cls: Any, method_name: str) -> None:
    assert hasattr(cls, method_name), f"{cls.__name__} debe tener el método {method_name}"
    method = getattr(cls, method_name)
    # En protocolos, los métodos con '...' suelen detectarse como funciones normales
    # a menos que se use inspect.iscoroutinefunction en la definición async.
    assert inspect.iscoroutinefunction(method), f"{cls.__name__}.{method_name} debe ser async"


def _assert_lifecycle(cls: Any) -> None:
    _assert_async_method(cls, "setup")
    _assert_async_method(cls, "teardown")


def test_asr_backend_contract() -> None:
    """Valida el contrato de ASRBackend."""
    _assert_lifecycle(ASRBackend)
    _assert_async_method(ASRBackend, "transcribe")


def test_textref_provider_contract() -> None:
    """Valida el contrato de TextRefProvider."""
    _assert_lifecycle(TextRefProvider)
    _assert_async_method(TextRefProvider, "to_ipa")


def test_preprocessor_contract() -> None:
    """Valida el contrato de Preprocessor."""
    _assert_lifecycle(Preprocessor)
    _assert_async_method(Preprocessor, "process_audio")
    _assert_async_method(Preprocessor, "normalize_tokens")


def test_comparator_contract() -> None:
    """Valida el contrato de Comparator."""
    _assert_lifecycle(Comparator)
    _assert_async_method(Comparator, "compare")


def test_tts_provider_contract() -> None:
    """Valida el contrato de TTSProvider."""
    _assert_lifecycle(TTSProvider)
    _assert_async_method(TTSProvider, "synthesize")


def test_llm_adapter_contract() -> None:
    """Valida el contrato de LLMAdapter."""
    _assert_lifecycle(LLMAdapter)
    _assert_async_method(LLMAdapter, "complete")


def test_protocols_are_runtime_checkable() -> None:
    """Valida que los protocolos permitan comprobación en tiempo de ejecución."""
    class Dummy:
        async def setup(self): pass
        async def teardown(self): pass
        async def transcribe(self, audio, **kw): pass
        async def to_ipa(self, text, **kw): pass
        async def compare(self, ref, hyp, **kw): pass
        async def process_audio(self, audio, **kw): pass
        async def normalize_tokens(self, tokens, **kw): pass
        async def synthesize(self, text, **kw): pass
        async def complete(self, prompt, **kw): pass

    d = Dummy()
    # Nota: isinstance con Protocol requiere que coincidan las firmas o al menos los nombres.
    # runtime_checkable permite esto.
    from typing import runtime_checkable
    assert isinstance(d, ASRBackend)
    assert isinstance(d, TextRefProvider)
    assert isinstance(d, Comparator)
    assert isinstance(d, Preprocessor)
    assert isinstance(d, TTSProvider)
    assert isinstance(d, LLMAdapter)
