from __future__ import annotations
import asyncio
import json
import random
import re
import unicodedata
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Tuple
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from ipa_core.audio.files import ensure_wav
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.kernel.core import create_kernel
from ipa_core.ipa_catalog import normalize_lang

console = Console()

class CatalogOutput(str, Enum):
    human = "human"
    json = "json"

_IPA_SCHEMA_VERSION = "1.0.0"
_COMPARE_MODES = ["casual", "objective", "phonetic"]
_EVAL_LEVELS = ["phonemic", "phonetic"]
_FEEDBACK_LEVELS = ["casual", "precise"]

def _stdout_supports_unicode() -> bool:
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() == "utf-8":
        return True
    return False

def _emit_json(data: dict) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))

def _read_json_source(source: str) -> dict:
    if source.startswith("{"):
        return json.loads(source)
    with open(source, "r", encoding="utf-8") as f:
        return json.load(f)

def _safe_print(text: str, style: str = "") -> None:
    try:
        console.print(text, style=style)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))

def _get_kernel(model_pack: Optional[str] = None, llm_name: Optional[str] = None) -> Kernel:
    from ipa_core.config.overrides import apply_overrides
    if model_pack:
        apply_overrides({"model_pack": model_pack})
    if llm_name:
        apply_overrides({"llm": {"name": llm_name}})
    return create_kernel()

def _exit_code_for_error(exc: Exception) -> int:
    from ipa_core.errors import FileNotFound, UnsupportedFormat, ValidationError
    if isinstance(exc, (FileNotFound, FileNotFoundError)):
        return 44  # No encontrado
    if isinstance(exc, (UnsupportedFormat, ValueError)):
        return 40  # Bad request
    if isinstance(exc, ValidationError):
        return 42  # Unprocessable
    return 1

def _normalize_context(ctx: Optional[str]) -> str:
    if not ctx:
        return "initial"
    mapping = {
        "i": "initial", "m": "medial", "f": "final",
        "ini": "initial", "med": "medial", "fin": "final",
        "v": "vowel-context", "vowel": "vowel-context",
    }
    return mapping.get(ctx.lower(), ctx.lower())

def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)

def _normalize_sound(sound: str) -> str:
    return sound.strip("/[] ")

def _position_label(pos: str) -> str:
    labels = {"initial": "Inicio", "medial": "Medio", "final": "Final", "vowel-context": "Intervocálica"}
    return labels.get(pos, pos.capitalize())

def _is_vowel(phone: str) -> bool:
    return phone.lower() in "aeiouɑɛɪɔʊʌə"

def _filter_context_tokens(tokens: List[str]) -> List[str]:
    return [t for t in tokens if t and t not in " ._"]

def _match_context(target_ipa: str, sound: str, context: str, before: Optional[str] = None, after: Optional[str] = None) -> bool:
    tokens = _filter_context_tokens(list(target_ipa))
    try:
        idx = tokens.index(sound)
    except ValueError:
        return False
    
    return _check_pos_match(tokens, idx, context, before, after)

def _check_pos_match(tokens: List[str], idx: int, context: str, before: Optional[str], after: Optional[str]) -> bool:
    if context == "initial":
        return idx == 0
    if context == "final":
        return idx == len(tokens) - 1
    if context == "medial":
        return 0 < idx < len(tokens) - 1
    if context == "vowel-context":
        return _check_vowel_context(tokens, idx, before, after)
    return True

def _check_vowel_context(tokens: List[str], idx: int, before: Optional[str], after: Optional[str]) -> bool:
    if idx == 0 or idx == len(tokens) - 1:
        return False
    
    if not (_is_vowel(tokens[idx-1]) and _is_vowel(tokens[idx+1])):
        return False
        
    return _check_vowel_neighbors(tokens, idx, before, after)

def _check_vowel_neighbors(tokens: List[str], idx: int, before: Optional[str], after: Optional[str]) -> bool:
    if before and tokens[idx-1] != before:
        return False
    if after and tokens[idx+1] != after:
        return False
    return True

