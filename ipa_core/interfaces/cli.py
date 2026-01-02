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
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.config import loader
from ipa_core.errors import FileNotFound, NotReadyError, UnsupportedFormat, ValidationError
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.pipeline.transcribe import transcribe as transcribe_pipeline
from ipa_core.types import AudioInput
from ipa_core.plugins.models import storage
from ipa_core.plugins.model_manager import ModelManager

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


console = Console()

class OutputFormat(str, Enum):
    json = "json"
    table = "table"
    aligned = "aligned"


def _get_kernel() -> Kernel:
    """Carga la configuración y crea el kernel."""
    from ipa_core.errors import NotReadyError
    try:
        cfg = loader.load_config()
        return create_kernel(cfg)
    except loader.ValidationError as e:
        console.print(loader.format_validation_error(e), style="red")
        raise typer.Exit(code=1)
    except (FileNotFoundError, NotReadyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)


async def _transcribe_async(kernel: Kernel, audio_in: AudioInput, lang: str) -> list[str]:
    await kernel.setup()
    try:
        return await transcribe_pipeline(kernel.pre, kernel.asr, kernel.textref, audio=audio_in, lang=lang)
    finally:
        await kernel.teardown()


@app.command()
def transcribe(
    audio: Optional[str] = typer.Option(None, "--audio", "-a", help="Ruta al archivo de audio"),
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    mic: bool = typer.Option(False, "--mic", help="Capturar desde el micrófono"),
    seconds: float = typer.Option(3.0, "--seconds", help="Duración de la grabación en segundos"),
    json_output: bool = typer.Option(False, "--json/--no-json", help="Salida en formato JSON"),
):
    """Transcribe audio a tokens IPA."""
    if not mic and not audio:
        console.print("Error: Debes especificar --audio o --mic", style="red")
        raise typer.Exit(code=1)

    kernel = _get_kernel()
    wav_path = ""
    tmp_audio = False
    try:
        if mic:
            wav_path, _ = record(seconds=seconds)
            tmp_audio = True
        else:
            wav_path, tmp_audio = ensure_wav(audio)
        audio_in = to_audio_input(wav_path)

        with console.status("[bold green]Transcribiendo..."):
            tokens = asyncio.run(_transcribe_async(kernel, audio_in, lang))
    except (ValidationError, UnsupportedFormat, FileNotFound, FileNotFoundError, NotReadyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if tmp_audio and wav_path:
            cleanup_temp(wav_path)

    if json_output:
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
    text: str = typer.Option(..., "--text", "-t", help="Texto de referencia"),
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", "-f", help="Formato de salida"),
    accent_profile: Optional[str] = typer.Option(None, "--accent-profile", help="Ruta o nombre del perfil de acentos"),
    accent_target: Optional[str] = typer.Option(None, "--accent-target", help="ID del acento objetivo"),
    show_accent: bool = typer.Option(True, "--show-accent/--no-accent", help="Mostrar ranking de acento"),
    strict_ipa: bool = typer.Option(True, "--strict-ipa/--allow-textref", help="Requerir IPA directa del ASR"),
):
    """Compara el audio contra un texto de referencia y evalúa la pronunciación."""
    kernel = _get_kernel()
    wav_path = ""
    tmp_audio = False
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

    try:
        wav_path, tmp_audio = ensure_wav(audio)
        audio_in = to_audio_input(wav_path)
    except (ValidationError, UnsupportedFormat, FileNotFound, FileNotFoundError, NotReadyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)

    async def _run_compare():
        await kernel.setup()
        try:
            pre_audio_res = await kernel.pre.process_audio(audio_in)
            processed_audio = pre_audio_res.get("audio", audio_in)
            asr_result = await kernel.asr.transcribe(processed_audio, lang=lang)
            hyp_tokens = asr_result.get("tokens")
            if not hyp_tokens and not strict_ipa:
                raw_text = asr_result.get("raw_text", "")
                if raw_text:
                    tr_res = await kernel.textref.to_ipa(raw_text, lang=lang or "")
                    hyp_tokens = tr_res.get("tokens", [])
            if not hyp_tokens:
                raise ValidationError("ASR no devolvió tokens IPA")

            hyp_pre_res = await kernel.pre.normalize_tokens(hyp_tokens)
            hyp_tokens = hyp_pre_res.get("tokens", [])

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

            ref_tokens = await _ref_tokens(target_ref_lang)
            compare_res = await kernel.comp.compare(ref_tokens, hyp_tokens)

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
                    accent_res = await kernel.comp.compare(accent_ref, hyp_tokens)
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
    except (ValidationError, UnsupportedFormat, FileNotFound, FileNotFoundError, NotReadyError) as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)
    finally:
        if tmp_audio and wav_path:
            cleanup_temp(wav_path)

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


