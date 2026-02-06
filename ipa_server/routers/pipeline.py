"""Core pipeline endpoints: transcribe, textref, compare, feedback."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from ipa_core.config import loader
from ipa_core.config.overrides import apply_overrides
from ipa_core.errors import ValidationError
from ipa_core.kernel.core import Kernel, create_kernel
from ipa_core.normalization.resolve import resolve_pack_id
from ipa_core.pipeline.runner import run_pipeline_with_pack
from ipa_core.pipeline.transcribe import EvaluationMode
from ipa_core.phonology.representation import RepresentationLevel
from ipa_core.plugins import registry
from ipa_core.plugins.language_pack import LanguagePackPlugin
from ipa_core.services.adaptation import adapt_settings
from ipa_core.services.audio_quality import assess_audio_quality
from ipa_core.services.comparison import ComparisonService
from ipa_core.services.feedback import FeedbackService
from ipa_core.services.feedback_store import FeedbackStore
from ipa_core.services.transcription import TranscriptionService
from ipa_core.types import AudioInput
from ipa_server.models import (
    CompareResponse,
    FeedbackResponse,
    TextRefResponse,
    TranscriptionResponse,
)

logger = logging.getLogger("ipa_server")

router = APIRouter(prefix="/v1", tags=["pipeline"])


def _get_kernel() -> Kernel:
    """Carga la configuración y crea el kernel (Inyectable)."""
    cfg = loader.load_config()
    return create_kernel(cfg)


def _build_kernel(
    *,
    model_pack: Optional[str] = None,
    llm_name: Optional[str] = None,
) -> Kernel:
    cfg = loader.load_config()
    cfg = apply_overrides(cfg, model_pack=model_pack, llm_name=llm_name)
    return create_kernel(cfg)


async def _process_upload(audio: UploadFile) -> Path:
    """Guarda un UploadFile en un archivo temporal y retorna su ruta."""
    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        return Path(tmp.name)


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    audio: UploadFile = File(..., description="Archivo de audio a transcribir"),
    lang: str = Form("es", description="Idioma del audio"),
    backend: Optional[str] = Form(None, description="Nombre del backend ASR"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    persist: Optional[bool] = Form(False, description="Si True, guarda el audio procesado"),
    user_id: Optional[str] = Form(None, description="ID de usuario (opcional)"),
    kernel: Kernel = Depends(_get_kernel),
) -> dict[str, Any]:
    """Transcripción de audio a IPA usando el microkernel."""
    tmp_path = await _process_upload(audio)
    try:
        if backend:
            kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
        if textref:
            kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
        await kernel.setup()
        service = TranscriptionService(
            preprocessor=kernel.pre,
            asr=kernel.asr,
            textref=kernel.textref,
            default_lang=lang,
        )
        payload = await service.transcribe_file(str(tmp_path), lang=lang, user_id=user_id)
        return {
            "ipa": payload.ipa,
            "tokens": payload.tokens,
            "lang": lang,
            "meta": payload.meta,
        }
    finally:
        await kernel.teardown()
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/textref", response_model=TextRefResponse)
async def textref_endpoint(
    text: str = Form(..., description="Texto a convertir a IPA"),
    lang: str = Form("es", description="Idioma del texto"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    kernel: Kernel = Depends(_get_kernel),
) -> dict[str, Any]:
    """Convierte texto a IPA usando el proveedor TextRef."""
    try:
        if textref:
            kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
        await kernel.setup()
        tr_res = await kernel.textref.to_ipa(text, lang=lang)
        tokens = tr_res.get("tokens", [])
        meta = tr_res.get("meta", {})
        return {
            "ipa": " ".join(tokens),
            "tokens": tokens,
            "lang": lang,
            "meta": meta,
        }
    finally:
        await kernel.teardown()


@router.post("/compare", response_model=CompareResponse)
async def compare(
    audio: UploadFile = File(..., description="Archivo de audio a comparar"),
    text: str = Form(..., description="Texto de referencia"),
    lang: str = Form("es", description="Idioma del audio"),
    mode: str = Form("objective", description="Modo: casual, objective, phonetic, auto"),
    evaluation_level: str = Form("phonemic", description="Nivel: phonemic, phonetic, auto"),
    backend: Optional[str] = Form(None, description="Nombre del backend ASR"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    comparator: Optional[str] = Form(None, description="Nombre del comparador"),
    pack: Optional[str] = Form(None, description="Language pack (dialecto) a usar"),
    persist: Optional[bool] = Form(False, description="Si True, guarda el audio procesado"),
    user_id: Optional[str] = Form(None, description="ID de usuario (opcional)"),
    kernel: Kernel = Depends(_get_kernel),
) -> dict[str, Any]:
    """Comparación de audio contra texto de referencia."""
    logger.info("=== /v1/compare REQUEST ===")
    logger.info(f"text: {text}, lang: {lang}, mode: {mode}, evaluation_level: {evaluation_level}")

    tmp_path = await _process_upload(audio)
    try:
        if backend:
            kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
        if textref:
            kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
        if comparator:
            kernel.comp = registry.resolve_comparator(comparator.lower(), {})

        # Cargar language pack (auto si es posible)
        language_pack = None
        pack_id = None
        if pack:
            pack_path = Path(pack)
            if pack_path.exists() and pack_path.is_dir():
                pack_id = pack_path
            else:
                pack_id = pack.lower()
        if not pack_id:
            pack_id = resolve_pack_id(lang=lang)
        if pack_id:
            from ipa_core.packs.loader import DEFAULT_PACKS_DIR

            try:
                pack_dir = (
                    pack_id
                    if isinstance(pack_id, Path)
                    else (DEFAULT_PACKS_DIR / str(pack_id))
                )
                language_pack = LanguagePackPlugin(Path(pack_dir))
                await language_pack.setup()
            except Exception as e:
                logger.warning(f"No se pudo cargar language pack '{pack_id}': {e}")

        await kernel.setup()

        if language_pack:
            quality_res, quality_warnings, profile_meta = assess_audio_quality(
                str(tmp_path), user_id=user_id
            )
            profile = None
            if profile_meta and isinstance(profile_meta.get("profile"), dict):
                from ipa_core.services.user_profile import UserAudioProfile

                profile = UserAudioProfile.from_dict(profile_meta["profile"])
            effective_mode, effective_level, adaptive_meta = adapt_settings(
                requested_mode=mode,
                requested_level=evaluation_level,
                quality=quality_res,
                profile=profile,
            )
            comp_res = await run_pipeline_with_pack(
                pre=kernel.pre,
                asr=kernel.asr,
                textref=kernel.textref,
                audio={"path": str(tmp_path), "sample_rate": 16000, "channels": 1},
                text=text,
                pack=language_pack,
                lang=lang,
                mode=cast(EvaluationMode, effective_mode),
                evaluation_level=cast(RepresentationLevel, effective_level),
            )
            payload = comp_res.to_dict()
            payload["score"] = comp_res.score
            payload["mode"] = effective_mode
            payload["evaluation_level"] = effective_level
            payload["ipa"] = comp_res.observed.to_ipa(with_delimiters=False)
            payload["tokens"] = comp_res.observed.segments
            payload.setdefault("meta", {})
            payload["meta"]["adaptive"] = adaptive_meta
            if quality_res:
                payload["meta"]["audio_quality"] = quality_res.to_dict()
            if quality_warnings:
                payload["meta"]["warnings"] = quality_warnings
            if profile_meta:
                payload["meta"]["user_profile"] = profile_meta
            return payload

        # Fallback al comparador clásico (sin language pack)
        service = ComparisonService(
            preprocessor=kernel.pre,
            asr=kernel.asr,
            textref=kernel.textref,
            comparator=kernel.comp,
            default_lang=lang,
        )
        payload = await service.compare_file_detail(
            str(tmp_path),
            text,
            lang=lang,
            evaluation_level=evaluation_level,
            pack=pack,
            mode=mode,
            user_id=user_id,
        )
        res = payload.result
        hyp_tokens = payload.hyp_tokens
        ref_tokens = payload.ref_tokens
        meta = payload.meta

        per = res.get("per", 0.0)
        base_score = max(0.0, (1.0 - per) * 100.0)
        alignment = [list(pair) for pair in res.get("alignment", [])]

        adaptive = meta.get("adaptive", {}) if isinstance(meta, dict) else {}
        effective_mode = adaptive.get("effective", {}).get("mode", mode)
        effective_level = adaptive.get("effective", {}).get(
            "evaluation_level", evaluation_level
        )
        return {
            **res,
            "alignment": alignment,
            "score": base_score,
            "mode": effective_mode,
            "evaluation_level": effective_level,
            "ipa": " ".join(hyp_tokens),
            "tokens": hyp_tokens,
            "target_ipa": " ".join(ref_tokens),
            "meta": meta,
        }
    finally:
        await kernel.teardown()
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    audio: UploadFile = File(..., description="Archivo de audio a analizar"),
    text: str = Form(..., description="Texto de referencia"),
    lang: str = Form("es", description="Idioma del audio"),
    mode: str = Form("objective", description="Modo: casual, objective, phonetic, auto"),
    evaluation_level: str = Form(
        "phonemic", description="Nivel: phonemic, phonetic, auto"
    ),
    feedback_level: Optional[str] = Form(
        None, description="Nivel de feedback: casual (amigable) o precise (tecnico)"
    ),
    model_pack: Optional[str] = Form(None, description="Model pack a usar (opcional)"),
    llm: Optional[str] = Form(None, description="Adapter LLM a usar (opcional)"),
    prompt_path: Optional[str] = Form(
        None, description="Ruta a prompt override (opcional)"
    ),
    output_schema_path: Optional[str] = Form(
        None, description="Ruta a schema override (opcional)"
    ),
    persist: bool = Form(False, description="Guardar resultado localmente"),
    user_id: Optional[str] = Form(None, description="ID de usuario (opcional)"),
) -> dict[str, Any]:
    """Analiza la pronunciacion y genera feedback con LLM local."""
    tmp_path = await _process_upload(audio)
    kernel = _build_kernel(model_pack=model_pack, llm_name=llm)
    try:
        await kernel.setup()
        audio_in: AudioInput = {
            "path": str(tmp_path),
            "sample_rate": 16000,
            "channels": 1,
        }
        service = FeedbackService(kernel)
        prompt_file = Path(prompt_path) if prompt_path else None
        schema_file = Path(output_schema_path) if output_schema_path else None
        if prompt_file and not prompt_file.exists():
            raise ValidationError(f"Prompt file not found: {prompt_file}")
        if schema_file and not schema_file.exists():
            raise ValidationError(f"Output schema not found: {schema_file}")
        result = await service.analyze(
            audio=audio_in,
            text=text,
            lang=lang,
            mode=mode,
            evaluation_level=evaluation_level,
            feedback_level=feedback_level,
            prompt_path=prompt_file,
            output_schema_path=schema_file,
            user_id=user_id,
        )
        if persist:
            store = FeedbackStore()
            store.append(result, audio=dict(audio_in), meta={"text": text, "lang": lang})
        return result
    finally:
        await kernel.teardown()
        if tmp_path.exists():
            tmp_path.unlink()