def _pick_default_context(sound_entry: dict) -> str:
    contexts = sound_entry.get("contexts", {})
    for c in ["medial", "initial", "final", "vowel-context"]:
        if c in contexts:
            return c
    return list(contexts.keys())[0] if contexts else "initial"

def _resolve_feedback_level(requested: Optional[str], eval_level: str) -> str:
    if requested:
        return requested
    return "precise" if eval_level == "phonetic" else "casual"

def _build_confidence(mode: str, pack_used: bool) -> tuple[float, list[str]]:
    warnings = []
    if mode == "phonetic" and not pack_used:
        warnings.append("Modo phonetic sin Language Pack: resultados pueden ser inconsistentes.")
        return 0.4, warnings
    if mode == "objective":
        return 0.85, warnings
    return 0.7, warnings

def _sound_payload(entry: dict) -> dict:
    return {"id": entry.get("id"), "ipa": entry.get("ipa"), "name": entry.get("common_name")}

def _prompt_lang(lang: Optional[str], non_interactive: bool = False) -> str:
    if lang: return normalize_lang(lang)
    if non_interactive: return "es"
    return normalize_lang(typer.prompt("Idioma (es/en)", default="es"))

def _prompt_sound(sound: Optional[str], catalog: dict, non_interactive: bool = False) -> str:
    if sound: return sound
    if non_interactive: return "r"
    return typer.prompt("Sonido IPA o alias (ej: r, ch, ye)")

def _prompt_context(ctx: Optional[str], entry: dict, non_interactive: bool = False) -> str:
    if ctx: return ctx
    if non_interactive: return _pick_default_context(entry)
    available = list(entry.get("contexts", {}).keys())
    if not available: return "initial"
    print(f"Contextos disponibles: {', '.join(available)}")
    return typer.prompt("Contexto", default=available[0])

def _prompt_count(count: int, non_interactive: bool = False) -> int:
    if non_interactive: return count
    return int(typer.prompt("Número de ejemplos", default=str(count)))

def _build_request_payload(**kwargs) -> dict:
    return {k: v for k, v in kwargs.items() if v is not None}

def _build_meta(kernel: Kernel) -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "kernel_version": "1.0.0",
        "model_pack": kernel.model_pack.id if kernel.model_pack else None,
    }

def _print_feedback_payload(payload: dict) -> None:
    fb = payload.get("feedback", {})
    if fb.get("overall"):
        _safe_print(f"\n[bold green]Feedback:[/bold green] {fb['overall']}")
    if fb.get("tips"):
        for tip in fb["tips"]:
            _safe_print(f"• {tip}")

def _print_feedback(feedback: Any) -> None:
    if not feedback:
        return
    if isinstance(feedback, list):
        for f in feedback:
            _safe_print(f"• {f}")
    elif isinstance(feedback, dict):
        _print_feedback_payload({"feedback": feedback})
    else:
        _safe_print(str(feedback))

def _print_compare_table(res: dict) -> None:
    table = Table(title="Comparación")
    table.add_column("Ref")
    table.add_column("Hyp")
    table.add_column("Op")
    for op in res.get("ops", []):
        table.add_row(op.get("ref", ""), op.get("hyp", ""), op.get("op", ""))
    console.print(table)

def _print_accent_features(features: dict) -> None:
    table = Table(title="Características de Acento")
    table.add_column("Rasgo")
    table.add_column("Valor")
    for k, v in features.items():
        table.add_row(k, str(v))
    console.print(table)

def _print_accent_ranking(ranking: list) -> None:
    table = Table(title="Ranking de Acentos/Regiones")
    table.add_column("Posición", justify="right")
    table.add_column("Región")
    table.add_column("Distancia", justify="right")
    for i, r in enumerate(ranking, start=1):
        table.add_row(str(i), r.get("region", "unknown"), f"{r.get('distance', 0.0):.4f}")
    console.print(table)
