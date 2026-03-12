"""Health and setup-status endpoints."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ipa_core.audio.ffmpeg import find_ffmpeg_binary
from ipa_core.config import loader
from ipa_core.errors import NotReadyError
from ipa_core.kernel.core import _normalize_llm_name
from ipa_core.plugins import registry
from ipa_server.kernel_provider import peek_kernel

router = APIRouter(tags=["health"])


def _safe_component_ready(name: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"name": name, "ready": True}
    if extra:
        payload.update(extra)
    return payload


def _safe_component_error(name: str, error: Exception | str) -> dict[str, Any]:
    return {"name": name, "ready": False, "error": str(error)}


def _diagnose_asr(cfg) -> dict[str, Any]:
    backend_name = cfg.backend.name
    active_kernel = peek_kernel()
    if active_kernel is not None:
        return _safe_component_ready(
            backend_name,
            extra={"output_type": getattr(active_kernel.asr, "output_type", "unknown"), "source": "kernel_cache"},
        )
    return _safe_component_ready(backend_name, extra={"source": "config_only"})


def _diagnose_textref(cfg) -> dict[str, Any]:
    active_kernel = peek_kernel()
    if active_kernel is not None:
        return _safe_component_ready(cfg.textref.name, extra={"source": "kernel_cache"})
    return _safe_component_ready(cfg.textref.name, extra={"source": "config_only"})


def _diagnose_llm(cfg) -> dict[str, Any]:
    llm_name = cfg.llm.name
    active_kernel = peek_kernel()
    if active_kernel is not None and active_kernel.llm is not None:
        return _safe_component_ready(llm_name, extra={"source": "kernel_cache"})

    normalized = _normalize_llm_name((llm_name or "auto").lower())
    if normalized == "auto":
        return _safe_component_ready(llm_name, extra={"source": "config_auto"})
    return _safe_component_ready(llm_name, extra={"source": "config_only"})


def _diagnose_tts(cfg) -> dict[str, Any]:
    tts_name = cfg.tts.name
    active_kernel = peek_kernel()
    if active_kernel is not None and active_kernel.tts is not None:
        return _safe_component_ready(tts_name, extra={"source": "kernel_cache"})
    return _safe_component_ready(tts_name, extra={"source": "config_only"})


@router.get("/health")
async def health() -> dict[str, Any]:
    """Endpoint de salud ligero y determinista para checks rápidos.

    Evita instanciar plugins pesados o escanear artefactos grandes.
    Los detalles profundos de setup viven en `/api/setup-status`.
    """
    from ipa_core.packs.loader import DEFAULT_PACKS_DIR

    try:
        packs = [
            d.name
            for d in DEFAULT_PACKS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
    except Exception:
        packs = []

    # Diagnóstico de componentes
    components: dict[str, Any] = {}
    cfg = loader.load_config()

    # ASR Backend
    components["asr"] = _diagnose_asr(cfg)

    # TextRef
    components["textref"] = _diagnose_textref(cfg)

    # LLM (opcional)
    if cfg.llm and cfg.llm.name != "auto":
        components["llm"] = _diagnose_llm(cfg)

    # TTS (opcional)
    if cfg.tts and cfg.tts.name != "default":
        components["tts"] = _diagnose_tts(cfg)

    ffmpeg_path = find_ffmpeg_binary()

    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "strict_mode": cfg.strict_mode,
        "components": components,
        "ffmpeg": {"configured": bool(ffmpeg_path), "path": ffmpeg_path},
        "language_packs": packs,
        "local_models": None,
    }


@router.get("/api/setup-status")
async def setup_status() -> Dict[str, Any]:
    """Retorna estado de setup con instrucciones específicas para el OS actual."""
    import platform
    import shutil

    os_name = platform.system()
    cfg = loader.load_config()

    status: dict[str, Any] = {
        "os": os_name,
        "strict_mode": cfg.strict_mode,
        "checks": {},
    }

    # 1. Verificar Allosaurus (obligatorio)
    try:
        import allosaurus

        status["checks"]["allosaurus"] = {
            "installed": True,
            "version": getattr(allosaurus, "__version__", "unknown"),
            "instructions": None,
        }
    except ImportError:
        status["checks"]["allosaurus"] = {
            "installed": False,
            "instructions": {
                "command": "pip install allosaurus",
                "description": "Backend ASR obligatorio para reconocimiento fonético",
            },
        }

    # 2. Verificar eSpeak-NG
    espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
    if not espeak_bin and os_name == "Windows":
        windows_paths = [
            r"C:\\Program Files\\eSpeak NG\\espeak-ng.exe",
            r"C:\\Program Files (x86)\\eSpeak NG\\espeak-ng.exe",
        ]
        for path in windows_paths:
            if Path(path).exists():
                espeak_bin = path
                break

    if espeak_bin:
        status["checks"]["espeak"] = {
            "installed": True,
            "path": espeak_bin,
            "instructions": None,
        }
    else:
        if os_name == "Windows":
            instructions: dict[str, Any] = {
                "url": "https://github.com/espeak-ng/espeak-ng/releases",
                "description": "Descargar e instalar eSpeak NG para Windows",
                "env_var": "PRONUNCIAPA_ESPEAK_BIN=C:\\Program Files\\eSpeak NG\\espeak-ng.exe",
            }
        elif os_name == "Linux":
            instructions = {
                "command": "sudo apt-get install espeak-ng",
                "description": "Instalar eSpeak NG desde repositorios",
            }
        else:
            instructions = {
                "command": "brew install espeak-ng",
                "description": "Instalar eSpeak NG con Homebrew",
            }
        status["checks"]["espeak"] = {"installed": False, "instructions": instructions}

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
                        "instructions": None,
                    }
                else:
                    status["checks"]["ollama"] = {
                        "installed": True,
                        "running": False,
                        "instructions": {
                            "command": "ollama serve",
                            "description": "Iniciar servidor Ollama",
                        },
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
                        "ollama serve",
                    ],
                    "description": "Instalar Ollama para soporte de LLM",
                },
            }

    # 4. Script de descarga de modelos
    status["checks"]["models_script"] = {
        "available": True,
        "instructions": {
            "command": "python scripts/download_models.py",
            "description": "Descargar modelos de Allosaurus y otros componentes",
        },
    }

    return status
