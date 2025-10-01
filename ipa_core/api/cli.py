"""Typer-based command line interface for the IPA core kernel."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ipa_core.kernel import Kernel, KernelConfig
from ipa_core.plugins import PLUGIN_GROUPS, list_plugins

app = typer.Typer(help="CLI del microkernel IPA")
plugins_app = typer.Typer(help="Gestión de plugins registrados")
app.add_typer(plugins_app, name="plugins")


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


@app.command(help="Ejecutar el pipeline principal (stub)")
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
        help="Directorio con los archivos de entrada a procesar",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validar configuración y listar archivos sin ejecutar el pipeline",
    ),
    show_config: bool = typer.Option(
        False,
        "--show-config",
        help="Mostrar la configuración efectiva cargada",
    ),
) -> None:
    cfg = KernelConfig.from_yaml(config)
    kernel = Kernel(cfg)

    if show_config:
        typer.echo("Configuración efectiva:")
        for key, value in cfg.to_mapping().items():
            typer.echo(f"- {key}: {value}")

    result = kernel.run(input, dry_run=dry_run)

    typer.echo(
        f"Pipeline stub ejecutado en '{result['input_dir']}' "
        f"({len(result['files'])} archivos, dry_run={result['dry_run']})"
    )

    if result["files"]:
        typer.echo("Archivos detectados:")
        for file_name in result["files"]:
            typer.echo(f"  - {file_name}")


@app.command(help="Mostrar plugins disponibles (alias rápido)")
def plugins() -> None:
    """Convenience alias matching la API anterior."""

    list_plugins_cmd()
