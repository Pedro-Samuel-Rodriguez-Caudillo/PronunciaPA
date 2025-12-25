"""CLI para interactuar con PronunciaPA.

Este módulo define los comandos de línea de comandos para transcripción
y comparación fonética.
"""
from __future__ import annotations
import json
from typing import Optional
import typer
from ipa_core.config import loader
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.types import AudioInput

app = typer.Typer(help="PronunciaPA: Reconocimiento y evaluación fonética")


def _get_kernel() -> Kernel:
    """Carga la configuración y crea el kernel."""
    import os
    config_path = os.environ.get("PRONUNCIAPA_CONFIG", "configs/local.yaml")
    # Si el archivo no existe y es el default, creamos uno mínimo para stubs
    if not os.path.exists(config_path) and config_path == "configs/local.yaml":
        return create_kernel(loader.AppConfig(
            version=1,
            preprocessor={"name": "default"},
            backend={"name": "stub"},
            textref={"name": "default"},
            comparator={"name": "default"}
        ))
    cfg = loader.load_config(config_path)
    return create_kernel(cfg)


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
    
    # Usamos el preprocesador y ASR del kernel para el stub de transcribe
    # En el futuro esto llamará a un método del kernel
    processed = kernel.pre.process_audio(audio_in)
    res = kernel.asr.transcribe(processed, lang=lang)

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
    
    res = kernel.run(audio=audio_in, text=text, lang=lang)

    if json_output:
        typer.echo(json.dumps(res, ensure_ascii=False))
    else:
        typer.echo(f"PER: {res['per']}")
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