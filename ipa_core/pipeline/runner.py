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

from typing import Any, Optional

from ipa_core.errors import ValidationError
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import AudioInput, CompareResult, CompareWeights, Token


async def run_pipeline(
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
    """Orquestar preproceso -> ASR -> TextRef -> Comparación (Asíncrono)."""
    lang = lang or ""
    # 1. Preproceso de audio
    pre_audio_res = await pre.process_audio(audio)
    processed_audio = pre_audio_res.get("audio", audio)

    # 2. Transcripción ASR
    asr_result = await asr.transcribe(processed_audio, lang=lang or None)

    # 3. Resolución y normalización de hipótesis
    hyp_tokens = await _resolve_hyp_tokens(pre, asr_result)

    # 4. Obtención y normalización de referencia
    tr_result = await textref.to_ipa(text, lang=lang or "")
    ref_pre_res = await pre.normalize_tokens(tr_result.get("tokens", []))
    ref_tokens = ref_pre_res.get("tokens", [])

    # 5. Comparación
    return await comp.compare(ref_tokens, hyp_tokens, weights=weights)


async def _resolve_hyp_tokens(
    pre: Preprocessor,
    asr_result: dict[str, Any],
) -> list[Token]:
    """Extrae y normaliza tokens IPA del ASR."""
    tokens = asr_result.get("tokens")
    if tokens:
        res = await pre.normalize_tokens(tokens)
        return res.get("tokens", [])
    raise ValidationError("ASR no devolvió tokens IPA")
