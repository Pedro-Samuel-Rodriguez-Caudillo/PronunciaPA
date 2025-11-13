"""Aplicación HTTP basada en FastAPI."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from ipa_core.errors import KernelError, ValidationError
from ipa_core.services.transcription import TranscriptionService


@lru_cache(maxsize=1)
def _service() -> TranscriptionService:
    return TranscriptionService()


def get_app() -> Any:
    """Construye la app FastAPI y registra rutas."""
    app = FastAPI(title="PronunciaPA", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/pronunciapa/transcribe")
    async def transcribe(
        request: Request,
        audio: Optional[UploadFile] = File(default=None, description="Archivo de audio opcional"),
        lang: Optional[str] = Form(default=None, description="Código de idioma"),
    ) -> dict[str, Any]:
        service = _service()
        try:
            if audio is not None:
                data = await audio.read()
                payload = service.transcribe_bytes(data, filename=audio.filename or "upload.wav", lang=lang)
            else:
                raw = await request.body()
                if not raw:
                    raise ValidationError("El cuerpo del request está vacío")
                filename = request.headers.get("X-Audio-Filename", "stream.wav")
                payload = service.transcribe_bytes(raw, filename=filename, lang=lang)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KernelError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "ipa": payload.ipa,
            "tokens": payload.tokens,
            "lang": payload.lang,
            "audio": payload.audio,
            "meta": payload.meta,
        }

    @app.exception_handler(KernelError)
    async def kernel_error_handler(request: Request, exc: KernelError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    return app
