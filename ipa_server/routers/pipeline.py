"""Core pipeline endpoints: transcribe, textref, compare, feedback."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional, Union, cast

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from ipa_core.audio.markers import mark_audio_preprocessed
from ipa_core.audio.files import cleanup_temp, ensure_wav
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.config import loader
from ipa_core.config.resolution import resolve_request_lang
from ipa_core.config.overrides import apply_overrides
from ipa_core.errors import ValidationError
from ipa_core.kernel.core import Kernel, create_kernel
from ipa_core.normalization.resolve import resolve_pack_id
from ipa_core.pipeline.runner import run_pipeline_with_pack, execute_pipeline
from ipa_core.pipeline.transcribe import EvaluationMode
from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens, clean_textref_tokens
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
from ipa_core.display.ipa_display import build_display, DisplayMode
from ipa_server.http_errors import error_response
from ipa_server.kernel_provider import get_kernel as _get_kernel, get_or_create_kernel
from ipa_server.models import (
    CompareResponse,
    FeedbackResponse,
    IPADisplay,
    IPADisplayToken,
    TextRefResponse,
    TranscriptionResponse,
)

logger = logging.getLogger("ipa_server")

router = APIRouter(prefix="/v1", tags=["pipeline"])


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
    from ipa_core.audio.files import _fix_wav_data_chunk
    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    # Corregir header WAV si el cliente (Flutter/record) escribió tamaños erróneos.
    if tmp_path.suffix.lower() == ".wav":
        _fix_wav_data_chunk(str(tmp_path))
    return tmp_path


def _asr_unavailable_response(*, backend_name: str, reason: str) -> JSONResponse:
    detail = (
        "No hay un modelo ASR IPA real activo para este endpoint. "
        f"Backend detectado: '{backend_name}'. Motivo: {reason}. "
        "Para corregirlo: (1) elimina PRONUNCIAPA_ASR=stub en el entorno, "
        "(2) configura un backend IPA real en configs/local.yaml "
        "(ej. allosaurus), (3) verifica disponibilidad en /api/asr/engines."
    )
    return error_response(
        status_code=503,
        detail=detail,
        error_type="asr_unavailable",
        extra={"backend": backend_name},
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


def _cleanup_uploaded_file(path: Path) -> None:
    """Limpia archivos temporales de upload sin tapar errores previos."""
    if path.exists():
        cleanup_temp(str(path))


def _resolve_safe_client_path(raw_path: Optional[str], *, label: str) -> Optional[Path]:
    """Valida rutas opcionales provistas por el cliente.

    Política de seguridad:
    - solo se aceptan rutas relativas al workspace actual
    - se rechazan rutas absolutas y traversal (`..`)
    - si la ruta resultante no existe, se rechaza con mensaje descriptivo
    """
    if not raw_path:
        return None

    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValidationError(f"{label} file not found or path not allowed: {candidate}")

    workspace_root = Path.cwd().resolve()
    resolved = (workspace_root / candidate).resolve(strict=False)
    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise ValidationError(f"{label} file not found or path not allowed: {candidate}") from exc

    if not resolved.exists():
        raise ValidationError(f"{label} file not found: {resolved}")

    return resolved


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
    lang_resolved = resolve_request_lang(lang)
    tmp_path = await _process_upload(audio)
    try:
        if backend:
            kernel.asr = registry.resolve_asr(
                backend.lower(), {"lang": lang_resolved}, strict_mode=True
            )
        if textref:
            kernel.textref = registry.resolve_textref(
                textref.lower(), {"default_lang": lang_resolved}, strict_mode=True
            )
        # Validate output_type BEFORE setup() — avoids loading heavy models for
        # non-IPA backends injected via the `backend` request parameter.
        asr_guard = _assert_real_ipa_asr(kernel.asr)
        if asr_guard:
            return asr_guard
        await kernel.setup()
        # (which also runs it) — no need to call it redundantly here.
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
        return {
            "ipa": payload.ipa,
            "tokens": payload.tokens,
            "lang": lang_resolved,
            "meta": meta,
        }
    finally:
        await kernel.teardown()
        _cleanup_uploaded_file(tmp_path)


@router.post("/textref", response_model=TextRefResponse)
async def textref_endpoint(
    text: str = Form(..., description="Texto a convertir a IPA"),
    lang: Optional[str] = Form(None, description="Idioma del texto"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    kernel: Kernel = Depends(_get_kernel),
) -> Union[dict[str, Any], JSONResponse]:
    """Convierte texto a IPA usando el proveedor TextRef."""
    lang_resolved = resolve_request_lang(lang)
    try:
        if textref:
            kernel.textref = registry.resolve_textref(
                textref.lower(), {"default_lang": lang_resolved}, strict_mode=True
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
    target_ipa: Optional[str] = Form(None, description="IPA objetivo manual (tokens separados por espacios)"),
    lang: Optional[str] = Form(None, description="Idioma del audio"),
    lang_source: Optional[str] = Form(None, description="Idioma origen (audio/ASR)"),
    lang_target: Optional[str] = Form(None, description="Idioma destino (texto/TextRef)"),
    mode: str = Form("objective", description="Modo: casual, objective, phonetic, auto"),
    evaluation_level: str = Form("phonemic", description="Nivel: phonemic, phonetic, auto"),
    force_phonetic: Optional[bool] = Form(
        None,
        description="Forzar modo y nivel fonético, sin degradación automática",
    ),
    allow_quality_downgrade: Optional[bool] = Form(
        None,
        description="Permitir degradación automática por calidad de audio",
    ),
    backend: Optional[str] = Form(None, description="Nombre del backend ASR"),
    textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
    comparator: Optional[str] = Form(None, description="Nombre del comparador"),
    pack: Optional[str] = Form(None, description="Language pack (dialecto) a usar"),
    display_mode: Optional[str] = Form(
        None,
        description="Modo de display IPA: 'technical' (IPA puro) o 'casual' (transliteración). "
                    "Si se proporciona, la respuesta incluye el campo 'display' con tokens coloreados.",
    ),
    persist: Optional[bool] = Form(False, description="Si True, guarda el audio procesado"),
    user_id: Optional[str] = Form(None, description="ID de usuario (opcional)"),
    kernel: Kernel = Depends(_get_kernel),
) -> Union[dict[str, Any], JSONResponse]:
    """Comparación de audio contra texto de referencia."""
    lang_source_resolved = resolve_request_lang(lang_source or lang)
    lang_target_resolved = resolve_request_lang(lang_target or lang)
    logger.info("=== /v1/compare REQUEST ===")
    logger.info(
        "text: %s, lang_source: %s, lang_target: %s, mode: %s, evaluation_level: %s",
        text,
        lang_source_resolved,
        lang_target_resolved,
        mode,
        evaluation_level,
    )

    tmp_path = await _process_upload(audio)
    try:
        if backend:
            kernel.asr = registry.resolve_asr(
                backend.lower(), {"lang": lang_source_resolved}, strict_mode=True
            )
        if textref:
            kernel.textref = registry.resolve_textref(
                textref.lower(), {"default_lang": lang_target_resolved}, strict_mode=True
            )
        if comparator:
            kernel.comp = registry.resolve_comparator(
                comparator.lower(), {}, strict_mode=True
            )

        # Validate output_type BEFORE setup() — see note in /v1/transcribe.
        asr_guard = _assert_real_ipa_asr(kernel.asr)
        if asr_guard:
            return asr_guard
        await kernel.setup()

        service = ComparisonService(
            preprocessor=kernel.pre,
            asr=kernel.asr,
            textref=kernel.textref,
            comparator=kernel.comp,
            default_lang=lang_target_resolved,
        )
        compare_payload = await service.compare_file_detail(
            str(tmp_path),
            text,
            target_ipa=target_ipa,
            lang=lang,
            lang_source=lang_source_resolved,
            lang_target=lang_target_resolved,
            evaluation_level=evaluation_level,
            force_phonetic=force_phonetic,
            allow_quality_downgrade=allow_quality_downgrade,
            pack=pack,
            mode=mode,
            user_id=user_id,
        )
        payload = compare_payload.to_response()

        # Poblar campo display si el cliente lo solicita
        if display_mode is not None:
            dm: DisplayMode = "casual" if display_mode == "casual" else "technical"
            try:
                disp_result = build_display(
                    payload.get("ops", []),
                    mode=dm,
                    level=payload["evaluation_level"],  # type: ignore[arg-type]
                    score=float(payload.get("score") or 0.0),
                )
                d = disp_result.as_dict()
                payload["display"] = IPADisplay(
                    mode=d["mode"],
                    level=d["level"],
                    ref_technical=d["ref_technical"],
                    ref_casual=d["ref_casual"],
                    hyp_technical=d["hyp_technical"],
                    hyp_casual=d["hyp_casual"],
                    score_color=d["score_color"],
                    legend=d["legend"],
                    tokens=[IPADisplayToken(**t) for t in d["tokens"]],
                ).model_dump()
            except Exception as _disp_exc:
                logger.warning("build_display falló: %s", _disp_exc)

        return payload
    finally:
        await kernel.teardown()
        _cleanup_uploaded_file(tmp_path)


# ── Quick-compare: fast path using cached kernel, no quality gates ───
@router.post("/quick-compare", response_model=CompareResponse)
async def quick_compare(
    audio: UploadFile = File(..., description="Archivo de audio a comparar"),
    text: str = Form(..., description="Texto de referencia"),
    target_ipa: Optional[str] = Form(None, description="IPA objetivo manual (tokens separados por espacios)"),
    lang: Optional[str] = Form(None, description="Idioma del audio"),
    lang_source: Optional[str] = Form(None, description="Idioma origen (audio/ASR)"),
    lang_target: Optional[str] = Form(None, description="Idioma destino (texto/TextRef)"),
    mode: str = Form("objective", description="Modo: casual, objective, phonetic, auto"),
    evaluation_level: str = Form("phonemic", description="Nivel: phonemic, phonetic, auto"),
) -> Union[dict[str, Any], JSONResponse]:
    """Comparación rápida: ASR + textref + compare sin quality-gates.

    Usa el kernel singleton (ya inicializado) para evitar overhead de
    setup/teardown.  No ejecuta quality assessment ni adaptation.
    Ideal para revisiones rápidas durante la práctica.
    """
    kernel = await get_or_create_kernel()
    lang_source_resolved = resolve_request_lang(lang_source or lang)
    lang_target_resolved = resolve_request_lang(lang_target or lang)
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
        audio_pre = mark_audio_preprocessed(audio_in)
        pre_result = await kernel.pre.process_audio(cast(AudioInput, audio_pre))
        processed = pre_result.get("audio", audio_in)

        asr_result = await kernel.asr.transcribe(processed, lang=lang_source_resolved)
        hyp_tokens = asr_result.get("tokens", [])
        if not hyp_tokens:
            raw_text = asr_result.get("raw_text", "")
            no_speech_hint = "ASR no devolvió tokens IPA."
            if raw_text:
                no_speech_hint += (
                    f" Texto detectado: '{raw_text}'. "
                    "Verifique language pack/configuración del backend."
                )
            else:
                no_speech_hint += (
                    " El audio podría estar vacío, ser demasiado corto o no tener voz."
                )
            logger.warning("quick_compare: ASR sin tokens")
            raise ValidationError(no_speech_hint)

        # Limpieza IPA unificada para quick-compare
        hyp_tokens = clean_asr_tokens(hyp_tokens, lang=lang_source_resolved)
        if not hyp_tokens:
            raise ValidationError(
                "ASR no devolvió tokens IPA válidos tras limpieza. "
                "El audio podría ser muy corto o contener sólo ruido."
            )

        if target_ipa and target_ipa.strip():
            ref_tokens = clean_textref_tokens(target_ipa.strip().split(), lang=lang_target_resolved)
        else:
            tr_result = await kernel.textref.to_ipa(text, lang=lang_target_resolved)
            ref_tokens = clean_textref_tokens(tr_result.get("tokens", []), lang=lang_target_resolved)

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
                "asr_confidences": asr_result.get("confidences"),
                "compare": result.get("meta", {}),
                "lang_source": lang_source_resolved,
                "lang_target": lang_target_resolved,
                "quick": True,
            },
        }
    finally:
        if wav_tmp:
            cleanup_temp(wav_path)
        _cleanup_uploaded_file(tmp_path)


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    audio: UploadFile = File(..., description="Archivo de audio a analizar"),
    text: str = Form(..., description="Texto de referencia"),
    target_ipa: Optional[str] = Form(None, description="IPA objetivo manual (tokens separados por espacios)"),
    lang: Optional[str] = Form(None, description="Idioma del audio"),
    lang_source: Optional[str] = Form(None, description="Idioma origen (audio/ASR)"),
    lang_target: Optional[str] = Form(None, description="Idioma destino (texto/TextRef)"),
    mode: str = Form("objective", description="Modo: casual, objective, phonetic, auto"),
    evaluation_level: str = Form(
        "phonemic", description="Nivel: phonemic, phonetic, auto"
    ),
    force_phonetic: Optional[bool] = Form(
        None,
        description="Forzar modo y nivel fonético, sin degradación automática",
    ),
    allow_quality_downgrade: Optional[bool] = Form(
        None,
        description="Permitir degradación automática por calidad de audio",
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
    lang_source_resolved = resolve_request_lang(lang_source or lang)
    lang_target_resolved = resolve_request_lang(lang_target or lang)
    tmp_path = await _process_upload(audio)
    # Use the singleton kernel when no per-request overrides are needed.
    # _build_kernel creates a fresh kernel (+ full Allosaurus load) each call.
    use_singleton = model_pack is None and llm is None
    if use_singleton:
        kernel = await get_or_create_kernel()
    else:
        kernel = _build_kernel(model_pack=model_pack, llm_name=llm)
    try:
        # Validate output_type BEFORE setup() — see note in /v1/transcribe.
        asr_guard = _assert_real_ipa_asr(kernel.asr)
        if asr_guard:
            return asr_guard
        if not use_singleton:
            await kernel.setup()
        audio_in: AudioInput = {
            "path": str(tmp_path),
            "sample_rate": 16000,
            "channels": 1,
        }
        service = FeedbackService(kernel)
        prompt_file = _resolve_safe_client_path(prompt_path, label="Prompt")
        schema_file = _resolve_safe_client_path(output_schema_path, label="Output schema")
        result = await service.analyze(
            audio=audio_in,
            text=text,
            lang=lang_target_resolved,
            lang_source=lang_source_resolved,
            lang_target=lang_target_resolved,
            target_ipa=target_ipa,
            mode=mode,
            evaluation_level=evaluation_level,
            force_phonetic=force_phonetic,
            allow_quality_downgrade=allow_quality_downgrade,
            feedback_level=feedback_level,
            prompt_path=prompt_file,
            output_schema_path=schema_file,
            user_id=user_id,
        )
        if persist:
            store = FeedbackStore()
            store.append(
                result,
                audio=dict(audio_in),
                meta={
                    "text": text,
                    "lang": lang_target_resolved,
                    "lang_source": lang_source_resolved,
                    "lang_target": lang_target_resolved,
                },
            )
        return result
    finally:
        if not use_singleton:
            await kernel.teardown()
        _cleanup_uploaded_file(tmp_path)
