"""CLI para interactuar con PronunciaPA.

Este módulo define los comandos de línea de comandos para transcripción
y comparación fonética.
"""
from __future__ import annotations
import json
from typing import Optional
import typer

app = typer.Typer(help="PronunciaPA: Reconocimiento y evaluación fonética")


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

    # TODO: Implementar lógica real llamando al Kernel
    stub_result = {
        "ipa": "o l a",
        "tokens": ["o", "l", "a"],
        "lang": lang,
        "audio": {"path": audio or "microphone", "sample_rate": 16000, "channels": 1},
    }

    if json_output:
        typer.echo(json.dumps(stub_result, ensure_ascii=False))
    else:
        typer.echo(f"IPA ({lang}): {stub_result['ipa']}")


@app.command()
def compare(
    audio: str = typer.Option(..., "--audio", "-a", help="Ruta al archivo de audio"),
    text: str = typer.Option(..., "--text", "-t", help="Texto de referencia"),
    lang: str = typer.Option("es", "--lang", "-l", help="Idioma objetivo"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Salida en formato JSON (por defecto)"),
):
    """Compara el audio contra un texto de referencia y evalúa la pronunciación."""
    # TODO: Implementar lógica real llamando al Kernel
    stub_result = {
        "per": 0.0,
        "ops": [{"op": "eq", "ref": "o", "hyp": "o"}],
        "alignment": [["o", "o"]],
        "meta": {"backend": "stub"},
    }

    if json_output:
        typer.echo(json.dumps(stub_result, ensure_ascii=False))
    else:
        typer.echo(f"PER: {stub_result['per']}")


def main():
    """Punto de entrada para el script de consola."""
    app()


if __name__ == "__main__":
    main()