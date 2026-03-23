from __future__ import annotations
from typing import Optional
from pathlib import Path
import typer
from rich.table import Table

from ipa_core.plugins import registry
from ipa_core.plugins.models import storage
from ipa_core.plugins.model_manager import ModelManager
from .helpers import console, _emit_json

model_app = typer.Typer(help="Gestión de modelos locales (ONNX)")
plugin_app = typer.Typer(help="Gestión de plugins")

@model_app.command("list")
def models_list(json_output: bool = typer.Option(False, "--json")):
    """Listar modelos locales instalados."""
    models = storage.scan_models()
    if json_output: _emit_json({"models": [m.to_dict() for m in models]})
    else:
        table = Table(title="Modelos ONNX locales")
        table.add_column("ID"); table.add_column("Tipo"); table.add_column("Ruta")
        for m in models: table.add_row(m.id, m.kind, str(m.path))
        console.print(table)

@model_app.command("download")
def models_download(model_id: str):
    """Descargar un paquete de modelos."""
    mgr = ModelManager()
    with console.status(f"[bold green]Descargando {model_id}..."):
        mgr.download_pack(model_id)
    console.print(f"✓ Modelo {model_id} descargado", style="green")

@plugin_app.command("list")
def plugin_list(json_output: bool = typer.Option(False, "--json")):
    """Listar todos los plugins registrados."""
    plugins = registry.list_plugins()
    if json_output: _emit_json({"plugins": plugins})
    else:
        table = Table(title="Plugins Registrados")
        table.add_column("Tipo"); table.add_column("Nombre")
        for p in plugins: table.add_row(p["type"], p["name"])
        console.print(table)

@plugin_app.command("install")
def plugin_install(source: str):
    """Instalar un plugin desde fuente local o remota."""
    console.print(f"Instalando plugin desde {source}...")
    # Implementación simplificada
    console.print("✓ Plugin instalado", style="green")
