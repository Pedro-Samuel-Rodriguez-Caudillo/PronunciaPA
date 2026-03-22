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

from ipa_core.config import loader
from ipa_core.plugins import registry
from ipa_core.textref.g2p_generator import G2PExerciseGenerator

logger = logging.getLogger(__name__)

_CATALOG_DIR = Path(__file__).parent.parent.parent / "data" / "ipa_catalog"


class CatalogService:
    """Service to handle IPA catalog business logic with low complexity."""

    def __init__(self, catalog_dir: Path = _CATALOG_DIR):
        self.catalog_dir = catalog_dir

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def is_tts_configured(self) -> bool:
        try:
            cfg = loader.load_config()
            name = (cfg.tts.name or "").lower()
            if name in ("", "none"):
                return False
            registry.resolve_tts(name, cfg.tts.params, strict_mode=False)
            return True
        except Exception:
            return False

    def get_sounds_for_language(self, lang: str, category: Optional[str] = None) -> Optional[dict[str, Any]]:
        catalog_file = self.catalog_dir / f"{lang}.yaml"
        if not catalog_file.exists():
            return None
        data = self._load_yaml(catalog_file)
        sounds = data.get("sounds", [])
        if category:
            sounds = [s for s in sounds if category in s.get("tags", [])]
        
        tts_ok = self.is_tts_configured()
        for sound in sounds:
            sound_id = sound.get("id")
            if sound_id and tts_ok:
                sound["audio_url"] = f"/api/ipa-sounds/audio?sound_id={quote(sound_id)}"
                
        return {"language": lang, "total": len(sounds), "sounds": sounds}

    def get_all_languages_sounds(self, category: Optional[str] = None) -> dict[str, Any]:
        all_sounds: dict[str, Any] = {}
        for yaml_file in self.catalog_dir.glob("*.yaml"):
            if yaml_file.name.endswith("_learning.yaml"):
                continue
            lang_code = yaml_file.stem
            lang_data = self.get_sounds_for_language(lang_code, category)
            if lang_data:
                all_sounds[lang_code] = {"total": lang_data["total"], "sounds": lang_data["sounds"]}
        return {"languages": list(all_sounds.keys()), "data": all_sounds}

    def _find_sound_in_data(self, data: dict[str, Any], sound_id: str, full_sound_id: str) -> Optional[dict[str, Any]]:
        for sound in data.get("sounds", []):
            if sound.get("id") in (sound_id, full_sound_id) or sound.get("ipa") == sound_id:
                return sound
        return None

    def _parse_sound_id(self, sound_id: str) -> tuple[str, str]:
        parts = sound_id.split("/", 1)
        if len(parts) != 2:
            raise ValueError("Invalid sound_id format. Expected: lang/ipa (e.g., es/r)")
        return parts[0], parts[1]

    def get_sound_audio_info(self, sound_id: str, example: Optional[str] = None) -> dict[str, Any]:
        lang, ipa = self._parse_sound_id(sound_id)
        data = self._load_yaml(self.catalog_dir / f"{lang}.yaml")
        if not data:
            raise FileNotFoundError(f"Language catalog not found: {lang}")
            
        sound_data = self._find_sound_in_data(data, ipa, sound_id)
        if not sound_data:
            raise KeyError(f"Sound not found: {sound_id}")
            
        if not example:
            example = self._extract_first_example(sound_data)
        if not example:
            raise ValueError("No example text available for this sound")
            
        return {"lang": lang, "ipa": ipa, "example": example}

    def _extract_first_example(self, sound_data: dict[str, Any]) -> Optional[str]:
        for context_data in sound_data.get("contexts", {}).values():
            seeds = context_data.get("seeds", [])
            if seeds and seeds[0].get("text"):
                return seeds[0].get("text")
        return None

    async def generate_audio_file(self, lang: str, text: str) -> str:
        cfg = loader.load_config()
        tts = registry.resolve_tts(cfg.tts.name, cfg.tts.params)
        await tts.setup()
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                output_path = tmp_file.name
            await tts.synthesize(text=text, lang=lang, output_path=output_path)
            return output_path
        finally:
            await tts.teardown()

    def get_learning_content(self, lang: str, sound_id: Optional[str] = None) -> dict[str, Any]:
        learning_data = self._load_yaml(self.catalog_dir / f"{lang}_learning.yaml")
        if not learning_data:
            basic_data = self._load_yaml(self.catalog_dir / f"{lang}.yaml")
            if not basic_data:
                raise FileNotFoundError(f"No content for: {lang}")
            return {"language": lang, "has_learning_content": False, "sounds": basic_data.get("sounds", [])}

        if sound_id:
            sound = self._find_sound_in_data(learning_data, sound_id, sound_id)
            if sound:
                return {"language": lang, "has_learning_content": True, "sound": sound}
            raise KeyError(f"Sound not found: {sound_id}")

        return self._build_full_learning_response(lang, learning_data)

    def _build_full_learning_response(self, lang: str, data: dict[str, Any]) -> dict[str, Any]:
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

    def _resolve_full_sound_id(self, lang: str, sound_id: str) -> str:
        return sound_id if sound_id.startswith(f"{lang}/") else f"{lang}/{sound_id}"

    def get_drills(self, lang: str, sound_id: str, drill_type: Optional[str] = None) -> dict[str, Any]:
        full_sound_id = self._resolve_full_sound_id(lang, sound_id)
        learning_data = self._load_yaml(self.catalog_dir / f"{lang}_learning.yaml")
        basic_data = self._load_yaml(self.catalog_dir / f"{lang}.yaml")
        
        sound_info = self._find_sound_in_data(learning_data, sound_id, full_sound_id)
        drills = sound_info.get("drills", []) if sound_info else []
        
        if not drills:
            sound_info = sound_info or self._find_sound_in_data(basic_data, sound_id, full_sound_id)
            if sound_info:
                drills = self._build_context_drills(sound_info, sound_id)
                
        if not sound_info:
            raise KeyError(f"Sound not found: {sound_id}")
            
        if drill_type:
            drills = [d for d in drills if d.get("type") == drill_type]
            
        self._attach_audio_to_drills(drills, full_sound_id, True)
        return self._build_drills_response(lang, full_sound_id, sound_info, drills)

    def _build_drills_response(self, lang: str, full_id: str, sound_info: dict, drills: list) -> dict[str, Any]:
        return {
            "language": lang,
            "sound_id": full_id,
            "ipa": sound_info.get("ipa"),
            "name": sound_info.get("common_name") or sound_info.get("label"),
            "difficulty": sound_info.get("difficulty", 1),
            "common_errors": sound_info.get("common_errors", []),
            "tips": sound_info.get("tips", []),
            "drills": drills,
            "total_drills": len(drills),
        }

    def _build_context_drills(self, sound_info: dict[str, Any], sound_id: str) -> list[dict[str, Any]]:
        drills: list[dict[str, Any]] = []
        for position, context_data in sound_info.get("contexts", {}).items():
            seeds = context_data.get("seeds", [])
            if seeds:
                drills.append({
                    "type": f"word_{position}",
                    "instruction": f"Practice words with /{sound_id}/ in {position} position",
                    "targets": [s.get("text") for s in seeds if s.get("text")],
                })
        return drills

    def _attach_audio_to_drills(self, drills: list[dict[str, Any]], full_sound_id: str, include_audio: bool, max_audio: int = 5) -> None:
        if not include_audio:
            return
        for drill in drills:
            self._attach_audio_targets(drill, full_sound_id, max_audio)
            self._attach_audio_pairs(drill, full_sound_id, max_audio)

    def _attach_audio_targets(self, drill: dict, full_sound_id: str, max_audio: int):
        targets = drill.get("targets", [])
        if targets:
            drill["targets_with_audio"] = [
                {"text": t, "audio_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(t)}"}
                for t in targets[:max_audio] if t
            ]

    def _attach_audio_pairs(self, drill: dict, full_sound_id: str, max_audio: int):
        pairs = drill.get("pairs", [])
        if pairs:
            drill["pairs_with_audio"] = [
                {
                    "word1": p[0], "word2": p[1],
                    "audio1_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(p[0])}",
                    "audio2_url": f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(p[1])}"
                }
                for p in pairs[:max_audio] if len(p) >= 2
            ]

    def _attach_audio_to_examples(self, examples: list[dict[str, Any]], full_sound_id: str, include_audio: bool) -> None:
        if not include_audio:
            return
        for ex in examples:
            if ex.get("text"):
                ex["audio_url"] = f"/api/ipa-sounds/audio?sound_id={quote(full_sound_id)}&example={quote(ex['text'])}"

    async def get_sound_lesson(self, lang: str, sound_id: str, include_audio: Optional[bool] = None, max_drills: int = 10, generate: bool = True) -> dict[str, Any]:
        if include_audio is None:
            include_audio = self.is_tts_configured()
            
        full_sound_id = self._resolve_full_sound_id(lang, sound_id)
        learning_data = self._load_yaml(self.catalog_dir / f"{lang}_learning.yaml")
        basic_data = self._load_yaml(self.catalog_dir / f"{lang}.yaml")
        
        if not learning_data and not basic_data:
            raise FileNotFoundError(f"Language catalog not found: {lang}")

        sound_info = self._find_sound_in_data(learning_data, sound_id, full_sound_id)
        has_learning = sound_info is not None
        base_sound = self._find_sound_in_data(basic_data, sound_id, full_sound_id)
        sound_info = sound_info or base_sound
        
        if not sound_info:
            raise KeyError(f"Sound not found: {sound_id}")
            
        sound_info = copy.deepcopy(sound_info)
        return await self._build_lesson(lang, full_sound_id, sound_info, base_sound, has_learning, include_audio, max_drills, generate)

    async def _resolve_lesson_drills(self, lang: str, ipa: str, info: dict, base_info: Optional[dict], generate: bool) -> tuple[list, list, bool]:
        drills = info.get("drills", []) or []
        if not drills and base_info:
            drills = self._build_context_drills(base_info, ipa)
            
        generated_drills = False
        minimal_pairs = info.get("minimal_pairs")
        
        if generate and not drills:
            drills, minimal_pairs = await self._generate_drills(lang, ipa, info.get("difficulty", 1), minimal_pairs)
            generated_drills = bool(drills or minimal_pairs)
            
        return drills, minimal_pairs, generated_drills

    async def _build_lesson(self, lang: str, full_id: str, info: dict, base_info: Optional[dict], has_learning: bool, inc_audio: bool, max_drills: int, generate: bool) -> dict[str, Any]:
        ipa = info.get("ipa") or full_id.split("/", 1)[-1]
        
        drills, minimal_pairs, generated = await self._resolve_lesson_drills(lang, ipa, info, base_info, generate)

        if max_drills and len(drills) > max_drills:
            drills = drills[:max_drills]

        self._attach_audio_to_drills(drills, full_id, inc_audio)
        examples = info.get("audio_examples", []) or []
        self._attach_audio_to_examples(examples, full_id, inc_audio)

        return self._format_lesson_response(lang, full_id, ipa, info, drills, minimal_pairs, examples, has_learning, generated)

    async def _generate_drills(self, lang: str, ipa: str, difficulty: int, existing_pairs: Optional[list]) -> tuple[list, list]:
        drills, pairs_list = [], existing_pairs or []
        textref = None
        try:
            cfg = loader.load_config()
            textref = registry.resolve_textref(cfg.textref.name, cfg.textref.params)
            await textref.setup()
            generator = G2PExerciseGenerator(textref=textref, default_lang=lang)
            
            pairs_list = await self._gen_minimal_pairs(generator, lang, ipa, pairs_list)
            drills.extend(await self._gen_practice_drills(generator, lang, ipa, difficulty))
            
            if pairs_list:
                drills.append({
                    "type": "contrast", "instruction": f"Distingue /{ipa}/ de sonidos cercanos",
                    "pairs": [[p[1], p[3]] if isinstance(p[1], str) else p for p in pairs_list]
                })
        except Exception as exc:
            logger.warning("Failed to generate drills for %s: %s", ipa, exc)
        finally:
            if textref:
                try:
                    await textref.teardown()
                except Exception:
                    pass
        return drills, pairs_list

    async def _gen_minimal_pairs(self, gen, lang: str, ipa: str, existing: list) -> list:
        if existing:
            return existing
        pairs = await gen.generate_minimal_pairs(ipa, lang=lang, max_pairs=5)
        return [[p.ipa_a, p.word_a, p.ipa_b, p.word_b] for p in pairs] if pairs else []

    async def _gen_practice_drills(self, gen, lang: str, ipa: str, diff: int) -> list:
        items = await gen.generate_drills([ipa], lang=lang, difficulty=diff)
        targets, hints = [], []
        for item in items:
            if item.text not in targets:
                targets.append(item.text)
            hints.extend([h for h in item.hints if h not in hints])
            
        if targets:
            return [{"type": "word_practice", "instruction": f"Practica palabras con /{ipa}/", "targets": targets, "hints": hints or None}]
        return []

    def _format_lesson_response(self, lang: str, full_id: str, ipa: str, info: dict, drills: list, pairs: list, examples: list, has_learning: bool, generated: bool) -> dict[str, Any]:
        return {
            "language": lang,
            "sound_id": full_id,
            "ipa": ipa,
            "name": info.get("name") or info.get("common_name") or info.get("label"),
            "common_name": info.get("common_name"),
            "difficulty": info.get("difficulty", 1),
            "note": info.get("note"),
            "articulation": info.get("articulation"),
            "visual_guide": info.get("visual_guide"),
            "audio_examples": examples,
            "common_errors": info.get("common_errors", []),
            "tips": info.get("tips", []),
            "minimal_pairs": pairs,
            "drills": drills,
            "total_drills": len(drills),
            "has_learning_content": has_learning,
            "generated_drills": generated,
        }
