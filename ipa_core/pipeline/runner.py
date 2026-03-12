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

import logging
import os
from typing import Any, Optional, cast

from ipa_core.audio.quality_gates import quality_gate_error_code
from ipa_core.config import loader
from ipa_core.config.resolution import default_lang_from_config
from ipa_core.errors import ValidationError
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import ASRResult, AudioInput, CompareResult, CompareWeights, EditOp, PreprocessorResult, Token
from ipa_core.phonology.representation import (
    PhonologicalRepresentation,
    RepresentationLevel,
    ComparisonResult,
)
from ipa_core.pipeline.transcribe import EvaluationMode
from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens, clean_textref_tokens
from ipa_core.compare.compare import compare_representations
from ipa_core.compare.oov_handler import OOVHandler
from ipa_core.ports.oov import OOVHandlerPort

logger = logging.getLogger(__name__)


def _default_lang() -> str:
    """Return the canonical default language for TextRef when lang is None.

    Resolution order:
    1. Config options.lang
    2. Config backend.params.lang
    3. PRONUNCIAPA_DEFAULT_LANG
    4. "es"
    """
    default = default_lang_from_config()
    logger.debug("lang no especificado; usando default '%s' para TextRef", default)
    return default


# Issues que impiden llamar al ASR — el audio no tiene información fonética útil.
# Eliminados "too_short" y "clipping" de la lista de bloqueantes:
# - too_short: Allosaurus + padding interno maneja clips cortos; bloquear aquí
#   rechazaba grabaciones válidas de sílabas aisladas.
# - clipping: ffmpeg convierte a s16 con normalización; el clipping en el WAV
#   original ya no llega al ASR tras la conversión.
# LOW_SNR solo es una advertencia: el ASR puede intentarlo de todas formas.
_BLOCKING_QUALITY_ISSUES = {"no_speech", "too_quiet"}


def _quality_error_context(quality: dict[str, Any]) -> dict[str, object]:
    return {
        "issues": list(quality.get("issues", [])),
        "audio_quality": dict(quality),
    }


def _check_quality_gate(pre_res: PreprocessorResult) -> None:
    """Lanza ValidationError con feedback al usuario si la calidad es bloqueante.

    Solo bloquea en issues críticos (sin voz, demasiado silencioso, clipping,
    muy corto). LOW_SNR solo advierte: el ASR intentará de todas formas.
    """
    quality = pre_res.get("meta", {}).get("audio_quality")
    if not quality or quality.get("passed", True):
        return
    issues = set(quality.get("issues", []))
    if issues & _BLOCKING_QUALITY_ISSUES:
        msg = (
            quality.get("user_feedback")
            or "Audio de baja calidad: no se puede transcribir."
        )
        raise ValidationError(
            msg,
            error_code=cast(Optional[str], quality.get("error_code")) or quality_gate_error_code(list(issues)),
            context=_quality_error_context(cast(dict[str, Any], quality)),
        )


def _quality_enriched_error(pre_res: PreprocessorResult, fallback: str) -> ValidationError:
    """Retorna ValidationError usando feedback de calidad si está disponible."""
    quality = cast(dict[str, Any], pre_res.get("meta", {}).get("audio_quality", {}))
    feedback = quality.get("user_feedback")
    return ValidationError(
        cast(str, feedback or fallback),
        error_code=cast(Optional[str], quality.get("error_code")) or quality_gate_error_code(list(quality.get("issues", []))),
        context=_quality_error_context(quality) if quality else {},
    )


def _ops_from_alignment(alignment: list[tuple[Optional[str], Optional[str]]] | list[list[Optional[str]]]) -> list[EditOp]:
    """Reconstruye ops desde alignment cuando el comparador no las provee."""
    ops: list[EditOp] = []
    for pair in alignment:
        ref, hyp = pair
        if ref is None:
            op = "ins"
        elif hyp is None:
            op = "del"
        elif ref == hyp:
            op = "eq"
        else:
            op = "sub"
        ops.append({"op": op, "ref": ref, "hyp": hyp})
    return ops


