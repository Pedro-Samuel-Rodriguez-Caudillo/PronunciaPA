"""TTS (text-to-speech) endpoints."""
from __future__ import annotations

import tempfile
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse

from ipa_core.config import loader
from ipa_core.errors import NotReadyError
from ipa_core.plugins import registry

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/speak")
async def tts_speak(
    text: str = Query(..., description="Texto a sintetizar"),
    lang: str = Query("es", description="Código de idioma (es, en, etc.)"),
    voice: Optional[str] = Query(None, description="Voz específica (opcional)"),
):
    """Sintetiza texto a audio usando TTS (eSpeak-NG por defecto)."""
    if not text or not text.strip():
        return JSONResponse(
            status_code=400, content={"error": "El texto no puede estar vacío"}
        )

    try:
        cfg = loader.load_config()
        tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params)
        await tts.setup()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            result = await tts.synthesize(
                text=text.strip(), lang=lang, voice=voice, output_path=output_path
            )
            return FileResponse(
                path=output_path,
                media_type="audio/wav",
                filename=f"tts_{lang}_{text[:20].replace(' ', '_')}.wav",
                headers={
                    "X-TTS-Text": text[:100],
                    "X-TTS-Lang": lang,
                    "X-TTS-Backend": result.get("meta", {}).get("backend", "unknown"),
                },
            )
        finally:
            await tts.teardown()

    except NotReadyError as e:
        return JSONResponse(
            status_code=503,
            content={
                "error": "TTS no disponible",
                "detail": str(e),
                "hint": "Instala eSpeak-NG: https://github.com/espeak-ng/espeak-ng/releases",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error generando audio: {str(e)}", "text": text[:100]},
        )


@router.get("/status")
async def tts_status():
    """Verifica el estado del sistema TTS."""
    try:
        cfg = loader.load_config()
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
            "hint": "Instala eSpeak-NG: https://github.com/espeak-ng/espeak-ng/releases",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
