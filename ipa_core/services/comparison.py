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
from ipa_core.normalization.resolve import load_inventory_for
from ipa_core.services.audio_quality import assess_audio_quality
from ipa_core.services.adaptation import adapt_settings
from ipa_core.services.user_profile import UserAudioProfile
from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens, clean_textref_tokens


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

        audio = to_audio_input(wav_path)
        pre_audio_res = await self.pre.process_audio(audio)
        processed_audio = pre_audio_res.get("audio", audio)

        # Si el preprocessor ya ejecutó la cadena de audio, usar quality de ahí
        pre_meta = pre_audio_res.get("meta", {}) if isinstance(pre_audio_res, dict) else {}
        if quality_res is None and "audio_quality" in pre_meta:
            quality_res = pre_meta["audio_quality"]

        asr_result = await self.asr.transcribe(processed_audio, lang=lang or self._default_lang)
        hyp_tokens = asr_result.get("tokens")
        if not hyp_tokens and allow_textref_fallback:
            raw_text = asr_result.get("raw_text", "")
            if raw_text:
                tr_res = await self.textref.to_ipa(raw_text, lang=lang or self._default_lang)
                hyp_tokens = tr_res.get("tokens", [])
        if not hyp_tokens:
            raw_text = asr_result.get("raw_text", "")
            msg = "ASR no devolvió tokens IPA."
            if raw_text:
                msg += f" Texto detectado: '{raw_text}'. Verifique el language pack o la configuración del backend."
            else:
                msg += " El audio podría estar vacío, ser demasiado corto o el modelo aún no está listo."
            raise ValidationError(msg)

        # Limpieza IPA unificada antes de normalización
        hyp_tokens = clean_asr_tokens(hyp_tokens, lang=lang or self._default_lang)
        inventory, pack_id = load_inventory_for(lang=lang or self._default_lang, pack=pack)
        allophone_rules = inventory.allophone_collapse if inventory and effective_level == "phonemic" else None
        if effective_level == "phonetic" and not pack_id:
            warnings.append(
                "Aviso: evaluation_level=phonetic sin language pack; comparación aproximada."
            )
        hyp_pre_res = await self.pre.normalize_tokens(
            hyp_tokens,
            inventory=inventory,
            allophone_rules=allophone_rules,
        )
        hyp_tokens = hyp_pre_res.get("tokens", [])

        ref_lang = lang or self._default_lang
        try:
            tr_result = await self.textref.to_ipa(text, lang=ref_lang)
        except (ValidationError, NotReadyError):
            if fallback_lang and fallback_lang != ref_lang:
                tr_result = await self.textref.to_ipa(text, lang=fallback_lang)
            else:
                raise
        # Limpieza IPA para referencia (sin lang-fixes, TextRef es canónico)
        ref_tokens_raw = clean_textref_tokens(tr_result.get("tokens", []), lang=ref_lang)
        ref_pre_res = await self.pre.normalize_tokens(
            ref_tokens_raw,
            inventory=inventory,
            allophone_rules=allophone_rules,
        )
        ref_tokens = ref_pre_res.get("tokens", [])

        result = await self.comp.compare(ref_tokens, hyp_tokens, weights=weights)
        hyp_meta = hyp_pre_res.get("meta", {})
        oov_tokens = hyp_meta.get("oov_tokens", []) if isinstance(hyp_meta, dict) else []
        if oov_tokens:
            preview = ", ".join(oov_tokens[:6])
            warnings.append(f"Tokens IPA fuera del inventario: {preview}")
        meta: dict = {
            "asr": asr_result.get("meta", {}),
            "compare": result.get("meta", {}),
            "warnings": warnings,
            "normalization": {
                "pack": pack_id,
                "oov_tokens": oov_tokens,
                "oov_count": len(oov_tokens),
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
            result=result,
            meta=meta,
        )
