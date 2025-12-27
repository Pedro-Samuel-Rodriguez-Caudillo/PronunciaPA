"""Pipeline mínimo de transcripción a IPA (independiente del comparador).

Flujo:
- pre.process_audio(audio) → asr.transcribe
- Si ASRResult.tokens: pre.normalize_tokens(tokens) → salida
- Si solo ASRResult.raw_text: textref.to_ipa(raw_text, lang) → normalize
"""
from __future__ import annotations

from typing import Optional

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import AudioInput, Token


async def transcribe(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    *,
    audio: AudioInput,
    lang: Optional[str] = None,
) -> list[Token]:
    """Transcribir audio a tokens IPA normalizados (Asíncrono)."""
    # 1. Preproceso de audio
    pre_audio_res = await pre.process_audio(audio)
    processed_audio = pre_audio_res.get("audio", audio)

    # 2. ASR
    res = await asr.transcribe(processed_audio, lang=lang)

    # 3. Extracción y normalización de tokens
    tokens = res.get("tokens")
    if tokens:
        norm_res = await pre.normalize_tokens(tokens)
        return norm_res.get("tokens", [])

    raw = res.get("raw_text", "")
    if raw:
        tr_res = await textref.to_ipa(raw, lang=lang or "")
        norm_res = await pre.normalize_tokens(tr_res.get("tokens", []))
        return norm_res.get("tokens", [])

    return []