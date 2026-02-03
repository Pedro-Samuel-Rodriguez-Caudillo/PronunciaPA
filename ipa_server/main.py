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
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, Form, UploadFile, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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
from ipa_server.realtime import realtime_router


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

    # Incluir router de WebSocket para tiempo real
    app.include_router(realtime_router)

    # Handlers de excepciones
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        import logging
        import traceback
        logger = logging.getLogger("ipa_server")
        logger.error(f"Validation error on {request.url.path}: {exc}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        errors_list = exc.errors() if hasattr(exc, 'errors') else []
        logger.error(f"Error details: {errors_list}")
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
                "type": "validation_error",
                "path": request.url.path,
                "errors": errors_list
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
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        import logging
        import traceback
        logger = logging.getLogger("ipa_server")
        logger.error(f"Unhandled exception on {request.url.path}: {exc}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "path": request.url.path
            },
        )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Endpoint de salud con diagnóstico detallado de componentes."""
        from ipa_core.packs.loader import DEFAULT_PACKS_DIR
        from ipa_core.plugins.models import storage
        from ipa_core.errors import NotReadyError
        
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
        
        # Diagnóstico de componentes
        components = {}
        cfg = loader.load_config()
        
        # ASR Backend
        try:
            asr = registry.resolve_asr(cfg.backend.name, cfg.backend.params, strict_mode=True)
            await asr.setup()
            components["asr"] = {
                "name": cfg.backend.name,
                "ready": True,
                "output_type": getattr(asr, "output_type", "unknown")
            }
            await asr.teardown()
        except (KeyError, NotReadyError) as e:
            components["asr"] = {
                "name": cfg.backend.name,
                "ready": False,
                "error": str(e)
            }
        except Exception as e:
            components["asr"] = {
                "name": cfg.backend.name,
                "ready": False,
                "error": f"Unexpected error: {str(e)}"
            }
        
        # TextRef
        try:
            textref = registry.resolve_textref(cfg.textref.name, cfg.textref.params, strict_mode=True)
            await textref.setup()
            components["textref"] = {
                "name": cfg.textref.name,
                "ready": True
            }
            await textref.teardown()
        except (KeyError, NotReadyError) as e:
            components["textref"] = {
                "name": cfg.textref.name,
                "ready": False,
                "error": str(e)
            }
        except Exception as e:
            components["textref"] = {
                "name": cfg.textref.name,
                "ready": False,
                "error": f"Unexpected error: {str(e)}"
            }
        
        # LLM (opcional)
        if cfg.llm and cfg.llm.name != "auto":
            try:
                llm = registry.resolve_llm(cfg.llm.name, cfg.llm.params, strict_mode=True)
                await llm.setup()
                components["llm"] = {
                    "name": cfg.llm.name,
                    "ready": True
                }
                await llm.teardown()
            except (KeyError, NotReadyError) as e:
                components["llm"] = {
                    "name": cfg.llm.name,
                    "ready": False,
                    "error": str(e)
                }
            except Exception as e:
                components["llm"] = {
                    "name": cfg.llm.name,
                    "ready": False,
                    "error": f"Unexpected error: {str(e)}"
                }
        
        # TTS (opcional)
        if cfg.tts and cfg.tts.name != "default":
            try:
                tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params, strict_mode=True)
                await tts.setup()
                components["tts"] = {
                    "name": cfg.tts.name,
                    "ready": True
                }
                await tts.teardown()
            except (KeyError, NotReadyError) as e:
                components["tts"] = {
                    "name": cfg.tts.name,
                    "ready": False,
                    "error": str(e)
                }
            except Exception as e:
                components["tts"] = {
                    "name": cfg.tts.name,
                    "ready": False,
                    "error": f"Unexpected error: {str(e)}"
                }
        
        return {
            "status": "ok",
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(),
            "strict_mode": cfg.strict_mode,
            "components": components,
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
        persist: Optional[bool] = Form(False, description="Si True, guarda el audio procesado"),
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
        persist: Optional[bool] = Form(False, description="Si True, guarda el audio procesado"),
        kernel: Kernel = Depends(_get_kernel)
    ) -> dict[str, Any]:
        """Comparación de audio contra texto de referencia.
        
        Parámetros:
        - mode: casual (permisivo), objective (balance), phonetic (estricto)
        - evaluation_level: phonemic (subyacente) o phonetic (superficial)
        """
        import logging
        logger = logging.getLogger("ipa_server")
        logger.info(f"=== /v1/compare REQUEST ===")
        logger.info(f"audio: {audio.filename if audio else 'None'}")
        logger.info(f"text: {text}")
        logger.info(f"lang: {lang}")
        logger.info(f"mode: {mode}")
        logger.info(f"evaluation_level: {evaluation_level}")
        logger.info(f"backend: {backend}")
        logger.info(f"textref: {textref}")
        logger.info(f"comparator: {comparator}")
        logger.info(f"pack: {pack}")
        
        tmp_path = await _process_upload(audio)
        try:
            if backend:
                kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
            if textref:
                kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
            if comparator:
                kernel.comp = registry.resolve_comparator(comparator.lower(), {})
            
            # Cargar language pack si se especifica
            language_pack = None
            if pack:
                from ipa_core.packs.loader import load_language_pack
                try:
                    language_pack = load_language_pack(pack.lower())
                    kernel.language_pack = language_pack
                except Exception as e:
                    import logging
                    logger = logging.getLogger("ipa_server")
                    logger.warning(f"No se pudo cargar language pack '{pack}': {e}")
            
            await kernel.setup()
            
            if language_pack:
                # Comparación usando language pack (derive/collapse + scoring profile)
                comp_res = await run_pipeline_with_pack(
                    pre=kernel.pre,
                    asr=kernel.asr,
                    textref=kernel.textref,
                    audio={"path": str(tmp_path), "sample_rate": 16000, "channels": 1},
                    text=text,
                    pack=language_pack,
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
            
            # Fallback al comparador clásico (sin language pack)
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
            ref_tokens = payload.ref_tokens  # Get reference tokens
            meta = payload.meta
            
            logger.info(f"=== /v1/compare RESULT ===")
            logger.info(f"ref_tokens: {ref_tokens}")
            logger.info(f"hyp_tokens: {hyp_tokens}")
            logger.info(f"per: {res.get('per')}")
            logger.info(f"ops: {res.get('ops')}")
            
            # Calcular score basado en PER y modo
            per = res.get("per", 0.0)
            base_score = max(0.0, (1.0 - per) * 100.0)
            
            # Convertir alignment de tuples a lists para JSON
            alignment = [list(pair) for pair in res.get("alignment", [])]
            
            return {
                **res,
                "alignment": alignment,
                "score": base_score,
                "mode": mode,
                "evaluation_level": evaluation_level,
                "ipa": " ".join(hyp_tokens),
                "tokens": hyp_tokens,
                "target_ipa": " ".join(ref_tokens),  # Add target IPA
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

    # ============ TTS ENDPOINT ============
    
    @app.get("/api/tts/speak")
    async def tts_speak(
        text: str = Query(..., description="Texto a sintetizar"),
        lang: str = Query("es", description="Código de idioma (es, en, etc.)"),
        voice: Optional[str] = Query(None, description="Voz específica (opcional)"),
    ):
        """Sintetiza texto a audio usando TTS (eSpeak-NG por defecto).
        
        Genera audio pronunciando el texto dado en el idioma especificado.
        Útil para reproducir pronunciación de referencia.
        
        Args:
            text: Texto a pronunciar
            lang: Código de idioma (es, en, fr, pt)
            voice: Voz específica del backend (opcional)
            
        Returns:
            Audio WAV con el texto sintetizado
        """
        import tempfile
        
        if not text or not text.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "El texto no puede estar vacío"}
            )
        
        try:
            # Cargar configuración y resolver TTS
            cfg = loader.load_config()
            from ipa_core.plugins import registry
            tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params)
            await tts.setup()
            
            # Crear archivo temporal para el audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                output_path = tmp_file.name
            
            try:
                result = await tts.synthesize(
                    text=text.strip(),
                    lang=lang,
                    voice=voice,
                    output_path=output_path,
                )
                
                # Retornar el archivo de audio
                return FileResponse(
                    path=output_path,
                    media_type="audio/wav",
                    filename=f"tts_{lang}_{text[:20].replace(' ', '_')}.wav",
                    headers={
                        "X-TTS-Text": text[:100],
                        "X-TTS-Lang": lang,
                        "X-TTS-Backend": result.get("meta", {}).get("backend", "unknown"),
                    }
                )
            finally:
                await tts.teardown()
                
        except NotReadyError as e:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "TTS no disponible",
                    "detail": str(e),
                    "hint": "Instala eSpeak-NG: https://github.com/espeak-ng/espeak-ng/releases"
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"Error generando audio: {str(e)}",
                    "text": text[:100],
                }
            )
    
    @app.get("/api/tts/status")
    async def tts_status():
        """Verifica el estado del sistema TTS.
        
        Returns:
            Estado del backend TTS y backends disponibles.
        """
        try:
            cfg = loader.load_config()
            from ipa_core.plugins import registry
            tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params)
            await tts.setup()
            await tts.teardown()
            
            return {
                "status": "ready",
                "backend": cfg.tts.name,
                "prefer": cfg.tts.params.get("prefer", "system") if cfg.tts.params else "system",
            }
        except NotReadyError as e:
            return {
                "status": "not_ready",
                "error": str(e),
                "hint": "Instala eSpeak-NG: https://github.com/espeak-ng/espeak-ng/releases"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ============ IPA SOUNDS CATALOG ENDPOINT ============
    
    @app.get("/api/ipa-sounds")
    async def get_ipa_sounds(
        lang: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict[str, Any]:
        """Retorna el catálogo de sonidos IPA por idioma.
        
        Args:
            lang: Código de idioma (es, en). Si no se especifica, retorna todos.
            category: Filtrar por categoría (consonant, vowel, diphthong).
            
        Returns:
            Catálogo estructurado de sonidos IPA con ejemplos.
        """
        from pathlib import Path
        import yaml
        
        catalog_dir = Path(__file__).parent.parent / "data" / "ipa_catalog"
        
        # Si se especifica idioma, cargar solo ese
        if lang:
            catalog_file = catalog_dir / f"{lang}.yaml"
            if not catalog_file.exists():
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Idioma no encontrado: {lang}", "available": ["es", "en"]}
                )
            
            with open(catalog_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            sounds = data.get("sounds", [])
            
            # Filtrar por categoría si se especifica
            if category:
                sounds = [s for s in sounds if category in s.get("tags", [])]
            
            # Añadir URL de audio para cada sonido
            for sound in sounds:
                sound_id = sound.get("id")
                if sound_id:
                    from urllib.parse import quote
                    sound["audio_url"] = f"/api/ipa-sounds/audio?sound_id={quote(sound_id)}"
            
            return {
                "language": lang,
                "total": len(sounds),
                "sounds": sounds,
            }
        
        # Si no se especifica, cargar todos los idiomas
        all_sounds = {}
        for yaml_file in catalog_dir.glob("*.yaml"):
            lang_code = yaml_file.stem
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            sounds = data.get("sounds", [])
            
            # Filtrar por categoría si se especifica
            if category:
                sounds = [s for s in sounds if category in s.get("tags", [])]
            
            all_sounds[lang_code] = {
                "total": len(sounds),
                "sounds": sounds,
            }
        
        return {
            "languages": list(all_sounds.keys()),
            "data": all_sounds,
        }
    
    @app.get("/api/ipa-sounds/audio")
    async def get_ipa_sound_audio(
        sound_id: str,
        example: Optional[str] = None,
    ):
        """Genera audio TTS para un sonido IPA específico.
        
        Args:
            sound_id: ID del sonido (ej: es/ɾ, es/r)
            example: Texto de ejemplo opcional. Si no se provee, usa el primer ejemplo del catálogo.
            
        Returns:
            Audio WAV del ejemplo pronunciado.
        """
        from pathlib import Path
        from fastapi.responses import FileResponse
        import yaml
        import tempfile
        
        # Parsear sound_id (formato: lang/ipa)
        parts = sound_id.split("/", 1)
        if len(parts) != 2:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid sound_id format. Expected: lang/ipa (e.g., es/r)"}
            )
        
        lang, ipa = parts
        
        # Cargar catálogo para encontrar ejemplos
        catalog_dir = Path(__file__).parent.parent / "data" / "ipa_catalog"
        catalog_file = catalog_dir / f"{lang}.yaml"
        
        if not catalog_file.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Language catalog not found: {lang}"}
            )
        
        with open(catalog_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Buscar el sonido en el catálogo
        sound_data = None
        for sound in data.get("sounds", []):
            if sound.get("id") == sound_id or sound.get("ipa") == ipa:
                sound_data = sound
                break
        
        if not sound_data:
            return JSONResponse(
                status_code=404,
                content={"error": f"Sound not found: {sound_id}"}
            )
        
        # Obtener texto de ejemplo
        if not example:
            # Usar el primer ejemplo del catálogo
            contexts = sound_data.get("contexts", {})
            example = None
            for context_data in contexts.values():
                seeds = context_data.get("seeds", [])
                if seeds:
                    example = seeds[0].get("text")
                    break
            
            if not example:
                return JSONResponse(
                    status_code=404,
                    content={"error": "No example text available for this sound"}
                )
        
        # Generar audio usando TTS
        try:
            # Crear kernel minimal solo con TTS (sin ASR)
            cfg = loader.load_config()
            
            # Obtener TTS directamente del registry sin crear el kernel completo
            from ipa_core.plugins import registry
            tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params)
            await tts.setup()
            
            # Crear archivo temporal para el audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                output_path = tmp_file.name
            
            try:
                result = await tts.synthesize(
                    text=example,
                    lang=lang,
                    output_path=output_path,
                )
                
                # Retornar el archivo de audio
                return FileResponse(
                    path=output_path,
                    media_type="audio/wav",
                    filename=f"{sound_id.replace('/', '_')}_{example[:20]}.wav",
                    headers={
                        "X-Example-Text": example,
                        "X-Sound-IPA": ipa,
                    }
                )
            finally:
                await tts.teardown()
                
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"Failed to generate audio: {str(e)}",
                    "text": example,
                }
            )

    @app.get("/api/ipa-learn/{lang}")
    async def get_ipa_learning_content(
        lang: str,
        sound_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retorna contenido educativo para aprender IPA.
        
        Args:
            lang: Código de idioma (en, es)
            sound_id: ID de sonido específico para obtener lección detallada
            
        Returns:
            Contenido educativo: articulación, errores comunes, tips, drills
        """
        from pathlib import Path
        import yaml
        
        catalog_dir = Path(__file__).parent.parent / "data" / "ipa_catalog"
        learning_file = catalog_dir / f"{lang}_learning.yaml"
        
        if not learning_file.exists():
            # Fallback al catálogo básico
            basic_file = catalog_dir / f"{lang}.yaml"
            if not basic_file.exists():
                return JSONResponse(
                    status_code=404,
                    content={"error": f"No learning content for: {lang}"}
                )
            # Retornar catálogo básico si no hay contenido de aprendizaje
            with open(basic_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return {
                "language": lang,
                "has_learning_content": False,
                "sounds": data.get("sounds", []),
            }
        
        with open(learning_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Si se pide un sonido específico
        if sound_id:
            for sound in data.get("sounds", []):
                if sound.get("id") == sound_id:
                    return {
                        "language": lang,
                        "has_learning_content": True,
                        "sound": sound,
                    }
            return JSONResponse(
                status_code=404,
                content={"error": f"Sound not found: {sound_id}"}
            )
        
        # Retornar resumen del contenido
        return {
            "language": lang,
            "name": data.get("name", lang),
            "has_learning_content": True,
            "inventory": data.get("inventory", {}),
            "modules": data.get("modules", []),
            "progression": data.get("progression", {}),
            "sounds_count": len(data.get("sounds", [])),
            "sounds": [
                {
                    "id": s.get("id"),
                    "ipa": s.get("ipa"),
                    "common_name": s.get("common_name"),
                    "difficulty": s.get("difficulty", 1),
                }
                for s in data.get("sounds", [])
            ],
        }

    @app.get("/api/ipa-drills/{lang}/{sound_id:path}")
    async def get_sound_drills(
        lang: str,
        sound_id: str,
        drill_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retorna ejercicios de práctica para un sonido específico.
        
        Args:
            lang: Código de idioma (en, es)
            sound_id: ID del sonido (ej: θ, ð, ɹ)
            drill_type: Tipo de drill (isolation, syllable, word_initial, etc.)
            
        Returns:
            Lista de drills con palabras/frases de práctica
        """
        from pathlib import Path
        import yaml
        import random
        
        catalog_dir = Path(__file__).parent.parent / "data" / "ipa_catalog"
        
        # Intentar cargar archivo de aprendizaje primero
        learning_file = catalog_dir / f"{lang}_learning.yaml"
        basic_file = catalog_dir / f"{lang}.yaml"
        
        full_sound_id = f"{lang}/{sound_id}"
        drills = []
        sound_info = None
        
        # Buscar en archivo de aprendizaje
        if learning_file.exists():
            with open(learning_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            for sound in data.get("sounds", []):
                if sound.get("id") == full_sound_id or sound.get("ipa") == sound_id:
                    sound_info = sound
                    drills = sound.get("drills", [])
                    break
        
        # Si no hay drills, generar desde catálogo básico
        if not drills and basic_file.exists():
            with open(basic_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            for sound in data.get("sounds", []):
                if sound.get("id") == full_sound_id or sound.get("ipa") == sound_id:
                    sound_info = sound
                    contexts = sound.get("contexts", {})
                    
                    # Generar drills desde contexts
                    for position, context_data in contexts.items():
                        seeds = context_data.get("seeds", [])
                        if seeds:
                            drills.append({
                                "type": f"word_{position}",
                                "instruction": f"Practice words with /{sound_id}/ in {position} position",
                                "targets": [s.get("text") for s in seeds],
                            })
                    break
        
        if not sound_info:
            return JSONResponse(
                status_code=404,
                content={"error": f"Sound not found: {sound_id}"}
            )
        
        # Filtrar por tipo si se especifica
        if drill_type:
            drills = [d for d in drills if d.get("type") == drill_type]
        
        # Añadir URLs de audio para cada target
        for drill in drills:
            targets = drill.get("targets", [])
            pairs = drill.get("pairs", [])
            
            # Añadir audio a targets
            if targets:
                drill["targets_with_audio"] = [
                    {
                        "text": t,
                        "audio_url": f"/api/ipa-sounds/audio?sound_id={full_sound_id}&example={t}"
                    }
                    for t in targets[:5]  # Limitar a 5
                ]
            
            # Añadir audio a pairs
            if pairs:
                drill["pairs_with_audio"] = [
                    {
                        "word1": p[0],
                        "word2": p[1],
                        "audio1_url": f"/api/ipa-sounds/audio?sound_id={full_sound_id}&example={p[0]}",
                        "audio2_url": f"/api/ipa-sounds/audio?sound_id={full_sound_id}&example={p[1]}",
                    }
                    for p in pairs[:5]
                ]
        
        return {
            "language": lang,
            "sound_id": full_sound_id,
            "ipa": sound_info.get("ipa"),
            "name": sound_info.get("common_name") or sound_info.get("label"),
            "difficulty": sound_info.get("difficulty", 1),
            "common_errors": sound_info.get("common_errors", []),
            "tips": sound_info.get("tips", []),
            "drills": drills,
            "total_drills": len(drills),
        }

    @app.get("/api/setup-status")
    async def setup_status() -> Dict[str, Any]:
        """Retorna estado de setup con instrucciones específicas para el OS actual."""
        import platform
        import shutil
        from ipa_core.errors import NotReadyError
        
        os_name = platform.system()  # 'Windows', 'Linux', 'Darwin'
        cfg = loader.load_config()
        
        status = {
            "os": os_name,
            "strict_mode": cfg.strict_mode,
            "checks": {}
        }
        
        # 1. Verificar Allosaurus (obligatorio)
        try:
            import allosaurus
            status["checks"]["allosaurus"] = {
                "installed": True,
                "version": getattr(allosaurus, "__version__", "unknown"),
                "instructions": None
            }
        except ImportError:
            status["checks"]["allosaurus"] = {
                "installed": False,
                "instructions": {
                    "command": "pip install allosaurus",
                    "description": "Backend ASR obligatorio para reconocimiento fonético"
                }
            }
        
        # 2. Verificar eSpeak-NG (recomendado para TextRef)
        espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        if not espeak_bin and os_name == "Windows":
            # Buscar en rutas típicas de Windows
            windows_paths = [
                r"C:\\Program Files\\eSpeak NG\\espeak-ng.exe",
                r"C:\\Program Files (x86)\\eSpeak NG\\espeak-ng.exe"
            ]
            for path in windows_paths:
                if Path(path).exists():
                    espeak_bin = path
                    break
        
        if espeak_bin:
            status["checks"]["espeak"] = {
                "installed": True,
                "path": espeak_bin,
                "instructions": None
            }
        else:
            if os_name == "Windows":
                instructions = {
                    "url": "https://github.com/espeak-ng/espeak-ng/releases",
                    "description": "Descargar e instalar eSpeak NG para Windows",
                    "env_var": "PRONUNCIAPA_ESPEAK_BIN=C:\\Program Files\\eSpeak NG\\espeak-ng.exe"
                }
            elif os_name == "Linux":
                instructions = {
                    "command": "sudo apt-get install espeak-ng",
                    "description": "Instalar eSpeak NG desde repositorios"
                }
            else:  # macOS
                instructions = {
                    "command": "brew install espeak-ng",
                    "description": "Instalar eSpeak NG con Homebrew"
                }
            status["checks"]["espeak"] = {
                "installed": False,
                "instructions": instructions
            }
        
        # 3. Verificar Ollama (opcional para LLM)
        if cfg.llm and cfg.llm.name == "ollama":
            import httpx
            try:
                base_url = cfg.llm.params.get("base_url", "http://localhost:11434")
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"{base_url}/api/tags")
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        status["checks"]["ollama"] = {
                            "installed": True,
                            "running": True,
                            "models": models,
                            "instructions": None
                        }
                    else:
                        status["checks"]["ollama"] = {
                            "installed": True,
                            "running": False,
                            "instructions": {
                                "command": "ollama serve",
                                "description": "Iniciar servidor Ollama"
                            }
                        }
            except Exception:
                status["checks"]["ollama"] = {
                    "installed": False,
                    "running": False,
                    "instructions": {
                        "url": "https://ollama.ai/download",
                        "commands": [
                            "# Descargar e instalar Ollama",
                            "ollama pull tinyllama",
                            "ollama serve"
                        ],
                        "description": "Instalar Ollama para soporte de LLM"
                    }
                }
        
        # 4. Script de descarga de modelos
        status["checks"]["models_script"] = {
            "available": True,
            "instructions": {
                "command": "python scripts/download_models.py",
                "description": "Descargar modelos de Allosaurus y otros componentes"
            }
        }
        
        return status

    # ============ MODEL INSTALLATION ENDPOINTS ============
    
    @app.get("/api/models")
    async def list_models() -> dict[str, Any]:
        """Lista todos los modelos disponibles con su estado de instalación.
        
        Permite a clientes (CLI, Desktop, Android) ver qué está instalado
        y qué falta instalar.
        """
        from ipa_core.services.model_installer import get_installer
        
        installer = get_installer()
        models = await installer.get_all_status()
        
        # Agrupar por categoría
        by_category = {}
        for model in models:
            cat = model.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(model.to_dict())
        
        # Calcular resumen
        total = len(models)
        installed = sum(1 for m in models if m.status.value == "installed")
        required_missing = [m.id for m in models if m.is_required and m.status.value != "installed"]
        
        return {
            "summary": {
                "total": total,
                "installed": installed,
                "missing": total - installed,
                "required_missing": required_missing,
                "ready": len(required_missing) == 0,
            },
            "models": by_category,
        }
    
    @app.post("/api/models/{model_id}/install")
    async def install_model(model_id: str) -> dict[str, Any]:
        """Instalar un modelo específico.
        
        Args:
            model_id: ID del modelo a instalar (ej: "epitran", "tinyllama")
        
        Returns:
            Estado del modelo después de la instalación.
        """
        from ipa_core.services.model_installer import get_installer, MODEL_CATALOG
        
        if model_id not in MODEL_CATALOG:
            return JSONResponse(
                status_code=404,
                content={"error": f"Modelo no encontrado: {model_id}"}
            )
        
        installer = get_installer()
        
        try:
            result = await installer.install(model_id)
            return {
                "success": True,
                "model": result.to_dict(),
            }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "model_id": model_id,
                }
            )
    
    @app.post("/api/models/install-required")
    async def install_required_models() -> dict[str, Any]:
        """Instalar todos los modelos requeridos para funcionar.
        
        Endpoint de "quick setup" para nuevas instalaciones.
        """
        from ipa_core.services.model_installer import get_installer
        
        installer = get_installer()
        results = await installer.install_required()
        
        return {
            "installed": [r.to_dict() for r in results if r.status.value == "installed"],
            "errors": [r.to_dict() for r in results if r.status.value == "error"],
            "ready": all(r.status.value == "installed" for r in results),
        }
    
    @app.post("/api/models/install-recommended")
    async def install_recommended_models() -> dict[str, Any]:
        """Instalar todos los modelos recomendados.
        
        Setup completo con todas las funcionalidades.
        """
        from ipa_core.services.model_installer import get_installer
        
        installer = get_installer()
        results = await installer.install_recommended()
        
        return {
            "installed": [r.to_dict() for r in results if r.status.value == "installed"],
            "errors": [r.to_dict() for r in results if r.status.value == "error"],
            "ready": all(r.status.value == "installed" for r in results),
        }
    
    @app.post("/api/quick-setup")
    async def quick_setup_endpoint() -> dict[str, Any]:
        """Setup rápido automático.
        
        Instala las dependencias Python necesarias (aiohttp, epitran)
        y verifica el estado del sistema.
        """
        from ipa_core.services.model_installer import quick_setup
        
        result = await quick_setup()
        
        # Agregar health check después del setup
        ready = all(
            v in ("installed", "already_installed") 
            for k, v in result.items() 
            if k in ("aiohttp", "epitran")
        )
        
        return {
            "components": result,
            "ready": ready,
            "next_steps": [] if ready else [
                "Instalar eSpeak-NG si no está instalado",
                "Instalar Ollama para feedback con LLM",
            ],
        }
    
    # ============ ASR ENGINE MANAGEMENT ENDPOINTS ============
    
    @app.get("/api/asr/engines")
    async def list_asr_engines() -> dict[str, Any]:
        """Lista los motores ASR disponibles con salida IPA.
        
        Muestra qué engines están instalados y listos para usar.
        """
        from ipa_core.backends.unified_ipa_backend import UnifiedIPABackend, ASREngine
        
        engines = []
        for engine in ASREngine:
            status = UnifiedIPABackend.check_engine_ready(engine)
            engines.append({
                "id": engine.value,
                "name": {
                    "allosaurus": "Allosaurus (Universal IPA)",
                    "wav2vec2-ipa": "Wav2Vec2 Large IPA",
                    "xlsr-ipa": "XLS-R 300M IPA (Multilingüe)",
                }.get(engine.value, engine.value),
                "ready": status["ready"],
                "missing": status["missing"],
                "message": status["message"],
                "description": {
                    "allosaurus": "ASR universal con 200+ idiomas. Ligero (~500MB), funciona en CPU.",
                    "wav2vec2-ipa": "Alta precisión fonética. Requiere ~1.2GB y GPU para velocidad óptima.",
                    "xlsr-ipa": "Multilingüe (128 idiomas). Buen balance precisión/velocidad.",
                }.get(engine.value, ""),
            })
        
        # Determinar cuál está activo
        try:
            cfg = loader.load_config()
            backend_params = cfg.backend.params if cfg.backend.params else {}
            current_engine = backend_params.get("engine", "allosaurus")
        except Exception:
            current_engine = "allosaurus"
        
        return {
            "current": current_engine,
            "engines": engines,
            "recommendation": "allosaurus",  # Recomendado por defecto
        }
    
    @app.post("/api/asr/engine/{engine_id}")
    async def set_asr_engine(engine_id: str) -> dict[str, Any]:
        """Cambiar el motor ASR activo.
        
        Args:
            engine_id: ID del engine (allosaurus, wav2vec2-ipa, xlsr-ipa)
            
        Note:
            Este cambio requiere reiniciar el servidor para tomar efecto.
            Para cambios en runtime, usar el header X-ASR-Engine en las requests.
        """
        from ipa_core.backends.unified_ipa_backend import UnifiedIPABackend, ASREngine
        
        # Validar engine
        try:
            engine = ASREngine(engine_id)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Engine no válido: {engine_id}",
                    "valid_engines": [e.value for e in ASREngine],
                }
            )
        
        # Verificar si está listo
        status = UnifiedIPABackend.check_engine_ready(engine)
        if not status["ready"]:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Engine {engine_id} no está listo",
                    "missing": status["missing"],
                    "install_command": f"pip install {' '.join(status['missing'])}",
                }
            )
        
        # Actualizar config (solo en memoria para esta sesión)
        # Para persistir, el usuario debe editar local.yaml
        return {
            "success": True,
            "engine": engine_id,
            "message": f"Engine cambiado a {engine_id}. Para hacer el cambio permanente, edita configs/local.yaml",
            "config_example": {
                "backend": {
                    "name": "unified_ipa",
                    "params": {
                        "engine": engine_id,
                        "device": "cpu",  # o "cuda" para GPU
                    }
                }
            }
        }
    
    @app.post("/api/asr/install/{engine_id}")
    async def install_asr_engine(engine_id: str) -> dict[str, Any]:
        """Instalar las dependencias para un motor ASR.
        
        Args:
            engine_id: ID del engine (allosaurus, wav2vec2-ipa, xlsr-ipa)
        """
        from ipa_core.backends.unified_ipa_backend import ASREngine
        from ipa_core.services.model_installer import get_installer
        
        # Mapear engine a modelo(s) a instalar
        engine_to_models = {
            "allosaurus": ["allosaurus"],
            "wav2vec2-ipa": ["torch", "transformers", "wav2vec2-ipa"],
            "xlsr-ipa": ["torch", "transformers", "xlsr-ipa"],
        }
        
        if engine_id not in engine_to_models:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Engine no válido: {engine_id}",
                    "valid_engines": list(engine_to_models.keys()),
                }
            )
        
        installer = get_installer()
        results = []
        errors = []
        
        for model_id in engine_to_models[engine_id]:
            try:
                result = await installer.install(model_id)
                results.append(result.to_dict())
            except Exception as e:
                errors.append({"model": model_id, "error": str(e)})
        
        return {
            "engine": engine_id,
            "installed": results,
            "errors": errors,
            "ready": len(errors) == 0,
        }

    return app

# Crear instancia global para uvicorn
app = get_app()