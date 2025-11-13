"""Ejecución del pipeline de alto nivel.

Descripción
-----------
Define el contrato del orquestador de pasos del pipeline.

Estado: Implementación pendiente (expone entradas y salidas del proceso).

Patrones de diseño
------------------
- Template Method: secuencia estable de pasos con puntos de extensión.
- Observer: hooks opcionales de progreso/telemetría (a definir).

TODO
----
- Definir una interfaz de `hooks` para inicio/fin de paso, métricas y errores.
- Acordar manejo de `lang=None` (propagar desde configuración o requerirlo).
- Asegurar inmutabilidad de `AudioInput` y de tokens a lo largo del pipeline.
"""
from __future__ import annotations

from typing import Optional

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import AudioInput, CompareResult, CompareWeights, TokenSeq


def run_pipeline(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    comp: Comparator,
    *,
    audio: AudioInput,
    text: str,
    lang: Optional[str] = None,
    weights: Optional[CompareWeights] = None,
) -> CompareResult:
    """Orquestar preproceso -> ASR -> TextRef -> Comparación."""
    lang = lang or ""
    processed_audio = pre.process_audio(audio)
    asr_result = asr.transcribe(processed_audio, lang=lang or None)

    hyp_tokens = _resolve_hyp_tokens(pre, textref, asr_result, lang)
    ref_tokens = pre.normalize_tokens(textref.to_ipa(text, lang=lang or ""))

    return comp.compare(ref_tokens, hyp_tokens, weights=weights)


def _resolve_hyp_tokens(
    pre: Preprocessor,
    textref: TextRefProvider,
    asr_result,
    lang: str,
) -> list[str]:
    tokens: Optional[TokenSeq] = asr_result.get("tokens")
    if tokens:
        return pre.normalize_tokens(tokens)

    raw_text = asr_result.get("raw_text", "")
    if raw_text:
        derived = textref.to_ipa(raw_text, lang=lang or "")
        return pre.normalize_tokens(derived)

    return []
