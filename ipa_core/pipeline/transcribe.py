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


def transcribe(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    *,
    audio: AudioInput,
    lang: Optional[str] = None,
) -> list[Token]:
    a1 = pre.process_audio(audio)
    res = asr.transcribe(a1, lang=lang)
    tokens = res.get("tokens")
    if tokens:
        return pre.normalize_tokens(tokens)
    raw = res.get("raw_text", "")
    if raw:
        return pre.normalize_tokens(textref.to_ipa(raw, lang=lang or ""))
    return []

