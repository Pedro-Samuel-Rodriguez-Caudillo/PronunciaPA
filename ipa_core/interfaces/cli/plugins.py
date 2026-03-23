from __future__ import annotations
from typing import Optional
from pathlib import Path
import typer
from rich.table import Table

from ipa_core.plugins import registry
from ipa_core.plugins.models import storage
from ipa_core.plugins.model_manager import ModelManager
from ipa_core.plugins.manager import PluginManager
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
    """Listar todos los plugins registrados (internos y externos)."""
    # Core registered plugins
    core_plugins = registry.list_plugins()
    
    # External installed plugins via PluginManager
    pm = PluginManager()
    external_plugins = pm.get_installed_plugins()
    
    if json_output: 
        _emit_json({
            "core_plugins": core_plugins,
            "external_plugins": [p.__dict__ for p in external_plugins]
        })
    else:
        table = Table(title="Plugins del Sistema (Core)")
        table.add_column("Categoría", style="cyan")
        table.add_column("Nombre", style="green")
        for p in core_plugins:
            table.add_row(p["type"], p["name"])
        console.print(table)
        
        if external_plugins:
            ext_table = Table(title="Plugins Instalados (Extensiones)")
            ext_table.add_column("Categoría", style="cyan")
            ext_table.add_column("Nombre", style="green")
            ext_table.add_column("Versión")
            for p in external_plugins:
                ext_table.add_row(p.category, p.name, p.version)
            console.print(ext_table)

@plugin_app.command("install")
def plugin_install(source: str):
    """Instalar un plugin desde fuente local o remota (pip)."""
    pm = PluginManager()
    with console.status(f"[bold green]Instalando plugin desde {source}..."):
        try:
            pm.install_plugin(source)
            console.print("✓ Plugin instalado exitosamente.", style="green")
        except Exception as e:
            console.print(f"✗ Error instalando plugin: {e}", style="red")
            raise typer.Exit(1)

@plugin_app.command("info")
def plugin_info(category: str, name: str):
    """Muestra información detallada de un plugin externo."""
    pm = PluginManager()
    info = pm.get_plugin_info(category, name)
    
    if not info:
        console.print(f"[yellow]No se encontró información extendida para el plugin '{name}' en la categoría '{category}'. Puede ser un plugin core interno.[/yellow]")
        raise typer.Exit(1)
        
    table = Table(title=f"Plugin: {name} ({category})")
    table.add_column("Propiedad", style="cyan")
    table.add_column("Valor")
    table.add_row("Nombre", info.name)
    table.add_row("Categoría", info.category)
    table.add_row("Versión", info.version)
    table.add_row("Autor", info.author)
    table.add_row("Descripción", info.description)
    table.add_row("Entry Point", info.entry_point)
    table.add_row("Habilitado", "Sí" if info.enabled else "No")
    
    console.print(table)

