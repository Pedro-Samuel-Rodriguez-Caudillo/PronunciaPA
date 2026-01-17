"""Servicio de comparación de pronunciación."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ipa_core.audio.files import cleanup_temp, ensure_wav, persist_bytes
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.types import CompareResult, CompareWeights, Token
from ipa_core.plugins import registry


@dataclass
class ComparisonPayload:
    ref_tokens: list[Token]
    hyp_tokens: list[Token]
    result: CompareResult
    meta: dict = field(default_factory=dict)


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
        payload = await self.compare_file_detail(path, text, lang=lang, weights=weights)
        return payload.result

    async def compare_bytes(
        self,
        data: bytes,
        *,
        filename: str = "stream.wav",
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
    ) -> CompareResult:
        payload = await self.compare_bytes_detail(
            data,
            filename=filename,
            text=text,
            lang=lang,
            weights=weights,
        )
        return payload.result

    async def compare_file_detail(
        self,
        path: str,
        text: str,
        *,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
        allow_textref_fallback: bool = False,
        fallback_lang: Optional[str] = None,
    ) -> ComparisonPayload:
        wav_path, tmp = ensure_wav(path)
        try:
            return await self._run_pipeline_detail(
                wav_path,
                text,
                lang=lang,
                weights=weights,
                allow_textref_fallback=allow_textref_fallback,
                fallback_lang=fallback_lang,
            )
        finally:
            if tmp:
                cleanup_temp(wav_path)

    async def compare_bytes_detail(
        self,
        data: bytes,
        *,
        filename: str = "stream.wav",
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
        allow_textref_fallback: bool = False,
        fallback_lang: Optional[str] = None,
    ) -> ComparisonPayload:
        suffix = Path(filename).suffix or ".wav"
        tmp_original = persist_bytes(data, suffix=suffix)
        try:
            return await self.compare_file_detail(
                tmp_original,
                text,
                lang=lang,
                weights=weights,
                allow_textref_fallback=allow_textref_fallback,
                fallback_lang=fallback_lang,
            )
        finally:
            cleanup_temp(tmp_original)

    async def _run_pipeline_detail(
        self,
        wav_path: str,
        text: str,
        *,
        lang: Optional[str],
        weights: Optional[CompareWeights],
        allow_textref_fallback: bool,
        fallback_lang: Optional[str],
    ) -> ComparisonPayload:
        audio = to_audio_input(wav_path)
        pre_audio_res = await self.pre.process_audio(audio)
        processed_audio = pre_audio_res.get("audio", audio)
        asr_result = await self.asr.transcribe(processed_audio, lang=lang or self._default_lang)
        hyp_tokens = asr_result.get("tokens")
        if not hyp_tokens and allow_textref_fallback:
            raw_text = asr_result.get("raw_text", "")
            if raw_text:
                tr_res = await self.textref.to_ipa(raw_text, lang=lang or self._default_lang)
                hyp_tokens = tr_res.get("tokens", [])
        if not hyp_tokens:
            raise ValidationError("ASR no devolvió tokens IPA")
        hyp_pre_res = await self.pre.normalize_tokens(hyp_tokens)
        hyp_tokens = hyp_pre_res.get("tokens", [])

        ref_lang = lang or self._default_lang
        try:
            tr_result = await self.textref.to_ipa(text, lang=ref_lang)
        except (ValidationError, NotReadyError):
            if fallback_lang and fallback_lang != ref_lang:
                tr_result = await self.textref.to_ipa(text, lang=fallback_lang)
            else:
                raise
        ref_pre_res = await self.pre.normalize_tokens(tr_result.get("tokens", []))
        ref_tokens = ref_pre_res.get("tokens", [])

        result = await self.comp.compare(ref_tokens, hyp_tokens, weights=weights)
        meta = {"asr": asr_result.get("meta", {}), "compare": result.get("meta", {})}
        return ComparisonPayload(
            ref_tokens=ref_tokens,
            hyp_tokens=hyp_tokens,
            result=result,
            meta=meta,
        )
