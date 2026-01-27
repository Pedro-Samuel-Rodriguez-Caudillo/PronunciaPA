"""CLI para interactuar con PronunciaPA.

Este módulo define los comandos de línea de comandos para transcripción
y comparación fonética.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Optional
from enum import Enum
import json
import random
import re
import sys
import unicodedata
import typer
from rich.console import Console
from rich.table import Table
from ipa_core.analysis import accent as accent_analysis
from ipa_core.audio.files import ensure_wav, cleanup_temp
from ipa_core.audio.microphone import record
from ipa_core.backends.audio_io import to_audio_input, wav_duration
from ipa_core.config import loader
from ipa_core.config.overrides import apply_overrides
from ipa_core.errors import FileNotFound, NotReadyError, UnsupportedFormat, ValidationError
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.pipeline.transcribe import transcribe as transcribe_pipeline
from ipa_core.services.comparison import ComparisonService
from ipa_core.services.feedback import FeedbackService
from ipa_core.services.feedback_store import FeedbackStore
from ipa_core.services.error_report import build_enriched_error_report
from ipa_core.services.fallback import generate_fallback_feedback
from ipa_core.services.transcription import TranscriptionService
from ipa_core.llm.utils import extract_json_object, validate_json_schema
from ipa_core.types import AudioInput
from ipa_core.ipa_catalog import load_catalog, list_sounds, normalize_lang, resolve_sound_entry
from ipa_core.plugins.models import storage
from ipa_core.plugins.model_manager import ModelManager
from ipa_core.testing.benchmark import DatasetLoader, MetricsCalculator
import time
from pathlib import Path

app = typer.Typer(help="PronunciaPA: Reconocimiento y evaluación fonética")
config_app = typer.Typer(help="Gestión de configuración")
plugin_app = typer.Typer(help="Gestión de plugins")

app.add_typer(config_app, name="config")
app.add_typer(plugin_app, name="plugin")

model_app = typer.Typer(help="Gestión de modelos locales (ONNX)")
app.add_typer(model_app, name="models")

ipa_app = typer.Typer(help="Explorador y práctica de sonidos IPA")
app.add_typer(ipa_app, name="ipa")


@app.command()
def health(
    config: Optional[Path] = typer.Option(None, "--config", help="Ruta al archivo de configuración"),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON"),
):
    """🏥 Verificar estado del sistema y componentes."""
    from rich.panel import Panel
    from rich import box
    
    console_local = Console()
    
    def check_config():
        try:
            cfg = loader.load_config(str(config) if config else None)
            return ("✓", "green", f"v{cfg.version}")
        except Exception as e:
            return ("✗", "red", str(e)[:40])
    
    def check_plugins():
        try:
            from ipa_core.plugins import registry
            return ("✓", "green", "Cargados")
        except Exception:
            return ("✗", "red", "Error")
    
    def check_language_packs():
        try:
            from ipa_core.packs.loader import DEFAULT_PACKS_DIR
            packs = [d.name for d in DEFAULT_PACKS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
            return ("✓", "green", ", ".join(packs[:3]) if packs else "Ninguno")
        except Exception:
            return ("⚠", "yellow", "N/A")
    
    def check_models():
        try:
            models = storage.scan_models()
            if models:
                return ("✓", "green", f"{len(models)} instalados")
            return ("⚠", "yellow", "Sin modelos")
        except Exception:
            return ("✗", "red", "Error")
    
    health_items = [
        ("Config", check_config),
        ("Plugins", check_plugins),
        ("Lang Packs", check_language_packs),
        ("Models", check_models),
    ]
    
    all_ok = True
    results = []
    
    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("", width=3)
    table.add_column("", width=12)
    table.add_column("")
    
    for name, check_fn in health_items:
        icon, color, detail = check_fn()
        results.append({"component": name, "ok": icon == "✓", "detail": detail})
        if icon != "✓":
            all_ok = False
        table.add_row(f"[{color}]{icon}[/{color}]", name, f"[dim]{detail}[/dim]")
    
    if json_output:
        _emit_json({"healthy": all_ok, "components": results})
        return
    
    status = "[green]✓ OK[/green]" if all_ok else "[yellow]⚠ Revisar[/yellow]"
    console_local.print()
    console_local.print(Panel(table, title="[bold]🏥 Health Check[/bold]", subtitle=status, border_style="blue" if all_ok else "yellow"))
    console_local.print()


@model_app.command("list")
def models_list():
    """Lista los modelos instalados localmente."""
    models = storage.scan_models()
    if not models:
        console.print("No se encontraron modelos locales.", style="yellow")
        return

    table = Table(title="Modelos Locales")
    table.add_column("Nombre", style="cyan")
    table.add_column("Ruta", style="green")
    
    base_dir = storage.get_models_dir()
    for model in models:
        table.add_row(model, str(base_dir / model))
        
    console.print(table)


@model_app.command("download")
def models_download(
    url: str = typer.Argument(..., help="URL de descarga"),
    name: str = typer.Argument(..., help="Nombre local para el modelo"),
    sha256: Optional[str] = typer.Option(None, "--sha256", help="Hash SHA256 esperado"),
):
    """Descarga e instala un modelo desde una URL."""
    manager = ModelManager()
    # Por defecto, descargamos como 'model.onnx' dentro de la carpeta del modelo
    # Esto asume que la URL apunta directamente al archivo .onnx
    dest = storage.get_models_dir() / name / "model.onnx"
    
    async def _download():
        try:
            with console.status(f"[bold green]Descargando modelo '{name}'..."):
                await manager.download_model(name, url, dest, sha256=sha256)
            console.print(f"[green]✔[/green] Descarga de '[bold]{name}[/bold]' completada.")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

    asyncio.run(_download())


def _print_feedback_payload(payload: dict) -> None:
    feedback = payload.get("feedback", {})
    if not feedback:
        console.print("No feedback available.", style="yellow")
        return

    summary = feedback.get("summary")
    if summary:
        console.print(f"Summary: {summary}")

    advice_short = feedback.get("advice_short")
    if advice_short:
        console.print(f"Advice: {advice_short}")

    advice_long = feedback.get("advice_long")
    if advice_long:
        console.print(f"Details: {advice_long}")

    drills = feedback.get("drills", [])
    if drills:
        table = Table(title="Drills")
        table.add_column("Type", style="cyan")
        table.add_column("Text", style="green")
        for drill in drills:
            table.add_row(str(drill.get("type", "")), str(drill.get("text", "")))
        console.print(table)


@app.command()
def benchmark(
    dataset: Path = typer.Option(..., "--dataset", help="Ruta al archivo manifest.jsonl"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Límite de muestras"),
    lang: str = typer.Option("es", "--lang", help="Idioma objetivo"),
    config: Optional[Path] = typer.Option(None, "--config", help="Ruta al archivo de configuración"),
    model_pack: Optional[str] = typer.Option(None, "--model-pack", help="Model pack override"),
    llm_name: Optional[str] = typer.Option(None, "--llm", help="LLM adapter override"),
    prompt_path: Optional[Path] = typer.Option(None, "--prompt-path", help="Prompt override path"),
    output_schema_path: Optional[Path] = typer.Option(None, "--schema-path", help="Output schema override path"),
):
    """Ejecuta un benchmark de rendimiento (PER, RTF)."""
    if not dataset.exists():
        console.print(f"Error: Dataset no encontrado: {dataset}", style="red")
        raise typer.Exit(code=1)

    loader = DatasetLoader()
    calc = MetricsCalculator()
    kernel = _get_kernel(config, model_pack=model_pack, llm_name=llm_name)
    if prompt_path and not prompt_path.exists():
        console.print(f"Error: prompt not found: {prompt_path}", style="red")
        raise typer.Exit(code=1)
    if output_schema_path and not output_schema_path.exists():
        console.print(f"Error: schema not found: {output_schema_path}", style="red")
        raise typer.Exit(code=1)
    
    try:
        samples = loader.load_manifest(dataset)
        if limit:
            samples = samples[:limit]
            
        console.print(f"Iniciando benchmark con {len(samples)} muestras...", style="bold blue")
        
        results = []
        
        async def _run_batch():
            await kernel.setup()
            try:
                for i, s in enumerate(samples):
                    audio_path = s.get("audio")
                    ref_text = s.get("text")
                    
                    if not audio_path or not ref_text:
                        continue
                        
                    # Fix path relative to manifest if needed (simple assumption: absolute or same dir)
                    # For now assume audio_path is actionable
                    
                    start_time = time.perf_counter()
                    tmp_audio = False
                    wav_path = ""
                    try:
                        wav_path, tmp_audio = ensure_wav(audio_path)
                        # Run full comparison
                        # Kernel.run expects AudioInput dict
                        audio_in = to_audio_input(wav_path)

                        # Duración de audio para calcular RTF
                        res = await kernel.run(audio=audio_in, text=ref_text, lang=lang)
                        proc_time = time.perf_counter() - start_time

                        audio_dur = wav_duration(wav_path)

                        results.append({
                            "per": res["per"],
                            "proc_time": proc_time,
                            "audio_duration": audio_dur
                        })
                    finally:
                        if tmp_audio and wav_path:
                            cleanup_temp(wav_path)
                    
                    if i % 10 == 0:
                        console.print(f"Procesado {i+1}/{len(samples)}", end="\r")
            finally:
                await kernel.teardown()

        asyncio.run(_run_batch())
        
        summary = calc.calculate_summary(results)
        
        table = Table(title="Resultados del Benchmark")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Muestras", str(len(results)))
        table.add_row("Avg PER", f"{summary['avg_per']:.2%}")
        table.add_row("Min PER", f"{summary['min_per']:.2%}")
        table.add_row("Max PER", f"{summary['max_per']:.2%}")
        table.add_row("Avg RTF", f"{summary['avg_rtf']:.3f}x")
        
        console.print(table)

    except Exception as e:
        console.print(f"Error durante benchmark: {e}", style="red")
        raise typer.Exit(code=1)


console = Console()


def _stdout_supports_unicode() -> bool:
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return False
    return "utf" in encoding.lower()


def _emit_json(data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=not _stdout_supports_unicode(), indent=2)
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        try:
            buffer.write(payload.encode("utf-8"))
            buffer.write(b"\n")
            return
        except Exception:
            pass
    sys.stdout.write(payload + "\n")


def _read_json_source(path: Path) -> str:
    if str(path) == "-":
        return sys.stdin.read()
    return path.read_text(encoding="utf-8")


def _safe_print(message: str, *, style: Optional[str] = None) -> None:
    if _stdout_supports_unicode():
        if style:
            console.print(message, style=style)
        else:
            console.print(message)
        return
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write((message + "\n").encode("utf-8"))
        return
    sys.stdout.write(message + "\n")

class TranscribeFormat(str, Enum):
    json = "json"
    text = "text"

class OutputFormat(str, Enum):
    json = "json"
    table = "table"
    aligned = "aligned"


class CatalogOutput(str, Enum):
    human = "human"
    json = "json"


_PRACTICE_CONTEXTS = {"initial", "medial", "final", "cluster", "vowel_context"}
_IGNORED_TOKENS = {"ˈ", "ˌ", ".", "·", "ː", "ˑ"}
_TIE_BARS = {"\u0361", "\u035c"}
_VOWELS = {
    "a", "e", "i", "o", "u", "y",
    "æ", "ɑ", "ɒ", "ɔ", "ə", "ɚ", "ɝ",
    "ɛ", "ɜ", "ɐ", "ʌ", "ɪ", "ʊ", "ɯ",
    "ø", "œ", "ɶ", "ʏ", "ɨ",
}
_IPA_SCHEMA_VERSION = "1.0"
_COMPARE_MODES = {"casual", "objective", "phonetic"}
_EVAL_LEVELS = {"phonemic", "phonetic"}
_FEEDBACK_LEVELS = {"casual", "precise"}


def _get_kernel(
    config_path: Optional[Path] = None,
    *,
    model_pack: Optional[str] = None,
    llm_name: Optional[str] = None,
) -> Kernel:
    """Carga la configuración y crea el kernel."""
    from ipa_core.errors import NotReadyError
    try:
        cfg = loader.load_config(str(config_path) if config_path else None)
        cfg = apply_overrides(cfg, model_pack=model_pack, llm_name=llm_name)
        return create_kernel(cfg)
    except loader.ValidationError as e:
        console.print(loader.format_validation_error(e), style="red")
        raise typer.Exit(code=1)
    except (FileNotFoundError, NotReadyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)


def _exit_code_for_error(exc: Exception) -> int:
    if isinstance(exc, (FileNotFound, FileNotFoundError)):
        return 2
    if isinstance(exc, UnsupportedFormat):
        return 3
    if isinstance(exc, ValidationError):
        return 4
    if isinstance(exc, NotReadyError):
        return 5
    if isinstance(exc, KeyError):
        return 6
    return 1


def _normalize_context(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in _PRACTICE_CONTEXTS:
        raise ValueError(f"Contexto no soportado: {value}")
    return normalized


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "sample"


def _normalize_sound(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.strip().lower())
    for mark in _TIE_BARS:
        normalized = normalized.replace(mark, "")
    return normalized


def _position_label(index: int, total: int) -> str:
    if index <= 0:
        return "initial"
    if index >= total - 1:
        return "final"
    return "medial"


def _is_vowel(token: str) -> bool:
    return token in _VOWELS


def _filter_context_tokens(tokens: list[str]) -> list[str]:
    return [_normalize_sound(token) for token in tokens if token not in _IGNORED_TOKENS]


def _match_context(
    tokens: list[str],
    sound: str,
    context: str,
    before: Optional[str],
    after: Optional[str],
) -> Optional[int]:
    positions = [idx for idx, token in enumerate(tokens) if token == sound]
    if not positions:
        return None
    total = len(tokens)
    for idx in positions:
        if context == "initial" and idx == 0:
            return idx
        if context == "final" and idx == total - 1:
            return idx
        if context == "medial" and 0 < idx < total - 1:
            return idx
        if context == "cluster":
            left = tokens[idx - 1] if idx > 0 else None
            right = tokens[idx + 1] if idx < total - 1 else None
            if (left and not _is_vowel(left)) or (right and not _is_vowel(right)):
                return idx
        if context == "vowel_context":
            left = tokens[idx - 1] if idx > 0 else None
            right = tokens[idx + 1] if idx < total - 1 else None
            if before and left != before:
                continue
            if after and right != after:
                continue
            if not before and left and not _is_vowel(left):
                continue
            if not after and right and not _is_vowel(right):
                continue
            if left and right:
                return idx
    return None


def _pick_default_context(sound_entry: dict) -> str:
    contexts = sound_entry.get("contexts", {}) if isinstance(sound_entry, dict) else {}
    keys = [key for key in contexts.keys() if isinstance(key, str)]
    for preferred in ("medial", "initial", "final"):
        if preferred in keys:
            return preferred
    return keys[0] if keys else "initial"


def _resolve_feedback_level(value: Optional[str], evaluation_level: str) -> str:
    if value in ("casual", "precise"):
        return value
    if evaluation_level == "phonetic":
        return "precise"
    return "casual"


def _build_confidence(mode: str, pack_used: bool) -> tuple[str, list[str]]:
    warnings: list[str] = []
    confidence = "normal"
    if mode == "phonetic" and not pack_used:
        warnings.append(
            "Aviso: modo fonetico sin pack; confiabilidad baja, comparacion aproximada para IPA general."
        )
        confidence = "low"
    return confidence, warnings


def _sound_payload(entry: dict) -> dict:
    return {
        "id": entry.get("id"),
        "ipa": entry.get("ipa"),
        "label": entry.get("label"),
        "aliases": entry.get("aliases", []),
        "tags": entry.get("tags", []),
    }


def _prompt_lang(lang: Optional[str], *, non_interactive: bool) -> str:
    if lang:
        return normalize_lang(lang)
    if non_interactive:
        console.print("Error: --lang es requerido en modo no interactivo", style="red")
        raise typer.Exit(code=2)
    value = typer.prompt("Idioma (es/en)", default="es")
    return normalize_lang(value)


def _prompt_sound(sound: Optional[str], catalog: dict, *, non_interactive: bool) -> str:
    if sound:
        return sound
    if non_interactive:
        console.print("Error: --sound es requerido en modo no interactivo", style="red")
        raise typer.Exit(code=2)
    entries = list_sounds(catalog)
    console.print("Sonidos disponibles:", style="bold")
    for idx, entry in enumerate(entries, start=1):
        ipa = entry.get("ipa", "")
        label = entry.get("label", "")
        console.print(f"{idx}. {ipa} - {label}")
    choice = typer.prompt("Selecciona sonido (numero o IPA)", default=entries[0].get("ipa", ""))
    if str(choice).isdigit():
        pos = int(choice) - 1
        if 0 <= pos < len(entries):
            return entries[pos].get("ipa", "")
    return str(choice)


def _prompt_context(
    context: Optional[str],
    sound_entry: dict,
    *,
    non_interactive: bool,
) -> str:
    if context:
        return context
    default_context = _pick_default_context(sound_entry)
    if non_interactive:
        return default_context
    contexts = sound_entry.get("contexts", {}) if isinstance(sound_entry, dict) else {}
    options = [key for key in contexts.keys() if isinstance(key, str)]
    if options:
        console.print(f"Contextos disponibles: {', '.join(options)}")
    return typer.prompt("Contexto", default=default_context)


def _prompt_count(count: int, *, non_interactive: bool) -> int:
    if count > 0:
        return count
    if non_interactive:
        console.print("Error: --count debe ser mayor que 0", style="red")
        raise typer.Exit(code=2)
    return int(typer.prompt("Cantidad de ejemplos", default="10"))


def _build_request_payload(
    *,
    lang: str,
    sound: str,
    context: str,
    count: int,
    mode: str,
    evaluation_level: str,
    feedback_level: Optional[str],
    seed: Optional[int],
) -> dict:
    payload = {
        "lang": lang,
        "sound": sound,
        "context": context,
        "count": count,
        "mode": mode,
        "evaluation": evaluation_level,
    }
    if feedback_level:
        payload["feedback_level"] = feedback_level
    if seed is not None:
        payload["seed"] = seed
    return payload


def _build_meta(kernel: Kernel) -> dict:
    pack_id = kernel.model_pack.id if kernel.model_pack else None
    runtime = kernel.model_pack.runtime.kind if kernel.model_pack else None
    return {
        "model_pack": pack_id,
        "llm": runtime,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


async def _generate_llm_candidates(
    kernel: Kernel,
    *,
    lang: str,
    sound: dict,
    context: str,
    count: int,
    before: Optional[str],
    after: Optional[str],
) -> list[str]:
    if not kernel.llm or not kernel.model_pack:
        return []
    sound_ipa = sound.get("ipa", "")
    sound_label = sound.get("label", "")
    context_hint = {
        "initial": "inicio de palabra",
        "medial": "mitad de palabra",
        "final": "final de palabra",
        "cluster": "en cluster consonantico",
        "vowel_context": "entre vocales",
    }.get(context, context)
    extra = ""
    if before or after:
        extra = f" Vecino izquierdo: {before or 'cualquier vocal'}. Vecino derecho: {after or 'cualquier vocal'}."
    prompt = (
        "Eres un generador de ejemplos para practicar pronunciacion IPA.\n"
        f"Idioma: {lang}\n"
        f"Sonido IPA: {sound_ipa} ({sound_label})\n"
        f"Contexto: {context_hint}.{extra}\n"
        f"Genera {count} ejemplos cortos (palabras o frases breves), evita nombres propios.\n"
        "Devuelve SOLO JSON con la forma: {\"items\": [{\"text\": \"...\"}]}\n"
    )
    schema = {
        "type": "object",
        "required": ["items"],
        "properties": {"items": {"type": "array"}},
    }
    raw = await kernel.llm.complete(prompt, params=kernel.model_pack.params)
    payload = extract_json_object(raw)
    validate_json_schema(payload, schema)
    items = payload.get("items", [])
    results: list[str] = []
    for item in items:
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            text = item.get("text") or item.get("phrase") or ""
        else:
            text = ""
        text = str(text).strip()
        if text:
            results.append(text)
    return results


async def _validate_examples(
    kernel: Kernel,
    *,
    lang: str,
    sound: str,
    context: str,
    before: Optional[str],
    after: Optional[str],
    candidates: list[dict],
) -> list[dict]:
    validated: list[dict] = []
    for candidate in candidates:
        text = str(candidate.get("text", "")).strip()
        if not text:
            continue
        try:
            tr_result = await kernel.textref.to_ipa(text, lang=lang)
            norm = await kernel.pre.normalize_tokens(tr_result.get("tokens", []))
        except (ValidationError, NotReadyError):
            continue
        tokens = norm.get("tokens", [])
        filtered = _filter_context_tokens(tokens)
        match_idx = _match_context(filtered, sound, context, before, after)
        if match_idx is None:
            continue
        position = _position_label(match_idx, len(filtered))
        validated.append(
            {
                "text": text,
                "ipa": " ".join(tokens),
                "tokens": tokens,
                "position": position,
                "context": context,
                "source": candidate.get("source", "curated"),
                "validated": True,
            }
        )
    return validated


@app.command()
def transcribe(
    audio: Optional[str] = typer.Option(None, "--audio", "-a", help="Ruta al archivo de audio"),
    config: Optional[Path] = typer.Option(None, "--config", help="Ruta al archivo de configuración"),
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    backend: Optional[str] = typer.Option(None, "--backend", help="Nombre del backend ASR"),
    textref: Optional[str] = typer.Option(None, "--textref", help="Proveedor texto→IPA (fallback)"),
    mic: bool = typer.Option(False, "--mic", help="Capturar desde el micrófono"),
    seconds: float = typer.Option(3.0, "--seconds", help="Duración de la grabación en segundos"),
    output_format: TranscribeFormat = typer.Option(TranscribeFormat.text, "--format", "-f", help="Formato de salida"),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Salida en formato JSON"),
):
    """Transcribe audio a tokens IPA."""
    if not mic and not audio:
        console.print("Error: Debes especificar --audio o --mic", style="red")
        raise typer.Exit(code=1)

    kernel = _get_kernel(config)
    if backend:
        kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
    if textref:
        kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
    wav_path = ""
    tmp_audio = False
    payload = None
    try:
        if mic:
            wav_path, _ = record(seconds=seconds)
            tmp_audio = True
        else:
            wav_path = audio
        service = TranscriptionService(
            preprocessor=kernel.pre,
            asr=kernel.asr,
            textref=kernel.textref,
            default_lang=lang,
        )

        async def _run_transcribe():
            await kernel.setup()
            try:
                return await service.transcribe_file(wav_path, lang=lang)
            finally:
                await kernel.teardown()

        with console.status("[bold green]Transcribiendo..."):
            payload = asyncio.run(_run_transcribe())
    except (ValidationError, UnsupportedFormat, FileNotFound, FileNotFoundError, NotReadyError, KeyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=_exit_code_for_error(e))
    finally:
        if tmp_audio and wav_path:
            cleanup_temp(wav_path)

    tokens = payload.tokens if payload else []
    audio_in = payload.audio if payload else {}
    if json_output:
        output_format = TranscribeFormat.json

    if output_format == TranscribeFormat.json:
        _emit_json({
            "ipa": " ".join(tokens),
            "tokens": tokens,
            "lang": lang,
            "audio": audio_in
        })
    else:
        console.print(f"IPA ({lang}): [bold cyan]{' '.join(tokens)}[/bold cyan]")


def _print_compare_table(res: dict):
    table = Table(title=f"Resultado de la Comparación (PER: {res['per']:.2%})")
    table.add_column("Referencia", justify="center", style="green")
    table.add_column("Hipótesis (Usuario)", justify="center", style="cyan")
    table.add_column("Operación", justify="center")

    for ref, hyp in res["alignment"]:
        if ref == hyp:
            op = "[green]Match[/green]"
        elif ref is None:
            op = "[yellow]Inserción[/yellow]"
        elif hyp is None:
            op = "[red]Omisión[/red]"
        else:
            op = "[magenta]Sustitución[/magenta]"
            
        table.add_row(ref or "-", hyp or "-", op)
    
    console.print(table)


def _print_compare_aligned(res: dict):
    ref_line = "REF: "
    hyp_line = "HYP: "
    for ref, hyp in res["alignment"]:
        r = ref or "-"
        h = hyp or "-"
        width = max(len(r), len(h))
        ref_line += r.ljust(width) + " "
        hyp_line += h.ljust(width) + " "
    
    console.print(f"[bold]PER: {res['per']:.2%}[/bold]")
    console.print(ref_line)
    console.print(hyp_line)


def _print_accent_ranking(ranking: list[dict]) -> None:
    if not ranking:
        return
    table = Table(title="Acento (confianza)")
    table.add_column("Acento", style="cyan")
    table.add_column("PER", justify="right")
    table.add_column("Confianza", justify="right")
    for item in ranking:
        table.add_row(
            item.get("label", item.get("accent", "")),
            f"{item['per']:.2%}",
            f"{item['confidence'] * 100:.1f}%",
        )
    console.print(table)


def _print_accent_features(features: list[dict]) -> None:
    if not features:
        return
    table = Table(title="Rasgos de acento")
    table.add_column("Rasgo", style="magenta")
    table.add_column("Coincidencias", justify="right")
    table.add_column("Detalles")
    for feature in features:
        variants = feature.get("variants", [])
        details = ", ".join(
            f"{v['target']}→{v['alt'] or '_'} x{v['count']}" for v in variants
        ) or "-"
        table.add_row(
            feature.get("label", feature.get("id", "")),
            str(feature.get("matches", 0)),
            details,
        )
    console.print(table)


def _print_feedback(feedback: list[dict]) -> None:
    if not feedback:
        return
    table = Table(title="Feedback (ref → hyp)")
    table.add_column("Referencia", style="green")
    table.add_column("Hipótesis", style="cyan")
    table.add_column("Veces", justify="right")
    for item in feedback:
        table.add_row(str(item["ref"]), str(item["hyp"]), str(item["count"]))
    console.print(table)


@app.command()
def compare(
    audio: str = typer.Option(..., "--audio", "-a", help="Ruta al archivo de audio"),
    config: Optional[Path] = typer.Option(None, "--config", help="Ruta al archivo de configuración"),
    text: str = typer.Option(..., "--text", "-t", help="Texto de referencia"),
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    backend: Optional[str] = typer.Option(None, "--backend", help="Nombre del backend ASR"),
    textref: Optional[str] = typer.Option(None, "--textref", help="Proveedor texto→IPA"),
    comparator: Optional[str] = typer.Option(None, "--comparator", help="Nombre del comparador"),
    weight_sub: Optional[float] = typer.Option(None, "--weight-sub", help="Peso sustitución"),
    weight_ins: Optional[float] = typer.Option(None, "--weight-ins", help="Peso inserción"),
    weight_del: Optional[float] = typer.Option(None, "--weight-del", help="Peso eliminación"),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", "-f", help="Formato de salida"),
    accent_profile: Optional[str] = typer.Option(None, "--accent-profile", help="Ruta o nombre del perfil de acentos"),
    accent_target: Optional[str] = typer.Option(None, "--accent-target", help="ID del acento objetivo"),
    show_accent: bool = typer.Option(True, "--show-accent/--no-accent", help="Mostrar ranking de acento"),
    strict_ipa: bool = typer.Option(True, "--strict-ipa/--allow-textref", help="Requerir IPA directa del ASR"),
):
    """Compara el audio contra un texto de referencia y evalúa la pronunciación."""
    kernel = _get_kernel(config)
    if backend:
        kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
    if textref:
        kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
    if comparator:
        kernel.comp = registry.resolve_comparator(comparator.lower(), {})

    weights = {}
    if weight_sub is not None:
        weights["sub"] = weight_sub
    if weight_ins is not None:
        weights["ins"] = weight_ins
    if weight_del is not None:
        weights["del_"] = weight_del
    weights_payload = weights or None

    lang_key = (lang or "").split("-")[0]
    language_profile: dict | None = None
    accents: list[dict] = []
    features: list[dict] = []
    target_accent_id = accent_target
    target_ref_lang = lang
    accent_labels: dict[str, str] = {}

    if show_accent:
        try:
            loaded_profile = accent_analysis.load_profile(accent_profile)
            language_profile = loaded_profile.get("languages", {}).get(lang_key)
        except FileNotFoundError as exc:
            console.print(f"Warning: {exc}", style="yellow")
            show_accent = False

    if language_profile:
        accents = language_profile.get("accents", [])
        features = language_profile.get("features", [])
        if not target_accent_id:
            target_accent_id = language_profile.get("target")
        if not target_accent_id and accents:
            target_accent_id = accents[0].get("id")
        for accent in accents:
            accent_id = accent.get("id")
            if not accent_id:
                continue
            accent_labels[accent_id] = accent.get("label", accent_id)
            if accent_id == target_accent_id:
                target_ref_lang = accent.get("textref_lang", lang)

    service = ComparisonService(
        preprocessor=kernel.pre,
        asr=kernel.asr,
        textref=kernel.textref,
        comparator=kernel.comp,
        default_lang=lang,
    )

    async def _run_compare():
        await kernel.setup()
        try:
            payload = await service.compare_file_detail(
                audio,
                text,
                lang=target_ref_lang,
                weights=weights_payload,
                allow_textref_fallback=not strict_ipa,
                fallback_lang=lang,
            )
            hyp_tokens = payload.hyp_tokens
            ref_tokens = payload.ref_tokens
            compare_res = payload.result

            async def _ref_tokens(lang_code: str) -> list[str]:
                try:
                    tr_res = await kernel.textref.to_ipa(text, lang=lang_code or "")
                except (ValidationError, NotReadyError):
                    if lang_code != lang:
                        tr_res = await kernel.textref.to_ipa(text, lang=lang or "")
                    else:
                        raise
                norm_res = await kernel.pre.normalize_tokens(tr_res.get("tokens", []))
                return norm_res.get("tokens", [])

            feedback = accent_analysis.build_feedback(compare_res.get("ops", []))
            accent_payload = None

            if show_accent and accents:
                per_by_accent: dict[str, float] = {}
                accent_results: dict[str, dict] = {}
                for accent in accents:
                    accent_id = accent.get("id")
                    if not accent_id:
                        continue
                    accent_lang = accent.get("textref_lang", lang)
                    accent_ref = await _ref_tokens(accent_lang)
                    accent_res = await kernel.comp.compare(accent_ref, hyp_tokens, weights=weights_payload)
                    accent_results[accent_id] = accent_res
                    per_by_accent[accent_id] = accent_res["per"]
                ranking = accent_analysis.rank_accents(per_by_accent, accent_labels)
                target_res = accent_results.get(target_accent_id) if target_accent_id else None
                feature_data = accent_analysis.extract_features(
                    target_res.get("alignment", []) if target_res else [],
                    features,
                )
                accent_payload = {
                    "target": target_accent_id,
                    "ranking": ranking,
                    "features": feature_data,
                }

            result = dict(compare_res)
            result.update(
                {
                    "ref": {
                        "tokens": ref_tokens,
                        "ipa": " ".join(ref_tokens),
                        "lang": target_ref_lang,
                    },
                    "hyp": {
                        "tokens": hyp_tokens,
                        "ipa": " ".join(hyp_tokens),
                    },
                    "feedback": feedback,
                }
            )
            if accent_payload:
                result["accent"] = accent_payload
            return result
        finally:
            await kernel.teardown()

    try:
        with console.status("[bold green]Procesando comparación..."):
            res = asyncio.run(_run_compare())
    except (ValidationError, UnsupportedFormat, FileNotFound, FileNotFoundError, NotReadyError, KeyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=_exit_code_for_error(e))

    if output_format == OutputFormat.json:
        _emit_json(res)
    elif output_format == OutputFormat.aligned:
        _print_compare_aligned(res)
        _print_feedback(res.get("feedback", []))
        if show_accent:
            accent_data = res.get("accent", {})
            _print_accent_ranking(accent_data.get("ranking", []))
            _print_accent_features(accent_data.get("features", []))
    else:
        _print_compare_table(res)
        _print_feedback(res.get("feedback", []))
        if show_accent:
            accent_data = res.get("accent", {})
            _print_accent_ranking(accent_data.get("ranking", []))
            _print_accent_features(accent_data.get("features", []))


@app.command()
def feedback(
    audio: str = typer.Option(..., "--audio", "-a", help="Path to the audio file"),
    text: str = typer.Option(..., "--text", "-t", help="Reference text"),
    lang: str = typer.Option("es", "--lang", "-l", help="Target language"),
    mode: str = typer.Option("objective", "--mode", help="Comparison mode (casual/objective/phonetic)"),
    evaluation_level: str = typer.Option("phonemic", "--evaluation", "--evaluation-level", help="Evaluation level"),
    feedback_level: Optional[str] = typer.Option(None, "--feedback-level", help="Feedback level"),
    model_pack: Optional[str] = typer.Option(None, "--model-pack", help="Model pack override"),
    llm_name: Optional[str] = typer.Option(None, "--llm", help="LLM adapter override"),
    prompt_path: Optional[Path] = typer.Option(None, "--prompt-path", help="Prompt override path"),
    output_schema_path: Optional[Path] = typer.Option(None, "--schema-path", help="Output schema override path"),
    persist: bool = typer.Option(False, "--save/--no-save", help="Save feedback locally"),
    persist_dir: Optional[Path] = typer.Option(None, "--save-dir", help="Directory for saved feedback"),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Output JSON"),
):
    """Generate LLM feedback for a pronunciation attempt."""
    if mode not in _COMPARE_MODES:
        console.print("Error: --mode debe ser casual, objective o phonetic", style="red")
        raise typer.Exit(code=2)
    if evaluation_level not in _EVAL_LEVELS:
        console.print("Error: --evaluation debe ser phonemic o phonetic", style="red")
        raise typer.Exit(code=2)
    if feedback_level and feedback_level not in _FEEDBACK_LEVELS:
        console.print("Error: --feedback-level debe ser casual o precise", style="red")
        raise typer.Exit(code=2)
    before = _normalize_sound(before) if before else None
    after = _normalize_sound(after) if after else None
    kernel = _get_kernel(model_pack=model_pack, llm_name=llm_name)
    wav_path = ""
    tmp_audio = False

    try:
        wav_path, tmp_audio = ensure_wav(audio)
        audio_in = to_audio_input(wav_path)
    except (ValidationError, UnsupportedFormat, FileNotFound, FileNotFoundError, NotReadyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)

    service = FeedbackService(kernel)

    async def _run_feedback():
        await kernel.setup()
        try:
            return await service.analyze(
                audio=audio_in,
                text=text,
                lang=lang,
                mode=mode,
                evaluation_level=evaluation_level,
                feedback_level=feedback_level,
                prompt_path=prompt_path,
                output_schema_path=output_schema_path,
            )
        finally:
            await kernel.teardown()

    try:
        with console.status("[bold green]Generating feedback..."):
            res = asyncio.run(_run_feedback())
    except (ValidationError, UnsupportedFormat, FileNotFound, FileNotFoundError, NotReadyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if tmp_audio and wav_path:
            cleanup_temp(wav_path)

    persisted_to = None
    if persist:
        store = FeedbackStore(persist_dir)
        persisted_to = store.append(res, audio=audio_in, meta={"text": text, "lang": lang})

    if json_output:
        payload = dict(res)
        if persisted_to:
            payload["persisted_to"] = str(persisted_to)
        _emit_json(payload)
    else:
        compare = res.get("compare", {})
        per = compare.get("per")
        if per is not None:
            console.print(f"PER: {per:.2%}")
        _print_feedback_payload(res)
        if persisted_to:
            console.print(f"Saved to: {persisted_to}")


@app.command("feedback-export")
def feedback_export(
    out: Optional[Path] = typer.Option(None, "--out", help="Ruta de salida para el export"),
    persist_dir: Optional[Path] = typer.Option(None, "--dir", help="Directorio base de feedback"),
):
    """Exporta el indice de feedback a JSON."""
    store = FeedbackStore(persist_dir)
    try:
        export_path = store.export(out)
    except Exception as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(code=1)
    console.print(f"Exported to: {export_path}")


@ipa_app.command("list-sounds")
def ipa_list_sounds(
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo (es/en)"),
    output: CatalogOutput = typer.Option(CatalogOutput.human, "--output", "-o", help="Formato de salida"),
):
    """Lista sonidos IPA disponibles para un idioma."""
    lang_key = normalize_lang(lang)
    try:
        catalog = load_catalog(lang_key)
    except FileNotFoundError as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(code=1)

    sounds = list_sounds(catalog)
    if output == CatalogOutput.json:
        _emit_json({
            "schema_version": _IPA_SCHEMA_VERSION,
            "kind": "ipa.list-sounds",
            "request": {"lang": lang_key},
            "sounds": [_sound_payload(entry) for entry in sounds],
        })
        return

    table = Table(title=f"Sonidos IPA ({lang_key})")
    table.add_column("IPA", style="cyan")
    table.add_column("Etiqueta", style="green")
    table.add_column("Aliases", style="yellow")
    for entry in sounds:
        aliases = entry.get("aliases", [])
        alias_text = ", ".join(aliases) if isinstance(aliases, list) else ""
        table.add_row(
            str(entry.get("ipa", "")),
            str(entry.get("label", "")),
            alias_text,
        )
    console.print(table)


@ipa_app.command("explore")
def ipa_explore(
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Idioma objetivo (es/en)"),
    sound: Optional[str] = typer.Option(None, "--sound", "-s", help="Sonido IPA o alias"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Contexto (initial, medial, final, cluster, vowel-context)"),
    count: int = typer.Option(10, "--count", help="Numero maximo de ejemplos"),
    output: CatalogOutput = typer.Option(CatalogOutput.human, "--output", "-o", help="Formato de salida"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Semilla para muestreo"),
    interactive: bool = typer.Option(False, "--interactive", help="Forzar modo interactivo"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Desactivar prompts"),
):
    """Muestra detalles de un sonido y ejemplos verificados con IPA."""
    if interactive and non_interactive:
        console.print("Error: --interactive y --non-interactive son excluyentes", style="red")
        raise typer.Exit(code=2)
    lang_key = _prompt_lang(lang, non_interactive=non_interactive) if (interactive or not lang) else normalize_lang(lang)
    try:
        catalog = load_catalog(lang_key)
    except FileNotFoundError as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(code=1)

    sound_query = _prompt_sound(sound, catalog, non_interactive=non_interactive) if (interactive or not sound) else sound
    sound_entry = resolve_sound_entry(catalog, sound_query)
    if not sound_entry:
        console.print(f"Error: sonido no encontrado: {sound_query}", style="red")
        raise typer.Exit(code=1)

    raw_context = context
    if interactive and not context:
        raw_context = _prompt_context(context, sound_entry, non_interactive=non_interactive)
    if raw_context:
        try:
            context_key = _normalize_context(raw_context)
        except ValueError as exc:
            console.print(f"Error: {exc}", style="red")
            raise typer.Exit(code=2)
    else:
        context_key = None

    contexts = sound_entry.get("contexts", {}) if isinstance(sound_entry, dict) else {}
    candidates_by_context: dict[str, list[dict]] = {}
    if context_key:
        ctx_data = contexts.get(context_key, {})
        seeds = ctx_data.get("seeds", []) if isinstance(ctx_data, dict) else []
        candidates_by_context[context_key] = [{"text": seed.get("text"), "source": "curated"} for seed in seeds if isinstance(seed, dict)]
    else:
        for ctx, ctx_data in contexts.items():
            if not isinstance(ctx_data, dict):
                continue
            seeds = ctx_data.get("seeds", [])
            candidates_by_context[str(ctx)] = [{"text": seed.get("text"), "source": "curated"} for seed in seeds if isinstance(seed, dict)]

    kernel = _get_kernel()
    sound_ipa = _normalize_sound(sound_entry.get("ipa", ""))
    validated: list[dict] = []
    warnings: list[str] = []

    async def _run_explore():
        await kernel.setup()
        try:
            for ctx, items in candidates_by_context.items():
                validated.extend(
                    await _validate_examples(
                        kernel,
                        lang=lang_key,
                        sound=sound_ipa,
                        context=ctx,
                        before=None,
                        after=None,
                        candidates=items,
                    )
                )
        finally:
            await kernel.teardown()

    try:
        asyncio.run(_run_explore())
    except Exception as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(code=1)

    if not validated:
        warnings.append("No se encontraron ejemplos validados.")

    if seed is not None:
        random.Random(seed).shuffle(validated)
    if count > 0:
        validated = validated[:count]

    if output == CatalogOutput.json:
        _emit_json({
            "schema_version": _IPA_SCHEMA_VERSION,
            "kind": "ipa.explore",
            "request": {
                "lang": lang_key,
                "sound": sound_entry.get("ipa"),
                "context": context_key,
                "count": count,
            },
            "sound": _sound_payload(sound_entry),
            "examples": [
                {
                    "id": f"{sound_entry.get('id')}/{item.get('context')}/{_slugify(item.get('text', ''))}",
                    "text": item.get("text"),
                    "ipa": item.get("ipa"),
                    "position": item.get("position"),
                    "context": item.get("context"),
                    "source": item.get("source"),
                    "validated": item.get("validated", False),
                }
                for item in validated
            ],
            "warnings": warnings,
            "confidence": "normal",
            "meta": _build_meta(kernel),
        })
        return

    console.print(f"Sonido: {sound_entry.get('ipa')} - {sound_entry.get('label')}", style="bold")
    if warnings:
        for warning in warnings:
            console.print(warning, style="yellow")
    if not validated:
        return
    table = Table(title="Ejemplos")
    table.add_column("Texto", style="green")
    table.add_column("IPA", style="cyan")
    table.add_column("Contexto", style="magenta")
    for item in validated:
        table.add_row(
            str(item.get("text", "")),
            str(item.get("ipa", "")),
            str(item.get("context", "")),
        )
    console.print(table)


@ipa_app.command("practice")
def ipa_practice(
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Idioma objetivo (es/en)"),
    sound: Optional[str] = typer.Option(None, "--sound", "-s", help="Sonido IPA o alias"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Contexto (initial, medial, final, cluster, vowel-context)"),
    count: int = typer.Option(10, "--count", help="Numero de ejemplos"),
    mode: str = typer.Option("phonetic", "--mode", help="Modo de comparacion (casual/objective/phonetic)"),
    evaluation_level: str = typer.Option("phonetic", "--evaluation", "--evaluation-level", help="Nivel de evaluacion (phonemic/phonetic)"),
    feedback_level: Optional[str] = typer.Option(None, "--feedback-level", help="Nivel de feedback (casual/precise)"),
    before: Optional[str] = typer.Option(None, "--before", help="Vocal anterior (solo vowel-context)"),
    after: Optional[str] = typer.Option(None, "--after", help="Vocal posterior (solo vowel-context)"),
    audio: Optional[str] = typer.Option(None, "--audio", "-a", help="Ruta al audio"),
    mic: bool = typer.Option(False, "--mic", help="Grabar desde microfono"),
    seconds: float = typer.Option(3.0, "--seconds", help="Duracion de la grabacion"),
    loop: bool = typer.Option(False, "--loop", help="Iterar ejemplos con grabacion"),
    example_index: Optional[int] = typer.Option(None, "--example-index", help="Indice del ejemplo a evaluar"),
    output: CatalogOutput = typer.Option(CatalogOutput.human, "--output", "-o", help="Formato de salida"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Semilla para muestreo"),
    interactive: bool = typer.Option(False, "--interactive", help="Forzar modo interactivo"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Desactivar prompts"),
    model_pack: Optional[str] = typer.Option(None, "--model-pack", help="Model pack override"),
    llm_name: Optional[str] = typer.Option(None, "--llm", help="LLM adapter override"),
    prompt_path: Optional[Path] = typer.Option(None, "--prompt-path", help="Prompt override path"),
    output_schema_path: Optional[Path] = typer.Option(None, "--schema-path", help="Output schema override path"),
):
    """Genera práctica por sonido y contexto, con validación IPA."""
    if interactive and non_interactive:
        console.print("Error: --interactive y --non-interactive son excluyentes", style="red")
        raise typer.Exit(code=2)
    if audio and mic:
        console.print("Error: --audio y --mic son excluyentes", style="red")
        raise typer.Exit(code=2)
    if mode not in _COMPARE_MODES:
        console.print("Error: --mode debe ser casual, objective o phonetic", style="red")
        raise typer.Exit(code=2)
    if evaluation_level not in _EVAL_LEVELS:
        console.print("Error: --evaluation debe ser phonemic o phonetic", style="red")
        raise typer.Exit(code=2)
    if feedback_level and feedback_level not in _FEEDBACK_LEVELS:
        console.print("Error: --feedback-level debe ser casual o precise", style="red")
        raise typer.Exit(code=2)

    lang_key = _prompt_lang(lang, non_interactive=non_interactive) if (interactive or not lang) else normalize_lang(lang)
    try:
        catalog = load_catalog(lang_key)
    except FileNotFoundError as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(code=1)

    sound_query = _prompt_sound(sound, catalog, non_interactive=non_interactive) if (interactive or not sound) else sound
    sound_entry = resolve_sound_entry(catalog, sound_query)
    if not sound_entry:
        console.print(f"Error: sonido no encontrado: {sound_query}", style="red")
        raise typer.Exit(code=1)

    raw_context = context
    if not raw_context:
        raw_context = (
            _prompt_context(context, sound_entry, non_interactive=non_interactive)
            if not non_interactive
            else _pick_default_context(sound_entry)
        )
    try:
        context_key = _normalize_context(raw_context)
    except ValueError as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(code=2)

    count = _prompt_count(count, non_interactive=non_interactive)
    rng = random.Random(seed) if seed is not None else None

    contexts = sound_entry.get("contexts", {}) if isinstance(sound_entry, dict) else {}
    ctx_data = contexts.get(context_key, {}) if context_key else {}
    seeds = ctx_data.get("seeds", []) if isinstance(ctx_data, dict) else []
    candidates = [{"text": seed.get("text"), "source": "curated"} for seed in seeds if isinstance(seed, dict)]
    warnings: list[str] = []
    if not candidates:
        warnings.append("No hay ejemplos curados para este contexto.")

    kernel = _get_kernel(model_pack=model_pack, llm_name=llm_name)
    sound_ipa = _normalize_sound(sound_entry.get("ipa", ""))
    pack_used = kernel.model_pack is not None
    confidence, mode_warnings = _build_confidence(mode, pack_used)
    warnings.extend(mode_warnings)

    async def _run_practice():
        await kernel.setup()
        try:
            extra_needed = max(0, count - len(candidates))
            if extra_needed:
                if not kernel.llm:
                    warnings.append("LLM no disponible; se usaron solo ejemplos curados.")
                llm_items = await _generate_llm_candidates(
                    kernel,
                    lang=lang_key,
                    sound=sound_entry,
                    context=context_key,
                    count=extra_needed,
                    before=before,
                    after=after,
                )
                for item in llm_items:
                    candidates.append({"text": item, "source": "llm"})
            validated = await _validate_examples(
                kernel,
                lang=lang_key,
                sound=sound_ipa,
                context=context_key,
                before=before,
                after=after,
                candidates=candidates,
            )
            if rng:
                rng.shuffle(validated)
            return validated
        finally:
            await kernel.teardown()

    try:
        validated = asyncio.run(_run_practice())
    except Exception as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(code=1)

    if not validated:
        console.print("No se encontraron ejemplos validados.", style="yellow")
        raise typer.Exit(code=1)
    if len(validated) < count:
        warnings.append(f"Solo se validaron {len(validated)} ejemplos de {count}.")
    validated = validated[:count]

    for item in validated:
        item["id"] = f"{sound_entry.get('id')}/{item.get('context')}/{_slugify(item.get('text', ''))}"

    request_payload = _build_request_payload(
        lang=lang_key,
        sound=sound_entry.get("ipa", ""),
        context=context_key,
        count=count,
        mode=mode,
        evaluation_level=evaluation_level,
        feedback_level=feedback_level,
        seed=seed,
    )

    if not audio and not mic:
        if output == CatalogOutput.json:
            _emit_json({
                "schema_version": _IPA_SCHEMA_VERSION,
                "kind": "ipa.practice.set",
                "request": request_payload,
                "sound": _sound_payload(sound_entry),
                "items": [
                    {
                        "id": item.get("id"),
                        "text": item.get("text"),
                        "ipa": item.get("ipa"),
                        "position": item.get("position"),
                        "context": item.get("context"),
                        "source": item.get("source"),
                        "validated": item.get("validated", False),
                    }
                    for item in validated
                ],
                "warnings": warnings,
                "confidence": confidence,
                "meta": _build_meta(kernel),
            })
            return

        console.print(f"Modo IPA ({sound_entry.get('ipa')}) - contexto {context_key}", style="bold")
        for warning in warnings:
            console.print(warning, style="yellow")
        table = Table(title="Practica sugerida")
        table.add_column("Texto", style="green")
        table.add_column("IPA", style="cyan")
        for item in validated:
            table.add_row(str(item.get("text", "")), str(item.get("ipa", "")))
        console.print(table)
        return

    if loop and not mic:
        console.print("Error: --loop requiere --mic", style="red")
        raise typer.Exit(code=2)

    selected_indices = list(range(len(validated)))
    if not loop:
        if example_index is None and not non_interactive:
            console.print("Ejemplos disponibles:")
            for idx, item in enumerate(validated, start=1):
                console.print(f"{idx}. {item.get('text')}")
            example_index = int(typer.prompt("Selecciona ejemplo", default="1")) - 1
        if example_index is None:
            example_index = 0
        if example_index < 0 or example_index >= len(validated):
            console.print("Error: --example-index fuera de rango", style="red")
            raise typer.Exit(code=2)
        selected_indices = [example_index]

    feedback_level = _resolve_feedback_level(feedback_level, evaluation_level)

    def _emit_result(payload: dict) -> None:
        if output == CatalogOutput.json:
            _emit_json(payload)
            return
        compare = payload.get("compare", {})
        report = payload.get("report", {})
        if warnings:
            for warning in warnings:
                console.print(warning, style="yellow")
        if compare.get("per") is not None:
            console.print(f"PER: {compare.get('per'):.2%}")
        _print_feedback_payload(payload)
        if report.get("confidence"):
            console.print(f"Confiabilidad: {report.get('confidence')}")

    for idx in selected_indices:
        item = validated[idx]
        if mic:
            console.print(f"Grabando para: {item.get('text')}")
            if not non_interactive:
                typer.prompt("Presiona Enter para grabar", default="", show_default=False)
            wav_path, _ = record(seconds=seconds)
            tmp_audio = True
        else:
            wav_path, tmp_audio = ensure_wav(audio)
        audio_in = to_audio_input(wav_path)

        async def _run_feedback():
            await kernel.setup()
            try:
                service = FeedbackService(kernel)
                return await service.analyze(
                    audio=audio_in,
                    text=item.get("text", ""),
                    lang=lang_key,
                    mode=mode,
                    evaluation_level=evaluation_level,
                    feedback_level=feedback_level,
                    prompt_path=prompt_path,
                    output_schema_path=output_schema_path,
                )
            finally:
                await kernel.teardown()

        async def _run_fallback():
            await kernel.setup()
            try:
                service = ComparisonService(
                    preprocessor=kernel.pre,
                    asr=kernel.asr,
                    textref=kernel.textref,
                    comparator=kernel.comp,
                    default_lang=lang_key,
                )
                payload = await service.compare_file_detail(
                    wav_path,
                    item.get("text", ""),
                    lang=lang_key,
                )
                report = build_enriched_error_report(
                    target_text=item.get("text", ""),
                    target_tokens=payload.ref_tokens,
                    hyp_tokens=payload.hyp_tokens,
                    compare_result=payload.result,
                    lang=lang_key,
                    mode=mode,
                    evaluation_level=evaluation_level,
                    feedback_level=feedback_level,
                    confidence=confidence,
                    warnings=warnings,
                    meta=payload.meta,
                )
                feedback = generate_fallback_feedback(report)
                compare_payload = dict(payload.result)
                compare_payload.setdefault("mode", mode)
                compare_payload.setdefault("evaluation_level", evaluation_level)
                compare_payload.setdefault("score", report.get("metrics", {}).get("score"))
                return {
                    "report": report,
                    "compare": compare_payload,
                    "feedback": feedback,
                }
            finally:
                await kernel.teardown()

        try:
            result = asyncio.run(_run_feedback())
        except NotReadyError:
            result = asyncio.run(_run_fallback())
        except Exception as exc:
            console.print(f"Error: {exc}", style="red")
            raise typer.Exit(code=1)
        finally:
            if tmp_audio and wav_path:
                cleanup_temp(wav_path)

        payload = {
            "schema_version": _IPA_SCHEMA_VERSION,
            "kind": "ipa.practice.result",
            "request": request_payload,
            "sound": _sound_payload(sound_entry),
            "item": {
                "id": item.get("id"),
                "text": item.get("text"),
                "ipa": item.get("ipa"),
                "position": item.get("position"),
                "context": item.get("context"),
                "source": item.get("source"),
                "validated": item.get("validated", False),
            },
            "compare": result.get("compare"),
            "report": result.get("report"),
            "feedback": result.get("feedback"),
            "warnings": warnings,
            "confidence": confidence,
            "meta": _build_meta(kernel),
        }
        _emit_result(payload)


@ipa_app.command("load")
def ipa_load(
    path: Path = typer.Argument(..., help="Ruta al JSON IPA (o '-' para stdin)"),
    output: CatalogOutput = typer.Option(CatalogOutput.human, "--output", "-o", help="Formato de salida"),
):
    """Carga un JSON IPA y muestra un resumen en CLI."""
    try:
        raw = _read_json_source(path)
        payload = json.loads(raw)
    except FileNotFoundError:
        console.print(f"Error: archivo no encontrado: {path}", style="red")
        raise typer.Exit(code=1)
    except json.JSONDecodeError as exc:
        console.print(f"Error: JSON invalido: {exc}", style="red")
        raise typer.Exit(code=1)

    if output == CatalogOutput.json:
        _emit_json(payload)
        return

    if not isinstance(payload, dict):
        console.print("Error: JSON invalido (se esperaba objeto).", style="red")
        raise typer.Exit(code=1)

    kind = payload.get("kind", "unknown")
    _safe_print(f"IPA JSON: {kind}")

    warnings = payload.get("warnings", [])
    confidence = payload.get("confidence")
    if isinstance(warnings, list):
        for warning in warnings:
            _safe_print(str(warning))
    if confidence:
        _safe_print(f"Confiabilidad: {confidence}")

    if kind in ("ipa.practice.set", "ipa.explore"):
        items = payload.get("items") if kind == "ipa.practice.set" else payload.get("examples")
        sound = payload.get("sound", {}).get("ipa") if isinstance(payload.get("sound"), dict) else None
        context = payload.get("request", {}).get("context") if isinstance(payload.get("request"), dict) else None
        if sound:
            _safe_print(f"Sonido: {sound}")
        if context:
            _safe_print(f"Contexto: {context}")
        if not items:
            _safe_print("No hay ejemplos.")
            return
        _safe_print("Ejemplos:")
        for item in items:
            if not isinstance(item, dict):
                continue
            _safe_print(
                f"- {item.get('text', '')} | {item.get('ipa', '')} | {item.get('context', '')}"
            )
        return

    if kind == "ipa.list-sounds":
        sounds = payload.get("sounds", [])
        _safe_print("Sonidos:")
        for entry in sounds:
            if not isinstance(entry, dict):
                continue
            _safe_print(f"- {entry.get('ipa', '')} | {entry.get('label', '')}")
        return

    if kind == "ipa.practice.result":
        item = payload.get("item", {})
        if isinstance(item, dict):
            _safe_print(f"Texto: {item.get('text', '')}")
            _safe_print(f"IPA: {item.get('ipa', '')}")
        compare = payload.get("compare", {})
        if isinstance(compare, dict) and compare.get("per") is not None:
            _safe_print(f"PER: {compare.get('per'):.2%}")
        return


@config_app.command("show")
def config_show():
    """Muestra la configuración actual."""
    try:
        cfg = loader.load_config()
        _emit_json(cfg.model_dump())
    except Exception as e:
        console.print(f"Error cargando configuración: {e}", style="red")
        raise typer.Exit(code=1)


from ipa_core.plugins import registry, discovery
from ipa_core.plugins.manager import PluginManager


@plugin_app.command("list")
def plugin_list():
    """Lista los plugins instalados y su metadata básica."""
    manager = PluginManager()
    plugins = manager.get_installed_plugins()

    if not plugins:
        console.print("No se encontraron plugins instalados.", style="yellow")
        return

    table = Table(title="Plugins Registrados")
    table.add_column("Categoría", style="bold magenta")
    table.add_column("Nombre", style="cyan")
    table.add_column("Versión", style="green")
    table.add_column("Autor", style="yellow")
    table.add_column("Estado", justify="center")
    
    for p in plugins:
        status = "[green]Enabled[/green]" if p.enabled else "[white]Installed[/white]"
        table.add_row(
            p.category.upper(),
            p.name,
            p.version,
            p.author,
            status
        )
        
    console.print(table)


@plugin_app.command("info")
def plugin_info(
    category: str = typer.Argument(..., help="Categoría del plugin (asr, textref, etc.)"),
    name: str = typer.Argument(..., help="Nombre del plugin"),
):
    """Muestra información detallada de un plugin específico."""
    manager = PluginManager()
    p = manager.get_plugin_info(category.lower(), name)
    
    if not p:
        console.print(f"[red]Error:[/red] No se encontró el plugin '{category}.{name}'")
        raise typer.Exit(code=1)
        
    table = Table(show_header=False, title=f"Detalles: {category}.{name}")
    table.add_column("Propiedad", style="bold")
    table.add_column("Valor")
    
    table.add_row("Nombre", p.name)
    table.add_row("Categoría", p.category.upper())
    table.add_row("Versión", p.version)
    table.add_row("Autor", p.author)
    table.add_row("Descripción", p.description)
    table.add_row("Entry Point", p.entry_point)
    
    console.print(table)


@plugin_app.command("validate")
def plugin_validate():
    """Valida que todos los plugins instalados cumplan con sus contratos."""
    table = Table(title="Validación de Plugins")
    table.add_column("Plugin", style="cyan")
    table.add_column("Estado", justify="center")
    table.add_column("Detalles")
    
    found = False
    for category, name, ep in discovery.iter_plugin_entry_points():
        found = True
        try:
            plugin_cls = ep.load()
            is_valid, errors = registry.validate_plugin(category, plugin_cls)
            
            if is_valid:
                status = "[green]VALID[/green]"
                detail = "Correcto"
            else:
                status = "[red]INVALID[/red]"
                detail = ", ".join(errors)
        except Exception as e:
            status = "[bold red]ERROR[/bold red]"
            detail = f"No se pudo cargar: {e}"
            
        table.add_row(f"{category}.{name}", status, detail)
        
    if not found:
        console.print("No se encontraron plugins externos para validar.")
    else:
        console.print(table)


@plugin_app.command("install")
def plugin_install(
    package: str = typer.Argument(..., help="Nombre del paquete (o URL de git) a instalar"),
):
    """Instala un nuevo plugin usando pip."""
    import importlib
    
    manager = PluginManager()
    console.print(f"Instalando [bold cyan]{package}[/bold cyan]...")
    
    try:
        manager.install_plugin(package)
            
        console.print(f"[green]✔[/green] Instalación de '[bold]{package}[/bold]' completada.")
        
        # Post-install check: ¿Es un plugin de PronunciaPA?
        importlib.invalidate_caches() # Refrescar metadata de python
        
        # Ver si el paquete recién instalado registró algo
        # (Nota: iter_plugin_entry_points volverá a escanear)
        is_plugin = False
        for _, _, ep in discovery.iter_plugin_entry_points():
            # Comparar nombre de paquete (heurística simple)
            # ep.value suele ser 'package.module:attr'
            ep_package = ep.value.split(".")[0].split(":")[0]
            # Normalizar nombres para comparación básica (pip suele usar guiones, importlib guiones bajos o viceversa)
            if ep_package.replace("_", "-") in package.replace("_", "-"):
                is_plugin = True
                break
        
        if not is_plugin:
            console.print(
                "[yellow]WARNING:[/yellow] El paquete se instaló, pero no parece registrar "
                "ningún plugin para PronunciaPA (entry points)."
            )
            
    except RuntimeError as e:
        console.print(f"[red]Error al instalar:[/red]\n{e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error inesperado:[/red] {e}")
        raise typer.Exit(code=1)


@plugin_app.command("uninstall")
def plugin_uninstall(
    package: str = typer.Argument(..., help="Nombre del paquete a desinstalar"),
):
    """Desinstala un plugin usando pip."""
    manager = PluginManager()

    # Confirmación
    if not typer.confirm(f"¿Estás seguro de que deseas desinstalar '{package}'?"):
        console.print("Operación cancelada.")
        return

    console.print(f"Desinstalando [bold cyan]{package}[/bold cyan]...")
    
    try:
        manager.uninstall_plugin(package)
        console.print(f"[green]✔[/green] El paquete '[bold]{package}[/bold]' ha sido desinstalado.")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except RuntimeError as e:
        console.print(f"[red]Error al desinstalar:[/red]\n{e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error inesperado:[/red] {e}")
        raise typer.Exit(code=1)


# =============================================================================
# Modo Interactivo
# =============================================================================

class TranscriptionModeChoice(str, Enum):
    phonemic = "phonemic"
    phonetic = "phonetic"


class FeedbackLevelChoice(str, Enum):
    casual = "casual"
    precise = "precise"


@app.command()
def interactive(
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    mode: TranscriptionModeChoice = typer.Option(
        TranscriptionModeChoice.phonemic,
        "--mode", "-m",
        help="Modo de transcripción: phonemic (/.../) o phonetic ([...])"
    ),
    feedback_level: FeedbackLevelChoice = typer.Option(
        FeedbackLevelChoice.casual,
        "--feedback-level", "-f",
        help="Nivel de feedback: casual (sencillo) o precise (detallado)"
    ),
):
    """Modo interactivo con interfaz TUI, grabación en tiempo real y gamificación.
    
    Practica tu pronunciación con feedback visual inmediato.
    Incluye sistema de niveles, logros y estadísticas.
    
    Controles:
      r - Grabar audio
      t - Cambiar texto de referencia
      m - Alternar modo fonémico/fonético
      l - Cambiar idioma
      f - Cambiar nivel de feedback
      s - Ver estadísticas
      q - Salir
    """
    from ipa_core.interfaces.interactive import (
        run_interactive_session,
        TranscriptionMode,
        FeedbackLevel,
    )
    
    # Convertir enums
    tx_mode = (
        TranscriptionMode.PHONEMIC
        if mode == TranscriptionModeChoice.phonemic
        else TranscriptionMode.PHONETIC
    )
    fb_level = (
        FeedbackLevel.CASUAL
        if feedback_level == FeedbackLevelChoice.casual
        else FeedbackLevel.PRECISE
    )
    
    # Factory para crear kernel con config
    def kernel_factory():
        return _get_kernel()
    
    asyncio.run(run_interactive_session(
        initial_lang=lang,
        initial_mode=tx_mode,
        feedback_level=fb_level,
        kernel_factory=kernel_factory,
    ))


def main():
    """Punto de entrada para el script de consola."""
    app()


def cli_transcribe(audio: Optional[str], lang: str = "es", use_mic: bool = False, seconds: float = 3.0, textref: Optional[str] = None):
    """Wrapper para compatibilidad con tests antiguos."""
    if not use_mic and not audio:
        raise ValueError("Debes especificar audio o mic")

    kernel = _get_kernel()
    # Si se especificó un textref por parámetro, sobreescribir el del kernel para el test
    if textref:
        from ipa_core.plugins import registry
        kernel.textref = registry.resolve_textref(textref, {"default_lang": lang})

    wav_path = ""
    tmp_audio = False
    if use_mic:
        wav_path, _ = record(seconds=seconds)
        tmp_audio = True
    else:
        wav_path, tmp_audio = ensure_wav(audio)
    audio_in = to_audio_input(wav_path)

    async def _run():
        await kernel.setup()
        try:
            return await transcribe_pipeline(kernel.pre, kernel.asr, kernel.textref, audio=audio_in, lang=lang)
        finally:
            await kernel.teardown()

    try:
        return asyncio.run(_run())
    finally:
        if tmp_audio and wav_path:
            cleanup_temp(wav_path)


if __name__ == "__main__":
    main()
