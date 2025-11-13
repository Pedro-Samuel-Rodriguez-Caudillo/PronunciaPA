"""Resolución de plugins por nombre (stub).

Estado: Implementación pendiente (instanciación mediante factorías).

TODO
----
- Resolver por nombre con alias y validar compatibilidad de puertos.
- Permitir inyección de dependencias para pruebas (factory overrides).
- Gestionar versiones de plugins y fallbacks de manera simple.
"""
from __future__ import annotations

from ipa_core.backends.asr_allosaurus import AllosaurusASR
from ipa_core.backends.asr_stub import StubASR
from ipa_core.compare.levenshtein import LevenshteinComparator
from ipa_core.compare.noop import NoOpComparator
from ipa_core.errors import PluginResolutionError
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.textref.epitran import EpitranTextRef
from ipa_core.textref.simple import GraphemeTextRef


def resolve_asr(name: str, params: dict | None = None) -> ASRBackend:  # noqa: D401
    """Resuelve e instancia un backend ASR por nombre."""
    if name in {"allosaurus", "default"}:
        return AllosaurusASR(params)
    if name in {"stub", "fake"}:
        return StubASR(params)
    raise PluginResolutionError(f"ASR '{name}' no registrado")


def resolve_textref(name: str, params: dict | None = None) -> TextRefProvider:  # noqa: D401
    """Resuelve e instancia un proveedor de texto->IPA por nombre."""
    if name in {"grapheme", "default"}:
        return GraphemeTextRef()
    if name == "epitran":
        lang = (params or {}).get("default_lang", "es")
        return EpitranTextRef(default_lang=lang)
    raise PluginResolutionError(f"TextRef '{name}' no registrado")


def resolve_comparator(name: str, params: dict | None = None) -> Comparator:  # noqa: D401
    """Resuelve e instancia un comparador por nombre."""
    if name in {"levenshtein", "default"}:
        return LevenshteinComparator()
    if name == "noop":
        return NoOpComparator()
    raise PluginResolutionError(f"Comparator '{name}' no registrado (pendiente)")


def resolve_preprocessor(name: str, params: dict | None = None) -> Preprocessor:  # noqa: D401
    """Resuelve e instancia un preprocesador por nombre."""
    if name in {"basic", "default"}:
        return BasicPreprocessor()
    raise PluginResolutionError(f"Preprocessor '{name}' no registrado")
