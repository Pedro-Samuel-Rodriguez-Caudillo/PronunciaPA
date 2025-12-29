from __future__ import annotations
import asyncio
import json
from typing import Optional, List
from enum import Enum
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from ipa_core.config import loader
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.types import AudioInput
from ipa_core.plugins import registry

app = typer.Typer(help="PronunciaPA: Reconocimiento y evaluación fonética")
config_app = typer.Typer(help="Gestión de configuración")
plugin_app = typer.Typer(help="Gestión de plugins")

app.add_typer(config_app, name="config")
app.add_typer(plugin_app, name="plugin")

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


async def _transcribe_async(kernel: Kernel, audio_in: AudioInput, lang: str) -> dict:
    processed = await kernel.pre.process_audio(audio_in)
    return await kernel.asr.transcribe(processed, lang=lang)


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
    audio_in: AudioInput = {"path": audio or "microphone", "sample_rate": 16000, "channels": 1}
    
    with console.status("[bold green]Transcribiendo..."):
        res = asyncio.run(_transcribe_async(kernel, audio_in, lang))

    if json_output:
        console.print_json(data={
            "ipa": " ".join(res["tokens"]),
            "tokens": res["tokens"],
            "lang": lang,
            "audio": audio_in
        })
    else:
        console.print(f"IPA ({lang}): [bold cyan]{' '.join(res['tokens'])}[/bold cyan]")


def _print_compare_table(res: dict):
    table = Table(title=f"Resultado de la Comparación (PER: {res['per']:.2%})")
    table.add_column("Referencia", justify="center", style="green")
    table.add_column("Hipótesis (Usuario)", justify="center", style="cyan")
    table.add_column("Operación", justify="center")

    for ref, hyp in res["alignment"]:
        # Determinar la operación
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


@app.command()
def compare(
    audio: str = typer.Option(..., "--audio", "-a", help="Ruta al archivo de audio"),
    text: str = typer.Option(..., "--text", "-t", help="Texto de referencia"),
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", "-f", help="Formato de salida"),
):
    """Compara el audio contra un texto de referencia y evalúa la pronunciación."""
    kernel = _get_kernel()
    audio_in: AudioInput = {"path": audio, "sample_rate": 16000, "channels": 1}
    
    with console.status("[bold green]Procesando comparación..."):
        res = asyncio.run(kernel.run(audio=audio_in, text=text, lang=lang))

    if output_format == OutputFormat.json:
        console.print_json(data=res)
    elif output_format == OutputFormat.aligned:
        _print_compare_aligned(res)
    else:
        _print_compare_table(res)


@config_app.command("show")
def config_show():
    """Muestra la configuración actual."""
    try:
        cfg = loader.load_config()
        console.print_json(data=cfg.model_dump())
    except Exception as e:
        console.print(f"Error cargando configuración: {e}", style="red")
        raise typer.Exit(code=1)


@plugin_app.command("list")
def plugin_list():
    """Lista los plugins registrados."""
    registry._register_defaults()
    
    table = Table(title="Plugins Registrados")
    table.add_column("Categoría", style="bold magenta")
    table.add_column("Plugins", style="cyan")
    
    for category, plugins in registry._REGISTRY.items():
        table.add_row(category, ", ".join(plugins.keys()))
        
    console.print(table)



def main():
    """Punto de entrada para el script de consola."""
    app()


if __name__ == "__main__":
    main()