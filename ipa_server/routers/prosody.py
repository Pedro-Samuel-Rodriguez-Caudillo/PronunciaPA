"""Prosody analysis endpoint.

Endpoint
--------
POST /v1/prosody
    Upload a WAV file and optionally a list of observed IPA phones.
    Returns prosody metrics: speech rate, pauses, rhythm score, and (if librosa
    is installed) mean F0 and F0 standard deviation.

Optional query parameters
-------------------------
ref_speech_rate : float
    Reference speech rate in phones/second (default 14.0 for Spanish).
extract_f0 : bool
    Whether to attempt F0 extraction via librosa (default true).

Response (JSON)
---------------
{
  "speech_rate_phones_per_sec": 13.5,
  "speech_rate_ratio": 0.96,
  "pause_count": 2,
  "avg_pause_ms": 420.0,
  "max_pause_ms": 650.0,
  "voiced_ms": 1800,
  "total_ms": 2300,
  "speech_ratio": 0.78,
  "rhythm_score": 85.4,
  "f0_mean_hz": 195.4,   // null if librosa not installed
  "f0_std_hz": 22.1,
  "meta": {...}
}
"""
from __future__ import annotations

import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from ipa_core.services.prosody import DEFAULT_REF_SPEECH_RATE, analyze_prosody

logger = logging.getLogger("ipa_server")

router = APIRouter(prefix="/v1/prosody", tags=["prosody"])


@router.post(
    "",
    summary="Analyze prosody/rhythm of a WAV recording",
)
async def post_prosody(
    audio: UploadFile = File(..., description="WAV file (16-bit PCM, mono recommended)"),
    observed_phones: str = Query(
        default="",
        description="Space-separated IPA phones as observed by ASR, e.g. 'p a l a β ɾ a'",
    ),
    ref_speech_rate: float = Query(
        default=DEFAULT_REF_SPEECH_RATE,
        gt=0,
        le=50,
        description="Reference speech rate in phones/second",
    ),
    extract_f0: bool = Query(
        default=True,
        description="Extract F0 via librosa (slower; returns null if librosa absent)",
    ),
):
    """Analyze prosody and rhythm from a WAV file.

    The analysis does **not** require an ASR model — supply ``observed_phones``
    when you already have a transcription, or omit it to skip speed metrics.
    """
    if not audio.filename or not audio.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .wav")

    phones_list = [p for p in observed_phones.split() if p] if observed_phones else None

    # Save the uploaded file to a temp location
    suffix = ".wav"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        os.close(tmp_fd)
        content = await audio.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        metrics = analyze_prosody(
            tmp_path,
            observed_phones=phones_list,
            ref_speech_rate=ref_speech_rate,
            extract_f0=extract_f0,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en análisis de prosodia: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}") from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    from dataclasses import asdict

    return JSONResponse(content=asdict(metrics))
