"""Audio recording endpoint.

Exposes microphone capture (fixed-duration or VAD auto-stop) over HTTP so that
any client—including the Flutter app—can trigger a recording on the *server*
side and receive back the WAV file; or use it as a helper when the host machine
has a microphone attached.

Endpoints
---------
POST /v1/record
    Record a fixed number of seconds from the default microphone.

POST /v1/record/vad
    Record with VAD auto-stop (up to max_seconds).

Both endpoints return:
- 200 + audio/wav on success
- 503 if sounddevice/numpy are not installed
- 400 for invalid parameters
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from ipa_core.errors import ValidationError

logger = logging.getLogger("ipa_server")

router = APIRouter(prefix="/v1/record", tags=["record"])


@router.post(
    "",
    summary="Record fixed-duration audio from microphone",
    response_class=FileResponse,
)
async def record_fixed(
    seconds: float = Query(3.0, gt=0, le=60, description="Duration in seconds (1–60)"),
    sample_rate: int = Query(16000, description="Sample rate in Hz"),
    channels: int = Query(1, ge=1, le=2, description="Number of channels"),
):
    """Record a fixed number of seconds from the server-side microphone.

    Returns the captured PCM as a WAV file (audio/wav).
    """
    try:
        from ipa_core.audio.microphone import record
    except ImportError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Microphone capture not available",
                "detail": str(exc),
                "hint": "Install sounddevice and numpy: pip install sounddevice numpy",
            },
        )

    try:
        path, meta = record(seconds, sample_rate=sample_rate, channels=channels)
    except ValidationError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Error recording audio: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "error": "Recording failed",
                "detail": str(exc),
                "hint": "Make sure a microphone is connected and accessible.",
            },
        )

    return FileResponse(
        path=path,
        media_type="audio/wav",
        filename="recording.wav",
        headers={
            "X-Sample-Rate": str(meta["sample_rate"]),
            "X-Channels": str(meta["channels"]),
            "X-Duration-Seconds": str(meta["duration"]),
        },
        background=BackgroundTask(_unlink, path),
    )


@router.post(
    "/vad",
    summary="Record with VAD auto-stop",
    response_class=FileResponse,
)
async def record_vad(
    max_seconds: float = Query(10.0, gt=0, le=120, description="Max duration in seconds"),
    sample_rate: int = Query(16000, description="Sample rate in Hz"),
    channels: int = Query(1, ge=1, le=2),
    silence_timeout_ms: int = Query(1500, ge=200, le=5000, description="Silence timeout (ms) after speech"),
    energy_threshold: float = Query(0.01, gt=0, lt=1.0, description="Energy threshold for VAD"),
):
    """Record from microphone until silence is detected after speech.

    Stops automatically when ``silence_timeout_ms`` of silence is detected
    after at least a minimum amount of speech, or when ``max_seconds`` is
    reached.  Returns a WAV file.
    """
    try:
        from ipa_core.audio.microphone import record_with_vad
    except ImportError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Microphone capture not available",
                "detail": str(exc),
                "hint": "Install sounddevice and numpy: pip install sounddevice numpy",
            },
        )

    try:
        path, meta = record_with_vad(
            max_seconds,
            sample_rate=sample_rate,
            channels=channels,
            silence_timeout_ms=silence_timeout_ms,
            energy_threshold=energy_threshold,
        )
    except ValidationError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Error during VAD recording: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "error": "VAD recording failed",
                "detail": str(exc),
                "hint": "Make sure a microphone is connected and accessible.",
            },
        )

    return FileResponse(
        path=path,
        media_type="audio/wav",
        filename="recording_vad.wav",
        headers={
            "X-Sample-Rate": str(meta.get("sample_rate", sample_rate)),
            "X-Channels": str(meta.get("channels", channels)),
            "X-Duration-Seconds": str(meta.get("duration", "")),
            "X-Speech-Detected": str(meta.get("speech_detected", True)).lower(),
        },
        background=BackgroundTask(_unlink, path),
    )


# ── Helper ─────────────────────────────────────────────────────────────────────

def _unlink(path: str) -> None:
    """Delete a temp file silently."""
    try:
        os.unlink(path)
    except OSError:
        pass