def _normalization_params(pack: Any) -> dict[str, Any]:
    """Construye parámetros opcionales de normalización desde el pack."""
    if pack is not None and hasattr(pack, "get_inventory"):
        return {"inventory": pack.get_inventory()}
    return {}


async def _prepare_observed_phonetic(
    *,
    pre: Preprocessor,
    asr: ASRBackend,
    processed_audio: AudioInput,
    pre_audio_res: PreprocessorResult,
    lang: Optional[str],
    norm_params: dict[str, Any],
) -> tuple[PhonologicalRepresentation, list[Token], ASRResult]:
    """Ejecuta ASR, limpieza y normalización para obtener la hipótesis fonética."""
    asr_result = await asr.transcribe(processed_audio, lang=lang)
    raw_asr_tokens = asr_result.get("tokens")
    if not raw_asr_tokens:
        raise _quality_enriched_error(pre_audio_res, "ASR no devolvió tokens IPA")

    cleaned_asr = clean_asr_tokens(raw_asr_tokens, lang=lang)
    if not cleaned_asr:
        raise _quality_enriched_error(
            pre_audio_res,
            "ASR no devolvió tokens IPA válidos tras limpieza",
        )

    norm_asr = await pre.normalize_tokens(cleaned_asr, **norm_params)
    asr_tokens = norm_asr.get("tokens", cleaned_asr)
    observed_phonetic = PhonologicalRepresentation.phonetic("".join(asr_tokens))
    return observed_phonetic, asr_tokens, asr_result


async def _prepare_target_phonemic(
    *,
    pre: Preprocessor,
    textref: TextRefProvider,
    text: str,
    target_ipa: Optional[str],
    lang: str,
    evaluation_level: RepresentationLevel,
    norm_params: dict[str, Any],
) -> tuple[PhonologicalRepresentation, list[Token]]:
    """Convierte la referencia textual en representación fonémica normalizada."""
    if target_ipa and target_ipa.strip():
        raw_ref_tokens = [tok for tok in target_ipa.strip().split() if tok]
        if not raw_ref_tokens:
            raise ValidationError("target_ipa no contiene tokens IPA válidos")
    else:
        tr_result = await textref.to_ipa(text, lang=lang)
        raw_ref_tokens = tr_result.get("tokens", [])
    cleaned_ref = clean_textref_tokens(
        raw_ref_tokens,
        lang=lang,
        preserve_allophones=(evaluation_level == "phonetic"),
    )
    norm_ref = await pre.normalize_tokens(cleaned_ref, **norm_params)
    ref_tokens = norm_ref.get("tokens", cleaned_ref)
    target_phonemic = PhonologicalRepresentation.phonemic("".join(ref_tokens))
    return target_phonemic, ref_tokens


def _select_representations(
    *,
    pack: Any,
    mode: EvaluationMode,
    evaluation_level: RepresentationLevel,
    observed_phonetic: PhonologicalRepresentation,
    target_phonemic: PhonologicalRepresentation,
) -> tuple[PhonologicalRepresentation, PhonologicalRepresentation]:
    """Selecciona representaciones objetivo/observada según nivel y pack."""
    if evaluation_level == "phonemic":
        if pack is not None:
            collapsed_ipa = pack.collapse(observed_phonetic.ipa, mode=mode)
            observed_repr = PhonologicalRepresentation.phonemic(collapsed_ipa)
        else:
            observed_repr = PhonologicalRepresentation.phonemic(observed_phonetic.ipa)
        return target_phonemic, observed_repr

    if pack is not None:
        derived_ipa = pack.derive(target_phonemic.ipa, mode=mode)
        target_repr = PhonologicalRepresentation.phonetic(derived_ipa)
    else:
        target_repr = PhonologicalRepresentation.phonetic(target_phonemic.ipa)
    return target_repr, observed_phonetic


