"""Resolución de plugins por nombre (stub).

Estado: Implementación pendiente (instanciación mediante factorías).

TODO (Issue #18)
----------------
- Resolver por nombre con alias y validación de compatibilidad de puertos.
- Permitir inyección de dependencias para pruebas (factory overrides).
- Gestionar versiones de plugins y fallbacks.
"""
from __future__ import annotations

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider


def resolve_asr(name: str, params: dict | None = None) -> ASRBackend:  # noqa: D401
    """Resuelve e instancia un backend ASR por nombre."""
    raise NotImplementedError("resolve_asr no implementado")


def resolve_textref(name: str, params: dict | None = None) -> TextRefProvider:  # noqa: D401
    """Resuelve e instancia un proveedor de texto->IPA por nombre."""
    raise NotImplementedError("resolve_textref no implementado")


def resolve_comparator(name: str, params: dict | None = None) -> Comparator:  # noqa: D401
    """Resuelve e instancia un comparador por nombre."""
    raise NotImplementedError("resolve_comparator no implementado")


def resolve_preprocessor(name: str, params: dict | None = None) -> Preprocessor:  # noqa: D401
    """Resuelve e instancia un preprocesador por nombre."""
    raise NotImplementedError("resolve_preprocessor no implementado")
