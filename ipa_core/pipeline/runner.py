"""Ejecución del pipeline de alto nivel.

Descripción
-----------
Define el contrato del orquestador de pasos del pipeline.

Patrones de diseño
------------------
- Template Method: secuencia estable de pasos con puntos de extensión.

Entrypoints
-----------
- execute_pipeline(): función unificada, soporta pack y sin pack, ambos niveles.
- run_pipeline(): wrapper delgado sobre execute_pipeline() (sin pack).
- run_pipeline_with_pack(): wrapper delgado sobre execute_pipeline() (con pack).
"""
from __future__ import annotations

from typing import Any, Optional

from ipa_core.errors import ValidationError
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import AudioInput, CompareResult, CompareWeights, Token
from ipa_core.phonology.representation import (
    PhonologicalRepresentation,
    RepresentationLevel,
    ComparisonResult,
)
from ipa_core.pipeline.transcribe import EvaluationMode
from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens, clean_textref_tokens
from ipa_core.compare.compare import compare_representations


async def execute_pipeline(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    comp: Optional[Comparator] = None,
    *,
    audio: AudioInput,
    text: str,
    lang: Optional[str] = None,
    pack=None,  # Optional LanguagePackPlugin
    mode: EvaluationMode = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
    weights: Optional[CompareWeights] = None,
) -> ComparisonResult:
    """Pipeline unificado: preproceso → ASR → TextRef → comparación.

    Soporta tanto el path con pack (derive/collapse) como sin pack.
    Aplica limpieza IPA en ambas rutas (ASR y TextRef).

    Parameters
    ----------
    pre : Preprocessor
    asr : ASRBackend
    textref : TextRefProvider
    comp : Comparator, optional
        Solo usado en el path sin pack (fallback a Levenshtein).
    audio : AudioInput
    text : str
    lang : str, optional
    pack : LanguagePackPlugin, optional
        Si se proporciona, usa derive/collapse y ScoringProfile.
    mode : EvaluationMode
    evaluation_level : RepresentationLevel
    weights : CompareWeights, optional

    Returns
    -------
    ComparisonResult
    """
    lang = lang or ""

    # 1. Preproceso de audio (cadena completa si BasicPreprocessor tiene audio_chain)
    pre_audio_res = await pre.process_audio(audio)
    processed_audio = pre_audio_res.get("audio", audio)

    # 2. ASR → tokens limpios → normalización → representación fonética
    asr_result = await asr.transcribe(processed_audio, lang=lang or None)
    raw_asr_tokens = asr_result.get("tokens")
    if not raw_asr_tokens:
        raise ValidationError("ASR no devolvió tokens IPA")
    cleaned_asr = clean_asr_tokens(raw_asr_tokens, lang=lang)
    if not cleaned_asr:
        raise ValidationError("ASR no devolvió tokens IPA válidos tras limpieza")
    norm_asr = await pre.normalize_tokens(cleaned_asr)
    asr_tokens = norm_asr.get("tokens", cleaned_asr)
    observed_phonetic = PhonologicalRepresentation.phonetic("".join(asr_tokens))

    # 3. TextRef → tokens limpios → normalización → representación fonémica
    tr_result = await textref.to_ipa(text, lang=lang or "")
    raw_ref_tokens = tr_result.get("tokens", [])
    cleaned_ref = clean_textref_tokens(raw_ref_tokens, lang=lang)
    norm_ref = await pre.normalize_tokens(cleaned_ref)
    ref_tokens = norm_ref.get("tokens", cleaned_ref)
    target_phonemic = PhonologicalRepresentation.phonemic("".join(ref_tokens))

    # 4. Alinear al nivel solicitado
    if evaluation_level == "phonemic":
        if pack is not None:
            collapsed_ipa = pack.collapse(observed_phonetic.ipa, mode=mode)
            observed_repr = PhonologicalRepresentation.phonemic(collapsed_ipa)
        else:
            observed_repr = PhonologicalRepresentation.phonemic(observed_phonetic.ipa)
        target_repr = target_phonemic
    else:  # phonetic
        if pack is not None:
            derived_ipa = pack.derive(target_phonemic.ipa, mode=mode)
            target_repr = PhonologicalRepresentation.phonetic(derived_ipa)
        else:
            target_repr = PhonologicalRepresentation.phonetic(target_phonemic.ipa)
        observed_repr = observed_phonetic

    # 5. Comparar con ScoringProfile del pack o defaults
    profile = pack.get_scoring_profile(mode) if pack is not None else None

    return await compare_representations(
        target_repr,
        observed_repr,
        mode=mode,
        evaluation_level=evaluation_level,
        profile=profile,
    )


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
    """Orquestar preproceso → ASR → TextRef → Comparación (Asíncrono).

    Wrapper compatible que usa el comparador ``comp`` proporcionado.
    Para el pipeline unificado con packs, usar ``execute_pipeline()``.
    """
    lang = lang or ""
    # 1. Preproceso de audio
    pre_audio_res = await pre.process_audio(audio)
    processed_audio = pre_audio_res.get("audio", audio)

    # 2. Transcripción ASR
    asr_result = await asr.transcribe(processed_audio, lang=lang or None)

    # 3. Resolución y normalización de hipótesis
    hyp_tokens = await _resolve_hyp_tokens(pre, asr_result, lang=lang)

    # 4. Obtención, limpieza y normalización de referencia
    tr_result = await textref.to_ipa(text, lang=lang or "")
    ref_tokens_raw = clean_textref_tokens(tr_result.get("tokens", []), lang=lang)
    ref_pre_res = await pre.normalize_tokens(ref_tokens_raw)
    ref_tokens = ref_pre_res.get("tokens", [])

    # 5. Comparación usando el comparador inyectado
    return await comp.compare(ref_tokens, hyp_tokens, weights=weights)


async def run_pipeline_with_pack(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    *,
    audio: AudioInput,
    text: str,
    pack,
    lang: Optional[str] = None,
    mode: EvaluationMode = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
) -> ComparisonResult:
    """Wrapper delgado sobre execute_pipeline() con pack.

    Mantiene compatibilidad con código existente.
    """
    if pack is None:
        raise ValidationError("Language pack requerido para run_pipeline_with_pack")

    return await execute_pipeline(
        pre, asr, textref,
        audio=audio, text=text, lang=lang,
        pack=pack, mode=mode, evaluation_level=evaluation_level,
    )


__all__ = [
    "execute_pipeline",
    "run_pipeline",
    "run_pipeline_with_pack",
]


async def _resolve_hyp_tokens(
    pre: Preprocessor,
    asr_result: dict[str, Any],
    lang: Optional[str] = None,
) -> list[Token]:
    """Extrae, limpia y normaliza tokens IPA del ASR (usado internamente)."""
    tokens = asr_result.get("tokens")
    if tokens:
        tokens = clean_asr_tokens(tokens, lang=lang)
        res = await pre.normalize_tokens(tokens)
        return res.get("tokens", [])
    raise ValidationError("ASR no devolvió tokens IPA")
