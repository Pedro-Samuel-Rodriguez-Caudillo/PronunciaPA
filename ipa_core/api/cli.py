"""CLI para interactuar con PronunciaPA.

Este módulo define los comandos de línea de comandos para transcripción
y comparación fonética.
"""
from __future__ import annotations
import asyncio
import json
from typing import Optional
import typer
from ipa_core.config import loader
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.types import AudioInput

app = typer.Typer(help="PronunciaPA: Reconocimiento y evaluación fonética")


def _get_kernel() -> Kernel:
    """Carga la configuración y crea el kernel."""
    from ipa_core.errors import NotReadyError
    try:
        cfg = loader.load_config()
        return create_kernel(cfg)
    except loader.ValidationError as e:
        typer.echo(loader.format_validation_error(e), err=True)
        raise typer.Exit(code=1)
    except (FileNotFoundError, NotReadyError) as e:
        typer.echo(f"Error: {e}", err=True)
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
        typer.echo("Error: Debes especificar --audio o --mic", err=True)
        raise typer.Exit(code=1)

    kernel = _get_kernel()
    # TODO: Manejar grabación de micrófono real
    audio_in: AudioInput = {"path": audio or "microphone", "sample_rate": 16000, "channels": 1}
    
    res = asyncio.run(_transcribe_async(kernel, audio_in, lang))

    if json_output:
        typer.echo(json.dumps({
            "ipa": " ".join(res["tokens"]),
            "tokens": res["tokens"],
            "lang": lang,
            "audio": audio_in
        }, ensure_ascii=False))
    else:
        typer.echo(f"IPA ({lang}): {' '.join(res['tokens'])}")


@app.command()
def compare(
    audio: str = typer.Option(..., "--audio", "-a", help="Ruta al archivo de audio"),
    text: str = typer.Option(..., "--text", "-t", help="Texto de referencia"),
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Salida en formato JSON (por defecto)"),
):
    """Compara el audio contra un texto de referencia y evalúa la pronunciación."""
    kernel = _get_kernel()
    audio_in: AudioInput = {"path": audio, "sample_rate": 16000, "channels": 1}
    
    res = asyncio.run(kernel.run(audio=audio_in, text=text, lang=lang))

    if json_output:
        typer.echo(json.dumps(res, ensure_ascii=False))
    else:
        typer.echo(f"PER: {res['per']}")


def main():
    """Punto de entrada para el script de consola."""
    app()


if __name__ == "__main__":
    main()