def _apply_oov_filter_if_needed(
    *,
    pack: Any,
    oov_handler: Optional[OOVHandlerPort],
    evaluation_level: RepresentationLevel,
    target_repr: PhonologicalRepresentation,
    observed_repr: PhonologicalRepresentation,
) -> tuple[PhonologicalRepresentation, PhonologicalRepresentation]:
    """Filtra segmentos OOV cuando el pack provee inventario fonético."""
    if pack is None or not hasattr(pack, "get_inventory"):
        return target_repr, observed_repr

    phonetic_inv = pack.get_inventory()
    raw_inventory = list(phonetic_inv.get_all_phones()) if phonetic_inv is not None else []
    if not raw_inventory:
        return target_repr, observed_repr

    active_oov = (
        oov_handler
        if oov_handler is not None
        else OOVHandler(raw_inventory, collapse_threshold=0.3, level=evaluation_level)
    )
    target_filtered = active_oov.filter_sequence(target_repr.segments)
    observed_filtered = active_oov.filter_sequence(observed_repr.segments)
    return (
        PhonologicalRepresentation(
            level=target_repr.level,
            ipa=target_repr.ipa,
            segments=target_filtered,
        ),
        PhonologicalRepresentation(
            level=observed_repr.level,
            ipa=observed_repr.ipa,
            segments=observed_filtered,
        ),
    )


