"""CLI para interactuar con PronunciaPA.

Este módulo define los comandos de línea de comandos para transcripción
y comparación fonética.
"""
from __future__ import annotations
import asyncio
from typing import Optional
from enum import Enum
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
from ipa_core.services.transcription import TranscriptionService
from ipa_core.types import AudioInput
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

class TranscribeFormat(str, Enum):
    json = "json"
    text = "text"

class OutputFormat(str, Enum):
    json = "json"
    table = "table"
    aligned = "aligned"


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
        console.print_json(data={
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
        console.print_json(data=res)
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
    model_pack: Optional[str] = typer.Option(None, "--model-pack", help="Model pack override"),
    llm_name: Optional[str] = typer.Option(None, "--llm", help="LLM adapter override"),
    prompt_path: Optional[Path] = typer.Option(None, "--prompt-path", help="Prompt override path"),
    output_schema_path: Optional[Path] = typer.Option(None, "--schema-path", help="Output schema override path"),
    persist: bool = typer.Option(False, "--save/--no-save", help="Save feedback locally"),
    persist_dir: Optional[Path] = typer.Option(None, "--save-dir", help="Directory for saved feedback"),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Output JSON"),
):
    """Generate LLM feedback for a pronunciation attempt."""
    kernel = _get_kernel()
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
        console.print_json(data=payload)
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


@config_app.command("show")
def config_show():
    """Muestra la configuración actual."""
    try:
        cfg = loader.load_config()
        console.print_json(data=cfg.model_dump())
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
