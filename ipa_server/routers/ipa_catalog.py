"""IPA catalog, learning content and drill endpoints."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import yaml
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from ipa_core.config import loader
from ipa_core.plugins import registry

router = APIRouter(prefix="/api", tags=["ipa-catalog"])

_CATALOG_DIR = Path(__file__).parent.parent.parent / "data" / "ipa_catalog"


@router.get("/ipa-sounds", response_model=None)
async def get_ipa_sounds(
    lang: Optional[str] = None,
    category: Optional[str] = None,
):
    """Retorna el catálogo de sonidos IPA por idioma."""
    if lang:
        catalog_file = _CATALOG_DIR / f"{lang}.yaml"
        if not catalog_file.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Idioma no encontrado: {lang}", "available": ["es", "en"]},
            )

        with open(catalog_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sounds = data.get("sounds", [])
        if category:
            sounds = [s for s in sounds if category in s.get("tags", [])]

        for sound in sounds:
            sound_id = sound.get("id")
            if sound_id:
                sound["audio_url"] = f"/api/ipa-sounds/audio?sound_id={quote(sound_id)}"

        return {"language": lang, "total": len(sounds), "sounds": sounds}

    # Todos los idiomas
    all_sounds: dict[str, Any] = {}
    for yaml_file in _CATALOG_DIR.glob("*.yaml"):
        lang_code = yaml_file.stem
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sounds = data.get("sounds", [])
        if category:
            sounds = [s for s in sounds if category in s.get("tags", [])]
        all_sounds[lang_code] = {"total": len(sounds), "sounds": sounds}

    return {"languages": list(all_sounds.keys()), "data": all_sounds}


@router.get("/ipa-sounds/audio")
async def get_ipa_sound_audio(
    sound_id: str,
    example: Optional[str] = None,
):
    """Genera audio TTS para un sonido IPA específico."""
    parts = sound_id.split("/", 1)
    if len(parts) != 2:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid sound_id format. Expected: lang/ipa (e.g., es/r)"},
        )

    lang, ipa = parts
    catalog_file = _CATALOG_DIR / f"{lang}.yaml"
    if not catalog_file.exists():
        return JSONResponse(
            status_code=404, content={"error": f"Language catalog not found: {lang}"}
        )

    with open(catalog_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sound_data = None
    for sound in data.get("sounds", []):
        if sound.get("id") == sound_id or sound.get("ipa") == ipa:
            sound_data = sound
            break

    if not sound_data:
        return JSONResponse(
            status_code=404, content={"error": f"Sound not found: {sound_id}"}
        )

    if not example:
        contexts = sound_data.get("contexts", {})
        for context_data in contexts.values():
            seeds = context_data.get("seeds", [])
            if seeds:
                example = seeds[0].get("text")
                break
        if not example:
            return JSONResponse(
                status_code=404,
                content={"error": "No example text available for this sound"},
            )

    try:
        cfg = loader.load_config()
        tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params)
        await tts.setup()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            await tts.synthesize(text=example, lang=lang, output_path=output_path)
            return FileResponse(
                path=output_path,
                media_type="audio/wav",
                filename=f"{sound_id.replace('/', '_')}_{example[:20]}.wav",
                headers={"X-Example-Text": example, "X-Sound-IPA": ipa},
            )
        finally:
            await tts.teardown()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to generate audio: {str(e)}", "text": example},
        )


@router.get("/ipa-learn/{lang}", response_model=None)
async def get_ipa_learning_content(
    lang: str,
    sound_id: Optional[str] = None,
):
    """Retorna contenido educativo para aprender IPA."""
    learning_file = _CATALOG_DIR / f"{lang}_learning.yaml"

    if not learning_file.exists():
        basic_file = _CATALOG_DIR / f"{lang}.yaml"
        if not basic_file.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"No learning content for: {lang}"},
            )
        with open(basic_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {
            "language": lang,
            "has_learning_content": False,
            "sounds": data.get("sounds", []),
        }

    with open(learning_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if sound_id:
        for sound in data.get("sounds", []):
            if sound.get("id") == sound_id:
                return {"language": lang, "has_learning_content": True, "sound": sound}
        return JSONResponse(
            status_code=404, content={"error": f"Sound not found: {sound_id}"}
        )

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


@router.get("/ipa-drills/{lang}/{sound_id:path}", response_model=None)
async def get_sound_drills(
    lang: str,
    sound_id: str,
    drill_type: Optional[str] = None,
):
    """Retorna ejercicios de práctica para un sonido específico."""
    learning_file = _CATALOG_DIR / f"{lang}_learning.yaml"
    basic_file = _CATALOG_DIR / f"{lang}.yaml"
    full_sound_id = f"{lang}/{sound_id}"
    drills: list[dict[str, Any]] = []
    sound_info = None

    if learning_file.exists():
        with open(learning_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for sound in data.get("sounds", []):
            if sound.get("id") == full_sound_id or sound.get("ipa") == sound_id:
                sound_info = sound
                drills = sound.get("drills", [])
                break

    if not drills and basic_file.exists():
        with open(basic_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for sound in data.get("sounds", []):
            if sound.get("id") == full_sound_id or sound.get("ipa") == sound_id:
                sound_info = sound
                contexts = sound.get("contexts", {})
                for position, context_data in contexts.items():
                    seeds = context_data.get("seeds", [])
                    if seeds:
                        drills.append(
                            {
                                "type": f"word_{position}",
                                "instruction": f"Practice words with /{sound_id}/ in {position} position",
                                "targets": [s.get("text") for s in seeds],
                            }
                        )
                break

    if not sound_info:
        return JSONResponse(
            status_code=404, content={"error": f"Sound not found: {sound_id}"}
        )

    if drill_type:
        drills = [d for d in drills if d.get("type") == drill_type]

    for drill in drills:
        targets = drill.get("targets", [])
        pairs = drill.get("pairs", [])
        if targets:
            drill["targets_with_audio"] = [
                {
                    "text": t,
                    "audio_url": f"/api/ipa-sounds/audio?sound_id={full_sound_id}&example={t}",
                }
                for t in targets[:5]
            ]
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