async def execute_pipeline(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    comp: Optional[Comparator] = None,
    *,
    audio: AudioInput,
    text: str,
    target_ipa: Optional[str] = None,
    lang: Optional[str] = None,
    lang_source: Optional[str] = None,
    lang_target: Optional[str] = None,
    pack=None,  # Optional LanguagePackPlugin
    mode: EvaluationMode = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
    weights: Optional[CompareWeights] = None,
    oov_handler: Optional[OOVHandlerPort] = None,
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
    # Backward-compatible behavior:
    # - If only `lang` is provided, it is used for both source and target.
    # - `lang_source` and `lang_target` can override each side independently.
    source_lang = lang_source or lang
    target_lang = lang_target or lang or _default_lang()

    # 1. Preproceso de audio (cadena completa si BasicPreprocessor tiene audio_chain)
    pre_audio_res = await pre.process_audio(audio)
    processed_audio = pre_audio_res.get("audio", audio)

    try:
        # Bloquear temprano si la calidad impide cualquier reconocimiento útil.
        # Esto da al usuario feedback accionable en lugar de un error genérico de ASR.
        _check_quality_gate(pre_audio_res)

        # 2. ASR → tokens limpios → normalización → representación fonética
        norm_params = _normalization_params(pack)
        observed_phonetic, _asr_tokens, _asr_result = await _prepare_observed_phonetic(
            pre=pre,
            asr=asr,
            processed_audio=processed_audio,
            pre_audio_res=pre_audio_res,
            lang=source_lang,
            norm_params=norm_params,
        )

        # 3. TextRef → tokens limpios → normalización → representación fonémica
        target_phonemic, _ref_tokens = await _prepare_target_phonemic(
            pre=pre,
            textref=textref,
            text=text,
            target_ipa=target_ipa,
            lang=target_lang,
            evaluation_level=evaluation_level,
            norm_params=norm_params,
        )

        # 4. Alinear al nivel solicitado
        target_repr, observed_repr = _select_representations(
            pack=pack,
            mode=mode,
            evaluation_level=evaluation_level,
            observed_phonetic=observed_phonetic,
            target_phonemic=target_phonemic,
        )

        # 5. OOV handling con inventario del pack (si disponible).
        # Si se inyectó un OOVHandlerPort custom se usa directamente;
        # si no, se construye el OOVHandler por defecto con el inventario del pack.
        target_repr, observed_repr = _apply_oov_filter_if_needed(
            pack=pack,
            oov_handler=oov_handler,
            evaluation_level=evaluation_level,
            target_repr=target_repr,
            observed_repr=observed_repr,
        )

        # 6. Comparar con ScoringProfile del pack o defaults
        if pack is not None:
            profile = pack.get_scoring_profile(mode)
            # Extraer error_weights del manifest si está disponible
            error_weights = None
            if hasattr(pack, 'manifest') and hasattr(pack.manifest, 'error_weights'):
                error_weights = pack.manifest.error_weights
            # Pasar el comparador inyectado para respetar el port Comparator
            # incluso cuando hay LanguagePack activo (antes era ignorado).
            return await compare_representations(
                target_repr,
                observed_repr,
                mode=mode,
                evaluation_level=evaluation_level,
                profile=profile,
                error_weights=error_weights,
                comparator=comp,
            )
        
        # Path sin pack: usar comparador inyectado si existe
        if comp is not None:
            res = await comp.compare(target_repr.segments, observed_repr.segments, weights=weights)
            ops = res.get("ops", []) or _ops_from_alignment(res.get("alignment", []))
            # Convertir CompareResult a ComparisonResult
            return ComparisonResult(
                target=target_repr,
                observed=observed_repr,
                mode=mode,
                evaluation_level=evaluation_level,
                distance=res.get("meta", {}).get("distance", 0.0),
                score=max(0.0, (1.0 - res.get("per", 0.0)) * 100.0),
                operations=ops,
            )

        return await compare_representations(
            target_repr,
            observed_repr,
            mode=mode,
            evaluation_level=evaluation_level,
        )
    finally:
        _cleanup_preprocessor_res(pre_audio_res)


async def run_pipeline(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    comp: Comparator,
    *,
    audio: AudioInput,
    text: str,
    lang: Optional[str] = None,
    lang_source: Optional[str] = None,
    lang_target: Optional[str] = None,
    weights: Optional[CompareWeights] = None,
) -> CompareResult:
    """Orquestar preproceso → ASR → TextRef → Comparación (Asíncrono).

    Wrapper compatible que usa el comparador ``comp`` proporcionado.
    Para el pipeline unificado con packs, usar ``execute_pipeline()``.
    """
    result = await execute_pipeline(
        pre,
        asr,
        textref,
        comp,
        audio=audio,
        text=text,
        lang=lang,
        lang_source=lang_source,
        lang_target=lang_target,
        pack=None,
        mode="objective",
        evaluation_level="phonemic",
        weights=weights,
    )
    return cast(CompareResult, result.to_dict())


async def run_pipeline_with_pack(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    *,
    audio: AudioInput,
    text: str,
    pack,
    lang: Optional[str] = None,
    lang_source: Optional[str] = None,
    lang_target: Optional[str] = None,
    mode: EvaluationMode = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
    oov_handler: Optional["OOVHandlerPort"] = None,
) -> ComparisonResult:
    """Wrapper delgado sobre execute_pipeline() con pack.

    Mantiene compatibilidad con código existente.
    """
    if pack is None:
        raise ValidationError("Language pack requerido para run_pipeline_with_pack")

    return await execute_pipeline(
        pre, asr, textref,
        audio=audio,
        text=text,
        lang=lang,
        lang_source=lang_source,
        lang_target=lang_target,
        pack=pack, mode=mode, evaluation_level=evaluation_level,
        oov_handler=oov_handler,
    )


__all__ = [
    "execute_pipeline",
    "run_pipeline",
    "run_pipeline_with_pack",
]


def _cleanup_preprocessor_res(res: PreprocessorResult) -> None:
    """Elimina archivos temporales creados por el preprocesador."""
    import os
    from ipa_core.audio.files import cleanup_temp
    
    meta = res.get("meta", {})
    # 1. Archivo principal si es diferente del original y marcado como temporal
    # Note: Currently BasicPreprocessor doesn't explicitly flag 'is_temp' in res, 
    # but AudioProcessingChain marks steps.
    
    # 2. Archivos en los metadatos de los pasos
    for step_key in ["ensure_wav", "vad_trim", "agc"]:
        step_meta = meta.get(step_key, {})
        if isinstance(step_meta, dict):
            path = step_meta.get("path")
            if path and os.path.exists(path):
                cleanup_temp(path)
