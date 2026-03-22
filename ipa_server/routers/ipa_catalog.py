"""IPA catalog, learning content and drill endpoints."""
from __future__ import annotations

import logging
import unicodedata
import re
from typing import Any, Optional
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ipa_core.services.catalog import CatalogService
from ipa_server.http_errors import error_response
from ipa_server.models import SoundLesson

router = APIRouter(prefix="/api", tags=["ipa-catalog"])
logger = logging.getLogger(__name__)

catalog_service = CatalogService()


def _ascii_header_value(value: str) -> str:
    """Encode arbitrary Unicode safely for HTTP headers."""
    return quote(value or "", safe="")


def _safe_filename_part(value: str, *, fallback: str = "audio") -> str:
    """Return an ASCII-safe filename segment."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_text).strip("._-")
    return (cleaned or fallback)[:40]


@router.get("/ipa-sounds", response_model=None)
async def get_ipa_sounds(lang: Optional[str] = None, category: Optional[str] = None):
    if lang:
        res = catalog_service.get_sounds_for_language(lang, category)
        if not res:
            return error_response(404, f"Idioma no encontrado: {lang}", "language_not_found", {"available": ["es", "en"]})
        return res
    return catalog_service.get_all_languages_sounds(category)


def _handle_audio_info_error(e: Exception):
    if isinstance(e, FileNotFoundError):
        return error_response(404, str(e), "language_not_found")
    if isinstance(e, KeyError):
        return error_response(404, str(e), "sound_not_found")
    if isinstance(e, ValueError):
        if "Invalid sound_id" in str(e):
            return error_response(400, str(e), "validation_error")
        return error_response(404, str(e), "example_not_found")
    return error_response(500, str(e), "internal_error")

@router.get("/ipa-sounds/audio")
async def get_ipa_sound_audio(sound_id: str, example: Optional[str] = None):
    try:
        info = catalog_service.get_sound_audio_info(sound_id, example)
    except Exception as e:
        return _handle_audio_info_error(e)

    try:
        output_path = await catalog_service.generate_audio_file(info["lang"], info["example"])
        safe_sound = _safe_filename_part(sound_id.replace("/", "_"), fallback="sound")
        safe_example = _safe_filename_part(info["example"], fallback="example")
        
        return FileResponse(
            path=output_path, media_type="audio/wav", filename=f"{safe_sound}_{safe_example}.wav",
            headers={"X-Example-Text": _ascii_header_value(info["example"]), "X-Sound-IPA": _ascii_header_value(info["ipa"])}
        )
    except Exception as e:
        return error_response(500, "Failed to generate audio", "audio_generation_failed", {"backend_error": str(e), "text": info["example"]})


@router.get("/ipa-learn/{lang}", response_model=None)
async def get_ipa_learning_content(lang: str, sound_id: Optional[str] = None):
    try:
        return catalog_service.get_learning_content(lang, sound_id)
    except FileNotFoundError as e:
        return error_response(404, str(e), "learning_content_not_found")
    except KeyError as e:
        return error_response(404, str(e), "sound_not_found")


@router.get("/ipa-drills/{lang}/{sound_id:path}", response_model=None)
async def get_sound_drills(lang: str, sound_id: str, drill_type: Optional[str] = None):
    try:
        return catalog_service.get_drills(lang, sound_id, drill_type)
    except KeyError as e:
        return error_response(404, str(e), "sound_not_found")


@router.get("/ipa-lesson/{lang}/{sound_id:path}", response_model=SoundLesson)
async def get_sound_lesson(lang: str, sound_id: str, include_audio: Optional[bool] = None, max_drills: int = 10, generate: bool = True):
    try:
        return await catalog_service.get_sound_lesson(lang, sound_id, include_audio, max_drills, generate)
    except FileNotFoundError as e:
        return error_response(404, str(e), "language_not_found")
    except KeyError as e:
        return error_response(404, str(e), "sound_not_found")
