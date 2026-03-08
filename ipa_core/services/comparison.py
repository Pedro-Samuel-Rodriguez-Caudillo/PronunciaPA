"""Servicio de comparación de pronunciación."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, cast

from ipa_core.audio.files import cleanup_temp, ensure_wav, persist_bytes
from ipa_core.audio.markers import mark_audio_preprocessed
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.normalization.resolve import resolve_pack_id
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.types import CompareResult, CompareWeights, Token
from ipa_core.plugins import registry
from ipa_core.phonology.representation import ComparisonResult, RepresentationLevel
from ipa_core.pipeline.runner import execute_pipeline
from ipa_core.pipeline.transcribe import EvaluationMode
from ipa_core.plugins.language_pack import LanguagePackPlugin
from ipa_core.packs.loader import DEFAULT_PACKS_DIR
from ipa_core.services.audio_quality import assess_audio_quality
from ipa_core.services.adaptation import adapt_settings
from ipa_core.services.user_profile import UserAudioProfile


@dataclass
class ComparisonPayload:
    ref_tokens: list[Token]
    hyp_tokens: list[Token]
    result: CompareResult
    mode: str = "objective"
    evaluation_level: str = "phonemic"
    meta: dict[str, Any] = field(default_factory=dict)

    def to_response(self, *, extra_meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        payload: dict[str, Any] = dict(self.result)
        per = float(payload.get("per", 0.0) or 0.0)
        payload["score"] = max(0.0, (1.0 - per) * 100.0)
        payload["mode"] = self.mode
        payload["evaluation_level"] = self.evaluation_level
        payload["ipa"] = " ".join(self.hyp_tokens)
        payload["tokens"] = list(self.hyp_tokens)
        payload["target_ipa"] = " ".join(self.ref_tokens)
        payload_meta = dict(cast(dict[str, Any], payload.get("meta", {})))
        payload_meta.update(self.meta)
        if extra_meta:
            payload_meta.update(extra_meta)
        payload["meta"] = payload_meta
        return payload


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

    @staticmethod
    def _build_pipeline_audio(path: str) -> dict[str, object]:
        return mark_audio_preprocessed({
            "path": path,
            "sample_rate": 16000,
            "channels": 1,
        })

    @staticmethod
    async def _load_language_pack(pack: Optional[str], lang: str) -> tuple[Optional[LanguagePackPlugin], Optional[str]]:
        if pack:
            pack_path = Path(pack)
            if pack_path.exists() and pack_path.is_dir():
                try:
                    language_pack = LanguagePackPlugin(pack_path)
                    await language_pack.setup()
                    return language_pack, str(pack_path)
                except Exception:
                    return None, str(pack_path)
        pack_id = resolve_pack_id(lang=lang, pack=pack)
        if not pack_id:
            return None, None
        try:
            language_pack = LanguagePackPlugin(DEFAULT_PACKS_DIR / pack_id)
            await language_pack.setup()
            return language_pack, pack_id
        except Exception:
            return None, pack_id

    async def compare_file(
        self,
        path: str,
        text: str,
        *,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
        evaluation_level: str = "phonemic",
        pack: Optional[str] = None,
        mode: str = "objective",
        user_id: Optional[str] = None,
    ) -> CompareResult:
        payload = await self.compare_file_detail(
            path,
            text,
            lang=lang,
            weights=weights,
            evaluation_level=evaluation_level,
            pack=pack,
            mode=mode,
            user_id=user_id,
        )
        return payload.result

    async def compare_bytes(
        self,
        data: bytes,
        *,
        filename: str = "stream.wav",
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
        evaluation_level: str = "phonemic",
        pack: Optional[str] = None,
        mode: str = "objective",
        user_id: Optional[str] = None,
    ) -> CompareResult:
        payload = await self.compare_bytes_detail(
            data,
            filename=filename,
            text=text,
            lang=lang,
            weights=weights,
            evaluation_level=evaluation_level,
            pack=pack,
            mode=mode,
            user_id=user_id,
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
        evaluation_level: str = "phonemic",
        pack: Optional[str] = None,
        mode: str = "objective",
        user_id: Optional[str] = None,
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
                evaluation_level=evaluation_level,
                pack=pack,
                mode=mode,
                user_id=user_id,
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
        evaluation_level: str = "phonemic",
        pack: Optional[str] = None,
        mode: str = "objective",
        user_id: Optional[str] = None,
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
                evaluation_level=evaluation_level,
                pack=pack,
                mode=mode,
                user_id=user_id,
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
        evaluation_level: str,
        pack: Optional[str],
        mode: str,
        user_id: Optional[str],
    ) -> ComparisonPayload:
        effective_lang = lang or self._default_lang
        quality_res, quality_warnings, profile_meta = assess_audio_quality(
            wav_path,
            user_id=user_id,
        )
        warnings: list[str] = list(quality_warnings)
        profile = None
        if profile_meta and isinstance(profile_meta.get("profile"), dict):
            profile = UserAudioProfile.from_dict(profile_meta["profile"])

        effective_mode, effective_level, adaptive_meta = adapt_settings(
            requested_mode=mode,
            requested_level=evaluation_level,
            quality=quality_res,
            profile=profile,
        )
        if allow_textref_fallback:
            raise ValidationError(
                "allow_textref_fallback ya no está soportado en modo estricto"
            )

        pipeline_lang = effective_lang
        if fallback_lang and fallback_lang != effective_lang:
            try:
                await self.textref.to_ipa(text, lang=effective_lang)
            except (ValidationError, NotReadyError):
                pipeline_lang = fallback_lang

        language_pack = None
        pack_id = None
        try:
            language_pack, pack_id = await self._load_language_pack(pack, pipeline_lang)
            if effective_level == "phonetic" and language_pack is None:
                warnings.append(
                    "Aviso: evaluation_level=phonetic sin language pack; comparación aproximada."
                )
            audio = self._build_pipeline_audio(wav_path)
            comp_res = await execute_pipeline(
                self.pre,
                self.asr,
                self.textref,
                self.comp,
                audio=audio,  # type: ignore[arg-type]
                text=text,
                lang=pipeline_lang,
                pack=language_pack,
                mode=effective_mode,  # type: ignore[arg-type]
                evaluation_level=effective_level,  # type: ignore[arg-type]
                weights=weights,
            )
        finally:
            if language_pack is not None:
                await language_pack.teardown()

        result = comp_res.to_dict()
        ref_tokens = list(comp_res.target.segments)
        hyp_tokens = list(comp_res.observed.segments)
        meta: dict[str, Any] = {
            "compare": result.get("meta", {}),
            "warnings": warnings,
            "normalization": {
                "pack": pack_id,
                "oov_tokens": [],
                "oov_count": 0,
            },
            "adaptive": adaptive_meta,
        }
        if quality_res:
            meta["audio_quality"] = quality_res.to_dict()
        if profile_meta:
            meta["user_profile"] = profile_meta
        return ComparisonPayload(
            ref_tokens=ref_tokens,
            hyp_tokens=hyp_tokens,
            result=cast(CompareResult, result),
            mode=effective_mode,
            evaluation_level=effective_level,
            meta=meta,
        )
