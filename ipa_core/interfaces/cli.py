"""CLI para interactuar con PronunciaPA.

Este módulo define los comandos de línea de comandos para transcripción
y comparación fonética.
"""
from __future__ import annotations
import asyncio
import json
from typing import Optional, List
from enum import Enum
import typer
from rich.console import Console
from rich.table import Table
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
    await kernel.setup()
    try:
        processed = await kernel.pre.process_audio(audio_in)
        return await kernel.asr.transcribe(processed, lang=lang)
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
    
    async def _run_compare():
        await kernel.setup()
        try:
            return await kernel.run(audio=audio_in, text=text, lang=lang)
        finally:
            await kernel.teardown()

    with console.status("[bold green]Procesando comparación..."):
        res = asyncio.run(_run_compare())

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


from ipa_core.plugins import registry, discovery


@plugin_app.command("list")
def plugin_list():
    """Lista los plugins instalados y su metadata básica."""
    table = Table(title="Plugins Instalados")
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
        
    audio_in: AudioInput = {"path": audio or "microphone", "sample_rate": 16000, "channels": 1}
    
    async def _run():
        await kernel.setup()
        try:
            processed = await kernel.pre.process_audio(audio_in)
            res = await kernel.asr.transcribe(processed, lang=lang)
            return res["tokens"]
        finally:
            await kernel.teardown()
            
    return asyncio.run(_run())


if __name__ == "__main__":
    main()
