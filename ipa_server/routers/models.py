"""Model installation and ASR engine management endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ipa_core.config import loader
from ipa_server.http_errors import error_response

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
        return error_response(
            status_code=404,
            detail=f"Modelo no encontrado: {model_id}",
            error_type="model_not_found",
        )

    installer = get_installer()
    try:
        result = await installer.install(model_id)
        return {"success": True, "model": result.to_dict()}
    except Exception as e:
        return error_response(
            status_code=500,
            detail="Error instalando modelo",
            error_type="model_install_error",
            extra={"success": False, "backend_error": str(e), "model_id": model_id},
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


def _check_asr_engine_ready(engine_id: str) -> dict[str, Any]:
    missing: list[str] = []
    if engine_id == "allosaurus":
        try:
            import allosaurus.app  # noqa: F401
        except Exception:
            missing.append("allosaurus")
    elif engine_id in {"wav2vec2-ipa", "xlsr-ipa"}:
        try:
            import torch  # noqa: F401
        except Exception:
            missing.append("torch")
        try:
            import transformers  # noqa: F401
        except Exception:
            missing.append("transformers")
    else:
        return {
            "ready": False,
            "missing": ["unknown_engine"],
            "message": f"Engine no válido: {engine_id}",
        }

    return {
        "ready": len(missing) == 0,
        "missing": missing,
        "message": "OK" if not missing else f"Faltan dependencias: {', '.join(missing)}",
    }


@router.get("/asr/engines")
async def list_asr_engines():
    """Lista los motores ASR disponibles con salida IPA."""
    engines_catalog = [
        {
            "id": "allosaurus",
            "name": "Allosaurus (Universal IPA)",
            "description": "ASR universal con 200+ idiomas. Ligero (~500MB), funciona en CPU.",
        },
        {
            "id": "wav2vec2-ipa",
            "name": "Wav2Vec2 Large IPA",
            "description": "Alta precisión fonética. Requiere ~1.2GB y GPU para velocidad óptima.",
        },
        {
            "id": "xlsr-ipa",
            "name": "XLS-R 300M IPA (Multilingüe)",
            "description": "Multilingüe (128 idiomas). Buen balance precisión/velocidad.",
        },
    ]

    engines = []
    for engine in engines_catalog:
        status = _check_asr_engine_ready(engine["id"])
        engines.append(
            {
                "id": engine["id"],
                "name": engine["name"],
                "ready": status["ready"],
                "missing": status["missing"],
                "message": status["message"],
                "description": engine["description"],
            }
        )

    try:
        cfg = loader.load_config()
        if cfg.backend.name == "allosaurus":
            current_engine = "allosaurus"
        elif cfg.backend.name == "wav2vec2":
            current_engine = "wav2vec2-ipa"
        else:
            backend_params = cfg.backend.params if cfg.backend.params else {}
            current_engine = backend_params.get("engine", cfg.backend.name)
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
    valid_engines = ["allosaurus", "wav2vec2-ipa", "xlsr-ipa"]
    if engine_id not in valid_engines:
        return error_response(
            status_code=400,
            detail=f"Engine no valido: {engine_id}",
            error_type="invalid_engine",
            extra={"valid_engines": valid_engines},
        )

    status = _check_asr_engine_ready(engine_id)
    if not status["ready"]:
        return error_response(
            status_code=400,
            detail=f"Engine {engine_id} no esta listo",
            error_type="engine_not_ready",
            extra={
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
                "name": "allosaurus" if engine_id == "allosaurus" else "wav2vec2",
                "params": {"device": "cpu", "lang": "es"},
            }
        },
    }


@router.post("/asr/install/{engine_id}", response_model=None)
async def install_asr_engine(engine_id: str):
    """Instalar las dependencias para un motor ASR."""
    from ipa_core.services.model_installer import get_installer

    engine_to_models: dict[str, list[str]] = {
        "allosaurus": ["allosaurus"],
        "wav2vec2-ipa": ["torch", "transformers", "wav2vec2-ipa"],
        "xlsr-ipa": ["torch", "transformers", "xlsr-ipa"],
    }

    if engine_id not in engine_to_models:
        return error_response(
            status_code=400,
            detail=f"Engine no valido: {engine_id}",
            error_type="invalid_engine",
            extra={"valid_engines": list(engine_to_models.keys())},
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


# ============ TEXTREF BACKEND MANAGEMENT ============


def _check_espeak_available() -> bool:
    import shutil
    return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None


def _check_nltk_cmudict() -> bool:
    import importlib

    try:
        nltk = importlib.import_module("nltk")
        nltk.data.find("corpora/cmudict")
        return True
    except Exception:
        return False


def _check_epitran_available() -> bool:
    try:
        import epitran  # noqa: F401
        return True
    except ImportError:
        return False


@router.get("/textref/backends")
async def list_textref_backends():
    """Lista los backends TextRef disponibles y su estado.

    Cada backend convierte texto en IPA de referencia para la comparación.
    """
    espeak_ok = _check_espeak_available()
    cmudict_ok = _check_nltk_cmudict()
    epitran_ok = _check_epitran_available()

    try:
        cfg = loader.load_config()
        current = cfg.textref.name
    except Exception:
        current = "auto"

    backends = [
        {
            "id": "grapheme",
            "name": "Grapheme (fallback)",
            "description": "Retorna los grafemas del texto como tokens. Sin dependencias externas.",
            "ready": True,
            "languages": ["*"],
            "install": None,
            "notes": "Solo útil para pruebas o idiomas sin soporte fonético.",
        },
        {
            "id": "espeak",
            "name": "eSpeak-NG",
            "description": "Convierte texto a IPA usando reglas fonológicas. Soporta 100+ idiomas.",
            "ready": espeak_ok,
            "languages": ["es", "en", "fr", "de", "it", "pt", "ru", "zh", "ja", "ar", "…"],
            "install": "sudo apt install espeak-ng  # Ubuntu/Debian\nbrew install espeak-ng  # macOS",
            "notes": "Recomendado para uso general.",
        },
        {
            "id": "cmudict",
            "name": "CMU Pronouncing Dictionary",
            "description": "Diccionario fonético para inglés americano (109K entradas). "
                           "OOV → fallback eSpeak.",
            "ready": cmudict_ok,
            "languages": ["en", "en-us", "en-gb", "en-au"],
            "install": "pip install nltk && python -c \"import nltk; nltk.download('cmudict')\"",
            "notes": "Pronunciaciones basadas en inglés americano (GA). "
                     "Para en-GB las palabras OOV usan eSpeak con voz en-gb.",
        },
        {
            "id": "epitran",
            "name": "Epitran",
            "description": "G2P basado en reglas para 30+ idiomas. Alta cobertura morfológica.",
            "ready": epitran_ok,
            "languages": ["es", "en", "fr", "de", "ar", "ru", "zh", "…"],
            "install": "pip install epitran",
            "notes": "Alternativa a eSpeak con distinto enfoque de reglas G2P.",
        },
        {
            "id": "auto",
            "name": "Auto (cascada)",
            "description": "Prueba: eSpeak → Epitran → Grapheme. Usa el primero disponible.",
            "ready": True,
            "languages": ["*"],
            "install": None,
            "notes": "Recomendado cuando no se sabe qué backends están instalados.",
        },
    ]

    ready_count = sum(1 for b in backends if b["ready"])
    return {
        "current": current,
        "backends": backends,
        "summary": {
            "total": len(backends),
            "ready": ready_count,
        },
        "recommendation": "espeak" if espeak_ok else "grapheme",
    }