@plugin_app.command("list")
def plugin_list():
    """Lista los plugins instalados y su metadata básica."""
    table = Table(title="Plugins Registrados")
    table.add_column("Categoría", style="bold magenta")
    table.add_column("Nombre", style="cyan")
    table.add_column("Versión", style="green")
    table.add_column("Autor", style="yellow")
    
    for category, name, ep in discovery.iter_plugin_entry_points():
        # Deducir paquete para metadatos
        package_name = ep.value.split(".")[0].split(":")[0]
        meta = discovery.get_package_metadata(package_name)
        
        table.add_row(
            category.upper(),
            name,
            meta["version"],
            meta["author"]
        )
        
    console.print(table)


@plugin_app.command("inspect")
def plugin_inspect(
    category: str = typer.Argument(..., help="Categoría del plugin (asr, textref, etc.)"),
    name: str = typer.Argument(..., help="Nombre del plugin"),
):
    """Muestra información detallada de un plugin específico."""
    details = discovery.get_plugin_details(category.lower(), name)
    
    if not details:
        console.print(f"[red]Error:[/red] No se encontró el plugin '{category}.{name}'")
        raise typer.Exit(code=1)
        
    table = Table(show_header=False, title=f"Detalles: {category}.{name}")
    table.add_column("Propiedad", style="bold")
    table.add_column("Valor")
    
    table.add_row("Nombre", details["name"])
    table.add_row("Categoría", details["category"].upper())
    table.add_row("Versión", details["version"])
    table.add_row("Autor", details["author"])
    table.add_row("Descripción", details["description"])
    table.add_row("Entry Point", details["entry_point"])
    
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
    import subprocess
    import sys
    import importlib

    console.print(f"Instalando [bold cyan]{package}[/bold cyan]...")
    
    try:
        # Ejecutar pip install
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]Error al instalar:[/red]\n{result.stderr}")
            raise typer.Exit(code=1)
            
        console.print(f"[green]✔[/green] Instalación de '[bold]{package}[/bold]' completada.")
        
        # Post-install check: ¿Es un plugin de PronunciaPA?
        importlib.invalidate_caches() # Refrescar metadata de python
        
        # Ver si el paquete recién instalado registró algo
        # (Nota: iter_plugin_entry_points volverá a escanear)
        is_plugin = False
        for _, _, ep in discovery.iter_plugin_entry_points():
            # Comparar nombre de paquete (heurística simple)
            ep_package = ep.value.split(".")[0].split(":")[0]
            if ep_package in package or package in ep_package:
                is_plugin = True
                break
        
        if not is_plugin:
            console.print(
                "[yellow]WARNING:[/yellow] El paquete se instaló, pero no parece registrar "
                "ningún plugin para PronunciaPA (entry points)."
            )
            
    except Exception as e:
        console.print(f"[red]Error inesperado:[/red] {e}")
        raise typer.Exit(code=1)


@plugin_app.command("uninstall")
def plugin_uninstall(
    package: str = typer.Argument(..., help="Nombre del paquete a desinstalar"),
):
    """Desinstala un plugin usando pip."""
    import subprocess
    import sys

    # Confirmación
    if not typer.confirm(f"¿Estás seguro de que deseas desinstalar '{package}'?"):
        console.print("Operación cancelada.")
        return

    console.print(f"Desinstalando [bold cyan]{package}[/bold cyan]...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]Error al desinstalar:[/red]\n{result.stderr}")
            raise typer.Exit(code=1)
            
        console.print(f"[green]✔[/green] El paquete '[bold]{package}[/bold]' ha sido desinstalado.")
            
    except Exception as e:
        console.print(f"[red]Error inesperado:[/red] {e}")
        raise typer.Exit(code=1)


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
