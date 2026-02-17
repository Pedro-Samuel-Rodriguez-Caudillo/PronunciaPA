"""Core pipeline endpoints: transcribe, textref, compare, feedback."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional, Union, cast

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from ipa_core.audio.files import cleanup_temp, ensure_wav
from ipa_core.backends.audio_io import to_audio_input
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


# ── Kernel singleton cache ────────────────────────────────────────────
_cached_kernel: Optional[Kernel] = None
_kernel_ready: bool = False


async def _get_or_create_kernel() -> Kernel:
    """Return a warm, already-setup kernel (singleton).

    The first call creates + sets up the kernel.  Subsequent calls reuse it.
    This removes the ~200-400 ms overhead of recreating the kernel per request.
    """
    global _cached_kernel, _kernel_ready
    if _cached_kernel is not None and _kernel_ready:
        return _cached_kernel
    cfg = loader.load_config()
    _cached_kernel = create_kernel(cfg)
    await _cached_kernel.setup()
    _kernel_ready = True
    logger.info("Kernel singleton created and ready")
    return _cached_kernel


def _get_kernel() -> Kernel:
    """Carga la configuración y crea el kernel (Inyectable — legacy).

    NOTE: Endpoints that depend on this still run setup()/teardown() per
    request.  Prefer _get_or_create_kernel() for fast-path endpoints.
    """
    cfg = loader.load_config()
    return create_kernel(cfg)


def _default_lang_from_config() -> str:
    """Obtiene idioma por defecto desde config con fallback seguro."""
    try:
        cfg = loader.load_config()
        opt_lang = getattr(cfg.options, "lang", None)
        if isinstance(opt_lang, str) and opt_lang.strip():
            return opt_lang.strip().lower()
        backend_lang = cfg.backend.params.get("lang")
        if isinstance(backend_lang, str) and backend_lang.strip():
            return backend_lang.strip().lower()
    except Exception as exc:  # pragma: no cover - fallback defensivo
        logger.debug("No se pudo resolver idioma por defecto desde config: %s", exc)
    return "es"


def _resolve_request_lang(lang: Optional[str]) -> str:
    """Normaliza lang de request; si falta, usa config."""
    if isinstance(lang, str) and lang.strip():
        return lang.strip().lower()
    return _default_lang_from_config()


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


def _asr_unavailable_response(*, backend_name: str, reason: str) -> JSONResponse:
    detail = (
        "No hay un modelo ASR IPA real activo para este endpoint. "
        f"Backend detectado: '{backend_name}'. Motivo: {reason}. "
        "Para corregirlo: (1) elimina PRONUNCIAPA_ASR=stub en el entorno, "
        "(2) configura un backend IPA real en configs/local.yaml "
        "(ej. unified_ipa/allosaurus), (3) verifica disponibilidad en /api/asr/engines."
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": detail,
            "type": "asr_unavailable",
            "backend": backend_name,
        },
    )


def _assert_real_ipa_asr(asr_backend: Any) -> Optional[JSONResponse]:
    """Bloquea backends stub o no-IPA en endpoints de usuario."""
    backend_name = asr_backend.__class__.__name__
    module_name = asr_backend.__class__.__module__
    output_type = getattr(asr_backend, "output_type", None)

    logger.info(
        "Effective ASR backend: %s (%s), output_type=%s",
        backend_name,
        module_name,
        output_type,
    )

    normalized_name = backend_name.lower()
    if normalized_name == "stubasr" or normalized_name.startswith("stub"):
        return _asr_unavailable_response(
            backend_name=backend_name,
            reason="backend de desarrollo (stub) activo",
        )

    if isinstance(output_type, str) and output_type.lower() != "ipa":
        return _asr_unavailable_response(
            backend_name=backend_name,
            reason=f"output_type='{output_type}' (se requiere 'ipa')",
        )

    return None


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    audio: UploadFile = File(..., description="Archivo de audio a transcribir"),
    lang: Optional[str] = Form(None, description="Idioma del audio"),
    backend: Optional[str] = Form(None, description="Nombre del backend ASR"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    persist: Optional[bool] = Form(False, description="Si True, guarda el audio procesado"),
    user_id: Optional[str] = Form(None, description="ID de usuario (opcional)"),
    kernel: Kernel = Depends(_get_kernel),
) -> Union[dict[str, Any], JSONResponse]:
    """Transcripción de audio a IPA usando el microkernel."""
    lang_resolved = _resolve_request_lang(lang)
    tmp_path = await _process_upload(audio)
    try:
        if backend:
            kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang_resolved})
        if textref:
            kernel.textref = registry.resolve_textref(
                textref.lower(), {"default_lang": lang_resolved}
            )
        await kernel.setup()
        asr_guard = _assert_real_ipa_asr(kernel.asr)
        if asr_guard:
            return asr_guard

        # Run quality gates before ASR
        quality_res, quality_warnings, _ = assess_audio_quality(
            str(tmp_path), user_id=user_id
        )

        service = TranscriptionService(
            preprocessor=kernel.pre,
            asr=kernel.asr,
            textref=kernel.textref,
            default_lang=lang_resolved,
        )
        payload = await service.transcribe_file(
            str(tmp_path), lang=lang_resolved, user_id=user_id
        )
        meta = payload.meta or {}
        if quality_res:
            meta["audio_quality"] = quality_res.to_dict()
        if quality_warnings:
            meta["warnings"] = quality_warnings
        return {
            "ipa": payload.ipa,
            "tokens": payload.tokens,
            "lang": lang_resolved,
            "meta": meta,
        }
    finally:
        await kernel.teardown()
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/textref", response_model=TextRefResponse)
async def textref_endpoint(
    text: str = Form(..., description="Texto a convertir a IPA"),
    lang: Optional[str] = Form(None, description="Idioma del texto"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    kernel: Kernel = Depends(_get_kernel),
) -> Union[dict[str, Any], JSONResponse]:
    """Convierte texto a IPA usando el proveedor TextRef."""
    lang_resolved = _resolve_request_lang(lang)
    try:
        if textref:
            kernel.textref = registry.resolve_textref(
                textref.lower(), {"default_lang": lang_resolved}
            )
        await kernel.setup()
        tr_res = await kernel.textref.to_ipa(text, lang=lang_resolved)
        tokens = tr_res.get("tokens", [])
        meta = tr_res.get("meta", {})
        return {
            "ipa": " ".join(tokens),
            "tokens": tokens,
            "lang": lang_resolved,
            "meta": meta,
        }
    finally:
        await kernel.teardown()


@router.post("/compare", response_model=CompareResponse)
async def compare(
    audio: UploadFile = File(..., description="Archivo de audio a comparar"),
    text: str = Form(..., description="Texto de referencia"),
    lang: Optional[str] = Form(None, description="Idioma del audio"),
    mode: str = Form("objective", description="Modo: casual, objective, phonetic, auto"),
    evaluation_level: str = Form("phonemic", description="Nivel: phonemic, phonetic, auto"),
    backend: Optional[str] = Form(None, description="Nombre del backend ASR"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    comparator: Optional[str] = Form(None, description="Nombre del comparador"),
    pack: Optional[str] = Form(None, description="Language pack (dialecto) a usar"),
    persist: Optional[bool] = Form(False, description="Si True, guarda el audio procesado"),
    user_id: Optional[str] = Form(None, description="ID de usuario (opcional)"),
    kernel: Kernel = Depends(_get_kernel),
) -> Union[dict[str, Any], JSONResponse]:
    """Comparación de audio contra texto de referencia."""
    lang_resolved = _resolve_request_lang(lang)
    logger.info("=== /v1/compare REQUEST ===")
    logger.info(
        "text: %s, lang: %s, mode: %s, evaluation_level: %s",
        text,
        lang_resolved,
        mode,
        evaluation_level,
    )

    tmp_path = await _process_upload(audio)
    try:
        if backend:
            kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang_resolved})
        if textref:
            kernel.textref = registry.resolve_textref(
                textref.lower(), {"default_lang": lang_resolved}
            )
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
            pack_id = resolve_pack_id(lang=lang_resolved)
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
        asr_guard = _assert_real_ipa_asr(kernel.asr)
        if asr_guard:
            return asr_guard

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
                lang=lang_resolved,
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
        # Still run quality assessment
        quality_res, quality_warnings, _ = assess_audio_quality(
            str(tmp_path), user_id=user_id
        )

        service = ComparisonService(
            preprocessor=kernel.pre,
            asr=kernel.asr,
            textref=kernel.textref,
            comparator=kernel.comp,
            default_lang=lang_resolved,
        )
        payload = await service.compare_file_detail(
            str(tmp_path),
            text,
            lang=lang_resolved,
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
            "meta": {
                **(meta if isinstance(meta, dict) else {}),
                **({"audio_quality": quality_res.to_dict()} if quality_res else {}),
                **({"warnings": quality_warnings} if quality_warnings else {}),
            },
        }
    finally:
        await kernel.teardown()
        if tmp_path.exists():
            tmp_path.unlink()


# ── Quick-compare: fast path using cached kernel, no quality gates ───
@router.post("/quick-compare", response_model=CompareResponse)
async def quick_compare(
    audio: UploadFile = File(..., description="Archivo de audio a comparar"),
    text: str = Form(..., description="Texto de referencia"),
    lang: Optional[str] = Form(None, description="Idioma del audio"),
    mode: str = Form("objective", description="Modo: casual, objective, phonetic, auto"),
    evaluation_level: str = Form("phonemic", description="Nivel: phonemic, phonetic, auto"),
) -> Union[dict[str, Any], JSONResponse]:
    """Comparación rápida: ASR + textref + compare sin quality-gates.

    Usa el kernel singleton (ya inicializado) para evitar overhead de
    setup/teardown.  No ejecuta quality assessment ni adaptation.
    Ideal para revisiones rápidas durante la práctica.
    """
    kernel = await _get_or_create_kernel()
    lang_resolved = _resolve_request_lang(lang)
    asr_guard = _assert_real_ipa_asr(kernel.asr)
    if asr_guard:
        return asr_guard
    tmp_path = await _process_upload(audio)
    wav_tmp = False
    wav_path = str(tmp_path)
    try:
        wav_path, wav_tmp = ensure_wav(str(tmp_path))

        # Direct ASR → textref → compare pipeline
        audio_in: AudioInput = to_audio_input(wav_path)
        pre_result = await kernel.pre.process_audio(audio_in)
        processed = pre_result.get("audio", audio_in)

        asr_result = await kernel.asr.transcribe(processed, lang=lang_resolved)
        hyp_tokens = asr_result.get("tokens", [])
        if not hyp_tokens:
            raw_text = asr_result.get("raw_text", "")
            msg = "ASR no devolvió tokens IPA."
            if raw_text:
                msg += (
                    f" Texto detectado: '{raw_text}'. "
                    "Verifique language pack/configuración del backend."
                )
            else:
                msg += " El audio podría estar vacío, ser demasiado corto o no tener voz."
            raise ValidationError(msg)

        tr_result = await kernel.textref.to_ipa(text, lang=lang_resolved)
        ref_tokens = tr_result.get("tokens", [])

        result = await kernel.comp.compare(ref_tokens, hyp_tokens)

        per = result.get("per", 0.0)
        score = max(0.0, (1.0 - per) * 100.0)
        alignment = [list(pair) for pair in result.get("alignment", [])]

        return {
            **result,
            "alignment": alignment,
            "score": score,
            "mode": mode,
            "evaluation_level": evaluation_level,
            "ipa": " ".join(hyp_tokens),
            "tokens": hyp_tokens,
            "target_ipa": " ".join(ref_tokens),
            "meta": {
                "asr": asr_result.get("meta", {}),
                "compare": result.get("meta", {}),
                "quick": True,
            },
        }
    finally:
        if wav_tmp:
            cleanup_temp(wav_path)
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    audio: UploadFile = File(..., description="Archivo de audio a analizar"),
    text: str = Form(..., description="Texto de referencia"),
    lang: Optional[str] = Form(None, description="Idioma del audio"),
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
) -> Union[dict[str, Any], JSONResponse]:
    """Analiza la pronunciacion y genera feedback con LLM local."""
    lang_resolved = _resolve_request_lang(lang)
    tmp_path = await _process_upload(audio)
    kernel = _build_kernel(model_pack=model_pack, llm_name=llm)
    try:
        await kernel.setup()
        asr_guard = _assert_real_ipa_asr(kernel.asr)
        if asr_guard:
            return asr_guard
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
            lang=lang_resolved,
            mode=mode,
            evaluation_level=evaluation_level,
            feedback_level=feedback_level,
            prompt_path=prompt_file,
            output_schema_path=schema_file,
            user_id=user_id,
        )
        if persist:
            store = FeedbackStore()
            store.append(
                result, audio=dict(audio_in), meta={"text": text, "lang": lang_resolved}
            )
        return result
    finally:
        await kernel.teardown()
        if tmp_path.exists():
            tmp_path.unlink()
