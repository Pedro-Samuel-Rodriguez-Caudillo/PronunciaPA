"""Model installation and ASR engine management endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ipa_core.config import loader

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
async def list_models():
    """Lista todos los modelos disponibles con su estado de instalación."""
    from ipa_core.services.model_installer import get_installer

    installer = get_installer()
    models = await installer.get_all_status()

    by_category: dict[str, list[dict[str, Any]]] = {}
    for model in models:
        cat = model.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(model.to_dict())

    total = len(models)
    installed = sum(1 for m in models if m.status.value == "installed")
    required_missing = [
        m.id for m in models if m.is_required and m.status.value != "installed"
    ]

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


@router.post("/models/{model_id}/install", response_model=None)
async def install_model(model_id: str):
    """Instalar un modelo específico."""
    from ipa_core.services.model_installer import MODEL_CATALOG, get_installer

    if model_id not in MODEL_CATALOG:
        return JSONResponse(
            status_code=404, content={"error": f"Modelo no encontrado: {model_id}"}
        )

    installer = get_installer()
    try:
        result = await installer.install(model_id)
        return {"success": True, "model": result.to_dict()}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "model_id": model_id},
        )


@router.post("/models/install-required")
async def install_required_models():
    """Instalar todos los modelos requeridos para funcionar."""
    from ipa_core.services.model_installer import get_installer

    installer = get_installer()
    results = await installer.install_required()
    return {
        "installed": [r.to_dict() for r in results if r.status.value == "installed"],
        "errors": [r.to_dict() for r in results if r.status.value == "error"],
        "ready": all(r.status.value == "installed" for r in results),
    }


@router.post("/models/install-recommended")
async def install_recommended_models():
    """Instalar todos los modelos recomendados."""
    from ipa_core.services.model_installer import get_installer

    installer = get_installer()
    results = await installer.install_recommended()
    return {
        "installed": [r.to_dict() for r in results if r.status.value == "installed"],
        "errors": [r.to_dict() for r in results if r.status.value == "error"],
        "ready": all(r.status.value == "installed" for r in results),
    }


@router.post("/quick-setup")
async def quick_setup_endpoint():
    """Setup rápido automático."""
    from ipa_core.services.model_installer import quick_setup

    result = await quick_setup()
    ready = all(
        v in ("installed", "already_installed")
        for k, v in result.items()
        if k in ("aiohttp", "epitran")
    )
    return {
        "components": result,
        "ready": ready,
        "next_steps": []
        if ready
        else [
            "Instalar eSpeak-NG si no está instalado",
            "Instalar Ollama para feedback con LLM",
        ],
    }


# ============ ASR ENGINE MANAGEMENT ============


@router.get("/asr/engines")
async def list_asr_engines():
    """Lista los motores ASR disponibles con salida IPA."""
    from ipa_core.backends.unified_ipa_backend import ASREngine, UnifiedIPABackend

    engines = []
    for engine in ASREngine:
        status = UnifiedIPABackend.check_engine_ready(engine)
        engines.append(
            {
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
            }
        )

    try:
        cfg = loader.load_config()
        backend_params = cfg.backend.params if cfg.backend.params else {}
        current_engine = backend_params.get("engine", "allosaurus")
    except Exception:
        current_engine = "allosaurus"

    return {
        "current": current_engine,
        "engines": engines,
        "recommendation": "allosaurus",
    }


@router.post("/asr/engine/{engine_id}", response_model=None)
async def set_asr_engine(engine_id: str):
    """Cambiar el motor ASR activo."""
    from ipa_core.backends.unified_ipa_backend import ASREngine, UnifiedIPABackend

    try:
        engine = ASREngine(engine_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Engine no válido: {engine_id}",
                "valid_engines": [e.value for e in ASREngine],
            },
        )

    status = UnifiedIPABackend.check_engine_ready(engine)
    if not status["ready"]:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Engine {engine_id} no está listo",
                "missing": status["missing"],
                "install_command": f"pip install {' '.join(status['missing'])}",
            },
        )

    return {
        "success": True,
        "engine": engine_id,
        "message": f"Engine cambiado a {engine_id}. Para hacer el cambio permanente, edita configs/local.yaml",
        "config_example": {
            "backend": {
                "name": "unified_ipa",
                "params": {"engine": engine_id, "device": "cpu"},
            }
        },
    }


@router.post("/asr/install/{engine_id}", response_model=None)
async def install_asr_engine(engine_id: str):
    """Instalar las dependencias para un motor ASR."""
    from ipa_core.backends.unified_ipa_backend import ASREngine
    from ipa_core.services.model_installer import get_installer

    engine_to_models: dict[str, list[str]] = {
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
            },
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
