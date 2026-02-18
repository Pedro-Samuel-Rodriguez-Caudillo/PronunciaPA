"""Pipeline de transcripción con modos y nivel de evaluación.

Flujo soporta:
- mode: casual, objective, phonetic (tolerancia/scoring)
- evaluation_level: phonemic, phonetic (nivel de comparación)
"""
from __future__ import annotations

from typing import Literal, Optional, TYPE_CHECKING

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.errors import ValidationError
from ipa_core.types import AudioInput, Token
from ipa_core.phonology.representation import (
    PhonologicalRepresentation,
    TranscriptionResult,
    ComparisonResult,
    RepresentationLevel,
)
from ipa_core.compare.compare import compare_representations
from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens, clean_textref_tokens

if TYPE_CHECKING:
    from ipa_core.plugins.language_pack import LanguagePackPlugin


# Tipos para parámetros
EvaluationMode = Literal["casual", "objective", "phonetic"]


async def transcribe_audio(
    pre: Preprocessor,
    asr: ASRBackend,
    *,
    audio: AudioInput,
    lang: Optional[str] = None,
) -> PhonologicalRepresentation:
    """Transcribir audio a IPA fonético.
    
    Retorna representación fonética (lo que ASR escucha).
    """
    # 1. Preproceso de audio
    pre_audio_res = await pre.process_audio(audio)
    processed_audio = pre_audio_res.get("audio", audio)

    # 2. ASR
    res = await asr.transcribe(processed_audio, lang=lang)

    # 3. Extraer y limpiar tokens
    tokens = res.get("tokens", [])
    if not tokens:
        raise ValidationError("ASR no devolvió tokens IPA")

    # Limpieza IPA: silence filter + lang fixes + dedup
    tokens = clean_asr_tokens(tokens, lang=lang)
    if not tokens:
        raise ValidationError("ASR no devolvió tokens IPA válidos tras limpieza")

    # Normalización del preprocessor
    norm_res = await pre.normalize_tokens(tokens)
    tokens = norm_res.get("tokens", tokens)

    # ASR produce representación fonética
    ipa = "".join(tokens)
    return PhonologicalRepresentation.phonetic(ipa)


async def transcribe_text(
    textref: TextRefProvider,
    *,
    text: str,
    lang: str,
) -> PhonologicalRepresentation:
    """Transcribir texto a IPA fonémico.
    
    Retorna representación fonémica (subyacente).
    """
    res = await textref.to_ipa(text, lang=lang)
    tokens = res.get("tokens", [])
    if not tokens:
        raise ValidationError("TextRef no devolvió tokens IPA")

    # Limpieza IPA: silence filter + artefactos no-IPA (sin lang-fixes, TextRef es canónico)
    tokens = clean_textref_tokens(tokens, lang=lang)
    if not tokens:
        raise ValidationError("TextRef no devolvió tokens IPA válidos tras limpieza")

    ipa = "".join(tokens)
    return PhonologicalRepresentation.phonemic(ipa)


async def prepare_comparison(
    target_text: str,
    observed_audio: AudioInput,
    *,
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    pack: Optional["LanguagePackPlugin"] = None,
    lang: str,
    mode: EvaluationMode = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
) -> tuple[PhonologicalRepresentation, PhonologicalRepresentation]:
    """Preparar representaciones para comparación.

    .. deprecated::
        Usar :func:`ipa_core.pipeline.runner.execute_pipeline` en su lugar.
    
    Parámetros
    ----------
    target_text : str
        Texto objetivo (lo que debería decir).
    observed_audio : AudioInput
        Audio del usuario.
    pack : LanguagePackPlugin
        Pack de idioma para derive/collapse.
    mode : str
        Modo de evaluación.
    evaluation_level : str
        Nivel de comparación: "phonemic" o "phonetic".
        
    Retorna
    -------
    tuple
        (target_repr, observed_repr) al mismo nivel.
    """
    # 1. Obtener representaciones base
    target_phonemic = await transcribe_text(textref, text=target_text, lang=lang)
    observed_phonetic = await transcribe_audio(pre, asr, audio=observed_audio, lang=lang)
    
    # 2. Convertir al nivel de evaluación solicitado
    if evaluation_level == "phonemic":
        # Colapsar observed a fonémico
        if pack is not None:
            collapsed_ipa = pack.collapse(observed_phonetic.ipa, mode=mode)
            observed_repr = PhonologicalRepresentation.phonemic(collapsed_ipa)
        else:
            # Sin pack, usar como está (aproximación)
            observed_repr = PhonologicalRepresentation.phonemic(observed_phonetic.ipa)
        
        target_repr = target_phonemic
        
    else:  # phonetic
        # Derivar target a fonético
        if pack is not None:
            derived_ipa = pack.derive(target_phonemic.ipa, mode=mode)
            target_repr = PhonologicalRepresentation.phonetic(derived_ipa)
        else:
            # Sin pack, usar como está
            target_repr = PhonologicalRepresentation.phonetic(target_phonemic.ipa)
        
        observed_repr = observed_phonetic
    
    return target_repr, observed_repr


async def compare_with_pack(
    target_text: str,
    observed_audio: AudioInput,
    *,
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    pack: Optional["LanguagePackPlugin"],
    lang: str,
    mode: EvaluationMode = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
) -> ComparisonResult:
    """Preparar y comparar usando LanguagePack (derive/collapse + scoring profile).

    .. deprecated::
        Usar :func:`ipa_core.pipeline.runner.execute_pipeline` en su lugar.
    """

    target_repr, observed_repr = await prepare_comparison(
        target_text,
        observed_audio,
        pre=pre,
        asr=asr,
        textref=textref,
        pack=pack,
        lang=lang,
        mode=mode,
        evaluation_level=evaluation_level,
    )

    profile = pack.get_scoring_profile(mode) if pack is not None else None

    return await compare_representations(
        target_repr,
        observed_repr,
        mode=mode,
        evaluation_level=evaluation_level,
        profile=profile,
    )


# Mantener compatibilidad con transcribe() original
async def transcribe(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    *,
    audio: AudioInput,
    lang: Optional[str] = None,
) -> list[Token]:
    """Transcribir audio a tokens IPA normalizados (legado).
    
    Mantiene compatibilidad con código existente.
    """
    # 1. Preproceso de audio
    pre_audio_res = await pre.process_audio(audio)
    processed_audio = pre_audio_res.get("audio", audio)

    # 2. ASR
    res = await asr.transcribe(processed_audio, lang=lang)

    # 3. Extracción y normalización de tokens (o fallback a TextRef)
    tokens = res.get("tokens")
    if not tokens:
        raw_text = res.get("raw_text", "")
        if raw_text:
            tr_res = await textref.to_ipa(raw_text, lang=lang or "")
            tokens = tr_res.get("tokens", [])
    if tokens:
        norm_res = await pre.normalize_tokens(tokens)
        return norm_res.get("tokens", [])

    raise ValidationError("ASR no devolvió tokens IPA")


__all__ = [
    "transcribe",
    "transcribe_audio",
    "transcribe_text",
    "prepare_comparison",
    "compare_with_pack",
    "EvaluationMode",
]
