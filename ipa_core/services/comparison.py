"""Servicio de comparación de pronunciación."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ipa_core.audio.files import cleanup_temp, ensure_wav, persist_bytes
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.errors import NotReadyError
from ipa_core.pipeline.runner import run_pipeline
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.textref.simple import GraphemeTextRef
from ipa_core.types import CompareResult, CompareWeights
from ipa_core.plugins import registry


class ComparisonService:
    """Coordina el pipeline de comparación (asíncrono)."""

    def __init__(
        self,
        *,
        preprocessor: Optional[Preprocessor] = None,
        asr: Optional[ASRBackend] = None,
        textref: Optional[TextRefProvider] = None,
        comparator: Optional[Comparator] = None,
        default_lang: str = "es",
        backend_name: Optional[str] = None,
        textref_name: Optional[str] = None,
        comparator_name: Optional[str] = None,
    ) -> None:
        self.pre = preprocessor or BasicPreprocessor()
        self.asr = asr or self._resolve_asr(default_lang, backend_name)
        self.textref = textref or self._resolve_textref(default_lang, textref_name)
        self.comp = comparator or self._resolve_comparator(comparator_name)
        self._default_lang = default_lang

    def _resolve_asr(self, lang: str, backend_name: Optional[str]) -> ASRBackend:
        backend = (backend_name or os.getenv("PRONUNCIAPA_ASR") or "default").lower()
        return registry.resolve_asr(backend, {"lang": lang})

    def _resolve_textref(self, lang: str, textref_name: Optional[str]) -> TextRefProvider:
        selected = (textref_name or os.getenv("PRONUNCIAPA_TEXTREF") or "grapheme").lower()
        try:
            return registry.resolve_textref(selected, {"default_lang": lang})
        except (NotReadyError, KeyError):
            if selected == "epitran":
                return registry.resolve_textref("espeak", {"default_lang": lang})
            raise

    def _resolve_comparator(self, comparator_name: Optional[str]) -> Comparator:
        selected = (comparator_name or os.getenv("PRONUNCIAPA_COMPARATOR") or "default").lower()
        return registry.resolve_comparator(selected, {})

    async def compare_file(
        self,
        path: str,
        text: str,
        *,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
    ) -> CompareResult:
        wav_path, tmp = ensure_wav(path)
        try:
            return await self._run_pipeline(wav_path, text, lang=lang, weights=weights)
        finally:
            if tmp:
                cleanup_temp(wav_path)

    async def compare_bytes(
        self,
        data: bytes,
        *,
        filename: str = "stream.wav",
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
    ) -> CompareResult:
        suffix = Path(filename).suffix or ".wav"
        tmp_original = persist_bytes(data, suffix=suffix)
        try:
            return await self.compare_file(tmp_original, text, lang=lang, weights=weights)
        finally:
            cleanup_temp(tmp_original)

    async def _run_pipeline(
        self,
        wav_path: str,
        text: str,
        *,
        lang: Optional[str],
        weights: Optional[CompareWeights],
    ) -> CompareResult:
        audio = to_audio_input(wav_path)
        return await run_pipeline(
            self.pre,
            self.asr,
            self.textref,
            self.comp,
            audio=audio,
            text=text,
            lang=lang or self._default_lang,
            weights=weights,
        )
