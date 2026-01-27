"""Aplicación HTTP basada en FastAPI.

Este módulo define la API REST para interactuar con el microkernel de
PronunciaPA.
"""
from __future__ import annotations
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from fastapi import FastAPI, File, Form, UploadFile, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware que agrega headers de timing."""
    
    async def dispatch(self, request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        response.headers["X-Timestamp"] = datetime.now().isoformat()
        return response

from ipa_core.config import loader
from ipa_core.config.overrides import apply_overrides
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.errors import FileNotFound, KernelError, NotReadyError, UnsupportedFormat, ValidationError
from ipa_core.plugins import registry
from ipa_core.services.comparison import ComparisonService
from ipa_core.services.feedback import FeedbackService
from ipa_core.services.feedback_store import FeedbackStore
from ipa_core.services.transcription import TranscriptionService
from ipa_core.types import AudioInput
from ipa_core.pipeline.runner import run_pipeline_with_pack
from ipa_core.pipeline.transcribe import EvaluationMode
from ipa_core.phonology.representation import RepresentationLevel
from ipa_server.models import TranscriptionResponse, TextRefResponse, CompareResponse, FeedbackResponse, EditOp


def _get_kernel() -> Kernel:
    """Carga la configuración y crea el kernel (Inyectable)."""
    try:
        cfg = loader.load_config()
        return create_kernel(cfg)
    except KernelError as e:
        # Fallback para errores de inicialización pesados
        raise e


def _build_kernel(
    *,
    model_pack: Optional[str] = None,
    llm_name: Optional[str] = None,
) -> Kernel:
    cfg = loader.load_config()
    cfg = apply_overrides(cfg, model_pack=model_pack, llm_name=llm_name)
    return create_kernel(cfg)


def get_app() -> FastAPI:
    """Construye y configura la aplicación FastAPI."""
    app = FastAPI(
        title="PronunciaPA API",
        description="API para reconocimiento y evaluación fonética",
        version="0.1.0"
    )

    # Configurar CORS
    raw_origins = os.environ.get("PRONUNCIAPA_ALLOWED_ORIGINS", "")
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    
    if not allowed_origins and os.environ.get("DEBUG"):
        allowed_origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Agregar middleware de timing
    app.add_middleware(TimingMiddleware)

    # Handlers de excepciones
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        import logging
        logger = logging.getLogger("ipa_server")
        logger.warning(f"Validation error on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
                "type": "validation_error",
                "path": request.url.path
            },
        )

    @app.exception_handler(UnsupportedFormat)
    async def unsupported_exception_handler(request: Request, exc: UnsupportedFormat):
        return JSONResponse(
            status_code=415,
            content={"detail": str(exc), "type": "unsupported_format"},
        )

    @app.exception_handler(FileNotFound)
    async def file_not_found_handler(request: Request, exc: FileNotFound):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "file_not_found"},
        )

    @app.exception_handler(KeyError)
    async def plugin_not_found_handler(request: Request, exc: KeyError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "plugin_not_found"},
        )

    @app.exception_handler(NotReadyError)
    async def not_ready_exception_handler(request: Request, exc: NotReadyError):
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "type": "not_ready"},
        )

    @app.exception_handler(KernelError)
    async def kernel_exception_handler(request: Request, exc: KernelError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": "kernel_error"},
        )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Endpoint de salud mejorado con info del sistema."""
        from ipa_core.packs.loader import DEFAULT_PACKS_DIR
        from ipa_core.plugins.models import storage
        
        # Detectar language packs
        try:
            packs = [d.name for d in DEFAULT_PACKS_DIR.iterdir() 
                     if d.is_dir() and not d.name.startswith(".")]
        except Exception:
            packs = []
        
        # Detectar modelos locales
        try:
            models = storage.scan_models()
        except Exception:
            models = []
        
        return {
            "status": "ok",
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(),
            "language_packs": packs,
            "local_models": len(models),
        }

    async def _process_upload(audio: UploadFile) -> Path:
        """Guarda un UploadFile en un archivo temporal y retorna su ruta."""
        suffix = Path(audio.filename).suffix if audio.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            return Path(tmp.name)

    @app.post("/v1/transcribe", response_model=TranscriptionResponse)
    async def transcribe(
        audio: UploadFile = File(..., description="Archivo de audio a transcribir"),
        lang: str = Form("es", description="Idioma del audio"),
        backend: Optional[str] = Form(None, description="Nombre del backend ASR"),
        textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
        kernel: Kernel = Depends(_get_kernel)
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
            payload = await service.transcribe_file(str(tmp_path), lang=lang)
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

    @app.post("/v1/textref", response_model=TextRefResponse)
    async def textref(
        text: str = Form(..., description="Texto a convertir a IPA"),
        lang: str = Form("es", description="Idioma del texto"),
        textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
        kernel: Kernel = Depends(_get_kernel)
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

    @app.post("/v1/compare", response_model=CompareResponse)
    async def compare(
        audio: UploadFile = File(..., description="Archivo de audio a comparar"),
        text: str = Form(..., description="Texto de referencia"),
        lang: str = Form("es", description="Idioma del audio"),
        mode: str = Form("objective", description="Modo: casual, objective, phonetic"),
        evaluation_level: str = Form("phonemic", description="Nivel: phonemic, phonetic"),
        backend: Optional[str] = Form(None, description="Nombre del backend ASR"),
        textref: Optional[str] = Form(None, description="Nombre del proveedor texto→IPA"),
        comparator: Optional[str] = Form(None, description="Nombre del comparador"),
        pack: Optional[str] = Form(None, description="Language pack (dialecto) a usar"),
        kernel: Kernel = Depends(_get_kernel)
    ) -> dict[str, Any]:
        """Comparación de audio contra texto de referencia.
        
        Parámetros:
        - mode: casual (permisivo), objective (balance), phonetic (estricto)
        - evaluation_level: phonemic (subyacente) o phonetic (superficial)
        """
        tmp_path = await _process_upload(audio)
        try:
            if backend:
                kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
            if textref:
                kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
            if comparator:
                kernel.comp = registry.resolve_comparator(comparator.lower(), {})
            if pack:
                kernel.pack = registry.resolve_pack(pack.lower())
            await kernel.setup()
            if pack and getattr(kernel, "pack", None):
                # Comparación usando language pack (derive/collapse + scoring profile)
                comp_res = await run_pipeline_with_pack(
                    pre=kernel.pre,
                    asr=kernel.asr,
                    textref=kernel.textref,
                    audio={"path": str(tmp_path), "sample_rate": 16000, "channels": 1},
                    text=text,
                    pack=kernel.pack,
                    lang=lang,
                    mode=EvaluationMode(mode),
                    evaluation_level=RepresentationLevel(evaluation_level),
                )
                return {
                    "mode": mode,
                    "evaluation_level": evaluation_level,
                    "distance": comp_res.distance,
                    "score": comp_res.score,
                    "operations": comp_res.operations,
                    "ipa": comp_res.observed.to_ipa(with_delimiters=False),
                    "tokens": comp_res.observed.segments,
                    "target": comp_res.target.to_ipa(with_delimiters=False),
                }
            # Fallback al comparador clásico
            service = ComparisonService(
                preprocessor=kernel.pre,
                asr=kernel.asr,
                textref=kernel.textref,
                comparator=kernel.comp,
                default_lang=lang,
            )
            payload = await service.compare_file_detail(str(tmp_path), text, lang=lang)
            res = payload.result
            hyp_tokens = payload.hyp_tokens
            meta = payload.meta
            
            # Calcular score basado en PER y modo
            per = res.get("per", 0.0)
            base_score = max(0.0, (1.0 - per) * 100.0)
            
            return {
                **res,
                "score": base_score,
                "mode": mode,
                "evaluation_level": evaluation_level,
                "ipa": " ".join(hyp_tokens),
                "tokens": hyp_tokens,
                "meta": meta,
            }
        finally:
            await kernel.teardown()
            if tmp_path.exists():
                tmp_path.unlink()

    @app.post("/v1/feedback", response_model=FeedbackResponse)
    async def feedback(
        audio: UploadFile = File(..., description="Archivo de audio a analizar"),
        text: str = Form(..., description="Texto de referencia"),
        lang: str = Form("es", description="Idioma del audio"),
        mode: str = Form("objective", description="Modo: casual, objective, phonetic"),
        evaluation_level: str = Form("phonemic", description="Nivel: phonemic, phonetic"),
        feedback_level: Optional[str] = Form(
            None,
            description="Nivel de feedback: casual (amigable) o precise (tecnico)",
        ),
        model_pack: Optional[str] = Form(None, description="Model pack a usar (opcional)"),
        llm: Optional[str] = Form(None, description="Adapter LLM a usar (opcional)"),
        prompt_path: Optional[str] = Form(None, description="Ruta a prompt override (opcional)"),
        output_schema_path: Optional[str] = Form(None, description="Ruta a schema override (opcional)"),
        persist: bool = Form(False, description="Guardar resultado localmente"),
    ) -> dict[str, Any]:
        """Analiza la pronunciacion y genera feedback con LLM local."""
        tmp_path = await _process_upload(audio)
        kernel = _build_kernel(model_pack=model_pack, llm_name=llm)
        try:
            await kernel.setup()
            audio_in: AudioInput = {"path": str(tmp_path), "sample_rate": 16000, "channels": 1}
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
            )
            if persist:
                store = FeedbackStore()
                store.append(result, audio=audio_in, meta={"text": text, "lang": lang})
            return result
        finally:
            await kernel.teardown()
            if tmp_path.exists():
                tmp_path.unlink()

    return app
