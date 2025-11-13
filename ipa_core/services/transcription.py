"""Servicio de transcripción a IPA."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ipa_core.audio.files import cleanup_temp, ensure_wav, persist_bytes
from ipa_core.backends.asr_allosaurus import AllosaurusASR
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.errors import NotReadyError
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.pipeline.transcribe import transcribe
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.textref.simple import GraphemeTextRef
from ipa_core.types import AudioInput, Token


@dataclass
class TranscriptionPayload:
    """Resultado de transcribir un audio."""

    tokens: list[Token]
    ipa: str
    lang: str
    audio: AudioInput
    meta: dict = field(default_factory=dict)


class TranscriptionService:
    """Coordina preprocesador, backend ASR y TextRef."""

    def __init__(
        self,
        *,
        preprocessor: Optional[Preprocessor] = None,
        asr: Optional[ASRBackend] = None,
        textref: Optional[TextRefProvider] = None,
        default_lang: str = "es",
        backend_name: Optional[str] = None,
        textref_name: Optional[str] = None,
    ) -> None:
        self.pre = preprocessor or BasicPreprocessor()
        self.asr = asr or self._resolve_asr(default_lang, backend_name)
        self.textref = textref or self._resolve_textref(default_lang, textref_name)
        self._default_lang = default_lang

    def _resolve_asr(self, lang: str, backend_name: Optional[str]) -> ASRBackend:
        backend = (backend_name or os.getenv("PRONUNCIAPA_ASR") or "allosaurus").lower()
        if backend == "stub":
            from ipa_core.backends.asr_stub import StubASR

            return StubASR()
        return AllosaurusASR({"lang": lang})

    def _resolve_textref(self, lang: str, textref_name: Optional[str]) -> TextRefProvider:
        selected = (textref_name or os.getenv("PRONUNCIAPA_TEXTREF") or "grapheme").lower()
        if selected == "epitran":
            from ipa_core.textref.epitran import EpitranTextRef

            try:
                return EpitranTextRef(default_lang=lang)
            except NotReadyError:
                selected = "espeak"
        if selected == "espeak":
            from ipa_core.textref.espeak import EspeakTextRef

            return EspeakTextRef(default_lang=lang)
        return GraphemeTextRef()

    def transcribe_file(self, path: str, *, lang: Optional[str] = None) -> TranscriptionPayload:
        wav_path, tmp = ensure_wav(path)
        try:
            return self._run_pipeline(wav_path, lang=lang)
        finally:
            if tmp:
                cleanup_temp(wav_path)

    def transcribe_bytes(self, data: bytes, *, filename: str = "stream.wav", lang: Optional[str] = None) -> TranscriptionPayload:
        suffix = Path(filename).suffix or ".wav"
        tmp_original = persist_bytes(data, suffix=suffix)
        try:
            return self.transcribe_file(tmp_original, lang=lang)
        finally:
            cleanup_temp(tmp_original)

    def _run_pipeline(self, wav_path: str, *, lang: Optional[str]) -> TranscriptionPayload:
        audio = to_audio_input(wav_path)
        tokens = transcribe(self.pre, self.asr, self.textref, audio=audio, lang=lang or self._default_lang)
        backend_name = self.asr.__class__.__name__.lower()
        return TranscriptionPayload(
            tokens=tokens,
            ipa=" ".join(tokens),
            lang=lang or self._default_lang,
            audio=audio,
            meta={"backend": backend_name, "tokens": len(tokens)},
        )
