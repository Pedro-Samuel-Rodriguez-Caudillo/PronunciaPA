"""Health and setup-status endpoints."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ipa_core.config import loader
from ipa_core.errors import NotReadyError
from ipa_core.plugins import registry

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Endpoint de salud con diagnóstico detallado de componentes."""
    from ipa_core.packs.loader import DEFAULT_PACKS_DIR
    from ipa_core.plugins.models import storage

    # Detectar language packs
    try:
        packs = [
            d.name
            for d in DEFAULT_PACKS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
    except Exception:
        packs = []

    # Detectar modelos locales
    try:
        models = storage.scan_models()
    except Exception:
        models = []

    # Diagnóstico de componentes
    components: dict[str, Any] = {}
    cfg = loader.load_config()

    # ASR Backend
    try:
        asr = registry.resolve_asr(cfg.backend.name, cfg.backend.params, strict_mode=True)
        await asr.setup()
        components["asr"] = {
            "name": cfg.backend.name,
            "ready": True,
            "output_type": getattr(asr, "output_type", "unknown"),
        }
        await asr.teardown()
    except (KeyError, NotReadyError) as e:
        components["asr"] = {"name": cfg.backend.name, "ready": False, "error": str(e)}
    except Exception as e:
        components["asr"] = {
            "name": cfg.backend.name,
            "ready": False,
            "error": f"Unexpected error: {str(e)}",
        }

    # TextRef
    try:
        textref = registry.resolve_textref(
            cfg.textref.name, cfg.textref.params, strict_mode=True
        )
        await textref.setup()
        components["textref"] = {"name": cfg.textref.name, "ready": True}
        await textref.teardown()
    except (KeyError, NotReadyError) as e:
        components["textref"] = {"name": cfg.textref.name, "ready": False, "error": str(e)}
    except Exception as e:
        components["textref"] = {
            "name": cfg.textref.name,
            "ready": False,
            "error": f"Unexpected error: {str(e)}",
        }

    # LLM (opcional)
    if cfg.llm and cfg.llm.name != "auto":
        try:
            llm = registry.resolve_llm(cfg.llm.name, cfg.llm.params, strict_mode=True)
            await llm.setup()
            components["llm"] = {"name": cfg.llm.name, "ready": True}
            await llm.teardown()
        except (KeyError, NotReadyError) as e:
            components["llm"] = {"name": cfg.llm.name, "ready": False, "error": str(e)}
        except Exception as e:
            components["llm"] = {
                "name": cfg.llm.name,
                "ready": False,
                "error": f"Unexpected error: {str(e)}",
            }

    # TTS (opcional)
    if cfg.tts and cfg.tts.name != "default":
        try:
            tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params, strict_mode=True)
            await tts.setup()
            components["tts"] = {"name": cfg.tts.name, "ready": True}
            await tts.teardown()
        except (KeyError, NotReadyError) as e:
            components["tts"] = {"name": cfg.tts.name, "ready": False, "error": str(e)}
        except Exception as e:
            components["tts"] = {
                "name": cfg.tts.name,
                "ready": False,
                "error": f"Unexpected error: {str(e)}",
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
