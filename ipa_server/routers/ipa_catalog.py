"""IPA catalog, learning content and drill endpoints."""
from __future__ import annotations

import copy
import logging
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import yaml
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from ipa_core.config import loader
from ipa_core.plugins import registry
from ipa_core.textref.g2p_generator import G2PExerciseGenerator
from ipa_server.models import SoundLesson

router = APIRouter(prefix="/api", tags=["ipa-catalog"])

_CATALOG_DIR = Path(__file__).parent.parent.parent / "data" / "ipa_catalog"
logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _ascii_header_value(value: str) -> str:
    """Encode arbitrary Unicode safely for HTTP headers."""
    return quote(value or "", safe="")


def _safe_filename_part(value: str, *, fallback: str = "audio") -> str:
    """Return an ASCII-safe filename segment."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_text).strip("._-")
    return (cleaned or fallback)[:40]


def _resolve_full_sound_id(lang: str, sound_id: str) -> str:
    if sound_id.startswith(f"{lang}/"):
        return sound_id
    return f"{lang}/{sound_id}"


def _find_sound(data: dict[str, Any], *, sound_id: str, full_sound_id: str) -> Optional[dict[str, Any]]:
    for sound in data.get("sounds", []):
        if sound.get("id") == full_sound_id or sound.get("id") == sound_id:
            return sound
        if sound.get("ipa") == sound_id:
            return sound
    return None


def _build_context_drills(sound_info: dict[str, Any], *, sound_id: str) -> list[dict[str, Any]]:
    drills: list[dict[str, Any]] = []
    contexts = sound_info.get("contexts", {}) or {}
    for position, context_data in contexts.items():
        seeds = context_data.get("seeds", [])
        if seeds:
            drills.append(
                {
                    "type": f"word_{position}",
                    "instruction": f"Practice words with /{sound_id}/ in {position} position",
                    "targets": [s.get("text") for s in seeds if s.get("text")],
                }
            )
    return drills


def _attach_audio_to_drills(
    drills: list[dict[str, Any]],
    *,
    full_sound_id: str,
    include_audio: bool,
    max_audio: int = 5,
) -> None:
    if not include_audio:
        return
    for drill in drills:
        targets = drill.get("targets", [])
        pairs = drill.get("pairs", [])
        if targets:
            drill["targets_with_audio"] = [
                {
                    "text": t,
                    "audio_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(t)}",
                }
                for t in targets[:max_audio]
                if t
            ]
        if pairs:
            drill["pairs_with_audio"] = [
                {
                    "word1": p[0],
                    "word2": p[1],
                    "audio1_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(p[0])}",
                    "audio2_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(p[1])}",
                }
                for p in pairs[:max_audio]
                if len(p) >= 2
            ]


def _attach_audio_to_examples(
    examples: list[dict[str, Any]],
    *,
    full_sound_id: str,
    include_audio: bool,
) -> None:
    if not include_audio:
        return
    for ex in examples:
        text = ex.get("text")
        if text:
            ex["audio_url"] = f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(text)}"


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
            safe_sound = _safe_filename_part(sound_id.replace("/", "_"), fallback="sound")
            safe_example = _safe_filename_part(example, fallback="example")
            return FileResponse(
                path=output_path,
                media_type="audio/wav",
                filename=f"{safe_sound}_{safe_example}.wav",
                headers={
                    "X-Example-Text": _ascii_header_value(example),
                    "X-Sound-IPA": _ascii_header_value(ipa),
                },
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
                    "audio_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(t)}",
                }
                for t in targets[:5]
            ]
        if pairs:
            drill["pairs_with_audio"] = [
                {
                    "word1": p[0],
                    "word2": p[1],
                    "audio1_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(p[0])}",
                    "audio2_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(p[1])}",
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


@router.get("/ipa-lesson/{lang}/{sound_id:path}", response_model=SoundLesson)
async def get_sound_lesson(
    lang: str,
    sound_id: str,
    include_audio: bool = True,
    max_drills: int = 10,
    generate: bool = True,
):
    """Retorna una lección completa para un sonido IPA."""
    learning_file = _CATALOG_DIR / f"{lang}_learning.yaml"
    basic_file = _CATALOG_DIR / f"{lang}.yaml"
    full_sound_id = _resolve_full_sound_id(lang, sound_id)

    learning_data: Optional[dict[str, Any]] = None
    basic_data: Optional[dict[str, Any]] = None
    if learning_file.exists():
        learning_data = _load_yaml(learning_file)
    if basic_file.exists():
        basic_data = _load_yaml(basic_file)

    if not learning_data and not basic_data:
        return JSONResponse(
            status_code=404,
            content={"error": f"Language catalog not found: {lang}"},
        )

    sound_info = None
    sound_from_learning = False
    if learning_data:
        sound_info = _find_sound(learning_data, sound_id=sound_id, full_sound_id=full_sound_id)
        sound_from_learning = sound_info is not None
    base_sound_info = None
    if basic_data:
        base_sound_info = _find_sound(basic_data, sound_id=sound_id, full_sound_id=full_sound_id)
        if sound_info is None:
            sound_info = base_sound_info

    if not sound_info:
        return JSONResponse(
            status_code=404, content={"error": f"Sound not found: {sound_id}"}
        )

    sound_info = copy.deepcopy(sound_info)
    has_learning_content = sound_from_learning
    ipa = sound_info.get("ipa") or full_sound_id.split("/", 1)[-1]
    name = sound_info.get("common_name") or sound_info.get("label") or sound_info.get("name")
    difficulty = sound_info.get("difficulty", 1)

    drills: list[dict[str, Any]] = sound_info.get("drills", []) or []
    if not drills and base_sound_info:
        drills = _build_context_drills(base_sound_info, sound_id=ipa)

    generated_drills = False
    minimal_pairs = sound_info.get("minimal_pairs")

    if generate and not drills:
        textref = None
        try:
            cfg = loader.load_config()
            textref = registry.resolve_textref(cfg.textref.name, cfg.textref.params)
            await textref.setup()
            generator = G2PExerciseGenerator(textref=textref, default_lang=lang)

            pairs = await generator.generate_minimal_pairs(ipa, lang=lang, max_pairs=5)
            if pairs and not minimal_pairs:
                minimal_pairs = [[p.ipa_a, p.word_a, p.ipa_b, p.word_b] for p in pairs]

            items = await generator.generate_drills([ipa], lang=lang, difficulty=difficulty)
            targets = []
            hints: list[str] = []
            for item in items:
                if item.text not in targets:
                    targets.append(item.text)
                for hint in item.hints:
                    if hint not in hints:
                        hints.append(hint)

            if targets:
                drills.append(
                    {
                        "type": "word_practice",
                        "instruction": f"Practica palabras con /{ipa}/",
                        "targets": targets[:max_drills],
                        "hints": hints or None,
                    }
                )

            if pairs:
                drills.append(
                    {
                        "type": "contrast",
                        "instruction": f"Distingue /{ipa}/ de sonidos cercanos",
                        "pairs": [[p.word_a, p.word_b] for p in pairs],
                    }
                )

            generated_drills = bool(drills or minimal_pairs)
        except Exception as exc:
            logger.warning("Failed to generate drills for %s: %s", full_sound_id, exc)
        finally:
            try:
                if textref is not None:
                    await textref.teardown()
            except Exception:
                pass

    if max_drills and len(drills) > max_drills:
        drills = drills[:max_drills]

    _attach_audio_to_drills(drills, full_sound_id=full_sound_id, include_audio=include_audio)

    audio_examples = sound_info.get("audio_examples", []) or []
    if audio_examples:
        _attach_audio_to_examples(audio_examples, full_sound_id=full_sound_id, include_audio=include_audio)

    return {
        "language": lang,
        "sound_id": full_sound_id,
        "ipa": ipa,
        "name": sound_info.get("name") or name,
        "common_name": sound_info.get("common_name"),
        "difficulty": difficulty,
        "note": sound_info.get("note"),
        "articulation": sound_info.get("articulation"),
        "visual_guide": sound_info.get("visual_guide"),
        "audio_examples": audio_examples,
        "common_errors": sound_info.get("common_errors", []),
        "tips": sound_info.get("tips", []),
        "minimal_pairs": minimal_pairs,
        "drills": drills,
        "total_drills": len(drills),
        "has_learning_content": has_learning_content,
        "generated_drills": generated_drills,
    }
