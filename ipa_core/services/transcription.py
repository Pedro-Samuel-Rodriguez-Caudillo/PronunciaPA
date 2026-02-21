"""Servicio de transcripción a IPA."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ipa_core.audio.files import cleanup_temp, ensure_wav, persist_bytes
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.types import AudioInput, Token
from ipa_core.plugins import registry
from ipa_core.normalization.resolve import load_inventory_for
from ipa_core.services.audio_quality import assess_audio_quality
from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens


@dataclass
class TranscriptionPayload:
    """Resultado de transcribir un audio."""

    tokens: list[Token]
    ipa: str
    lang: str
    audio: AudioInput
    meta: dict = field(default_factory=dict)


class TranscriptionService:
    """Coordina preprocesador, backend ASR y TextRef (Asíncrono)."""

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
        # Casts para satisfacer a mypy ya que las implementaciones concretas
        # ahora satisfacen los protocolos asíncronos.
        self.pre = preprocessor or BasicPreprocessor()
        self.asr = asr or self._resolve_asr(default_lang, backend_name)
        self.textref = textref or self._resolve_textref(default_lang, textref_name)
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
                try:
                    return registry.resolve_textref("espeak", {"default_lang": lang})
                except (NotReadyError, KeyError):
                    pass
            raise

    async def transcribe_file(
        self,
        path: str,
        *,
        lang: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> TranscriptionPayload:
        """Transcribir archivo de audio de forma asíncrona."""
        wav_path, tmp = ensure_wav(path)
        try:
            return await self._run_pipeline(wav_path, lang=lang, user_id=user_id)
        finally:
            if tmp:
                cleanup_temp(wav_path)

    async def transcribe_bytes(
        self,
        data: bytes,
        *,
        filename: str = "stream.wav",
        lang: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> TranscriptionPayload:
        """Transcribir bytes de audio de forma asíncrona."""
        suffix = Path(filename).suffix or ".wav"
        tmp_original = persist_bytes(data, suffix=suffix)
        try:
            return await self.transcribe_file(tmp_original, lang=lang, user_id=user_id)
        finally:
            cleanup_temp(tmp_original)

    async def _run_pipeline(
        self,
        wav_path: str,
        *,
        lang: Optional[str],
        user_id: Optional[str],
    ) -> TranscriptionPayload:
        quality_res, quality_warnings, profile_meta = assess_audio_quality(
            wav_path,
            user_id=user_id,
        )
        audio = to_audio_input(wav_path)
        pre_audio_res = await self.pre.process_audio(audio)
        processed_audio = pre_audio_res.get("audio", audio)
        asr_result = await self.asr.transcribe(processed_audio, lang=lang or self._default_lang)
        tokens = asr_result.get("tokens")
        if not tokens:
            raw_text = asr_result.get("raw_text", "")
            if raw_text:
                tr_res = await self.textref.to_ipa(raw_text, lang=lang or self._default_lang)
                tokens = tr_res.get("tokens", [])
        if not tokens:
            raise ValidationError("ASR no devolvió tokens IPA")
        # Limpieza IPA unificada
        raw_confidences = asr_result.get("confidences")
        tokens = clean_asr_tokens(tokens, lang=lang or self._default_lang)
        inventory, pack_id = load_inventory_for(lang=lang or self._default_lang)
        norm_res = await self.pre.normalize_tokens(tokens, inventory=inventory)
        tokens = norm_res.get("tokens", [])
        backend_name = self.asr.__class__.__name__.lower()
        meta = dict(asr_result.get("meta", {}))
        meta.setdefault("backend", backend_name)
        # Propagar confidence scores alineados con tokens limpios
        if raw_confidences is not None:
            n = len(tokens)
            meta["confidences"] = raw_confidences[:n] if len(raw_confidences) >= n else raw_confidences
        meta.setdefault("tokens", len(tokens))
        if quality_warnings:
            meta.setdefault("warnings", [])
            meta["warnings"].extend(quality_warnings)
        if quality_res:
            meta["audio_quality"] = quality_res.to_dict()
        if profile_meta:
            meta["user_profile"] = profile_meta
        if inventory:
            meta["normalization"] = {
                "pack": pack_id,
                "oov_tokens": norm_res.get("meta", {}).get("oov_tokens", []),
            }
        return TranscriptionPayload(
            tokens=tokens,
            ipa=" ".join(tokens),
            lang=lang or self._default_lang,
            audio=audio,
            meta=meta,
        )
