"""Typer-based command line interface for the IPA core kernel."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Optional

import typer

from ipa_core.kernel import Kernel, KernelConfig
from ipa_core.plugins import PLUGIN_GROUPS, list_plugins

app = typer.Typer(help="CLI del microkernel IPA")
plugins_app = typer.Typer(help="Gestión de plugins registrados")
app.add_typer(plugins_app, name="plugins")

logger = logging.getLogger(__name__)


def _echo_plugins(group_key: str) -> None:
    group = PLUGIN_GROUPS[group_key]
    names = list_plugins(group.entrypoint_group)
    if names:
        typer.echo(f"{group.name}: {', '.join(names)}")
    else:
        typer.echo(f"{group.name}: (sin plugins registrados)")


@plugins_app.command("list", help="Listar plugins instalados")
def list_plugins_cmd(
    group: Optional[str] = typer.Option(
        None,
        "--group",
        "-g",
        help="Filtrar por grupo (asr, textref, comparator, preprocessor)",
    )
) -> None:
    if group:
        group_key = group.lower()
        if group_key not in PLUGIN_GROUPS:
            raise typer.BadParameter(
                f"Grupo desconocido '{group}'. Valores válidos: {', '.join(PLUGIN_GROUPS)}"
            )
        _echo_plugins(group_key)
        return

    for group_key in PLUGIN_GROUPS:
        _echo_plugins(group_key)


@app.command(help="Ejecutar el pipeline principal")
def run(
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Ruta al archivo YAML de configuración del kernel",
    ),
    input: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Archivo CSV con metadata de los audios y textos de referencia",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directorio donde se almacenarán los reportes generados",
    ),
    show_config: bool = typer.Option(
        False,
        "--show-config",
        help="Mostrar la configuración efectiva cargada",
    ),
) -> None:
    logging.basicConfig(level=logging.INFO)

    try:
        cfg = KernelConfig.from_yaml(config)
    except Exception as exc:  # pragma: no cover - errores de configuración
        typer.secho(f"Error al cargar configuración: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    kernel = Kernel(cfg)

    if show_config:
        typer.echo("Configuración efectiva:")
        for key, value in cfg.to_mapping().items():
            typer.echo(f"- {key}: {value}")

    try:
        report = kernel.run(input)
    except Exception as exc:  # pragma: no cover - propagación controlada
        logger.exception("Error al ejecutar el kernel")
        typer.secho(f"Error al ejecutar el pipeline: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "report.json"
    csv_path = output / "report.csv"

    _write_json(json_path, report)
    _write_csv(csv_path, report.get("detalles", []))

    typer.echo(f"Reporte JSON generado en: {json_path}")
    typer.echo(f"Reporte CSV generado en: {csv_path}")
    summary = report.get("summary", {})
    typer.echo(
        "Resumen: {procesados} procesados, {con_error} con error, PER global={per:.4f}".format(
            procesados=summary.get("procesados", 0),
            con_error=summary.get("con_error", 0),
            per=report.get("per_global", 0.0),
        )
    )


@app.command(help="Mostrar plugins disponibles (alias rápido)")
def plugins() -> None:
    """Convenience alias matching la API anterior."""

    list_plugins_cmd()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, details: list[dict]) -> None:
    fieldnames = [
        "index",
        "audio_path",
        "text",
        "lang",
        "ref_ipa",
        "hyp_ipa",
        "per",
        "matches",
        "substitutions",
        "insertions",
        "deletions",
        "total_ref_tokens",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in details:
            serialised = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(serialised)
