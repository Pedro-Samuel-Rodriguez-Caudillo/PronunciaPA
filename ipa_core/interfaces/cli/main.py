from __future__ import annotations
import asyncio
from typing import Optional
from pathlib import Path
import typer
from rich.console import Console

from ipa_core.config import loader
from ipa_core.plugins.models import storage
from .helpers import console, _emit_json
from .practice import ipa_practice
from .explore import ipa_explore, ipa_list_sounds
from .compare import compare, transcribe, feedback
from .plugins import model_app, plugin_app

app = typer.Typer(help="PronunciaPA: Reconocimiento y evaluación fonética")
config_app = typer.Typer(help="Gestión de configuración")

app.add_typer(config_app, name="config")
app.add_typer(plugin_app, name="plugin")
app.add_typer(model_app, name="models")

ipa_app = typer.Typer(help="Explorador y práctica de sonidos IPA")
app.add_typer(ipa_app, name="ipa")

ipa_app.command("practice")(ipa_practice)
ipa_app.command("explore")(ipa_explore)
ipa_app.command("list-sounds")(ipa_list_sounds)

app.command("compare")(compare)
app.command("transcribe")(transcribe)
app.command("feedback")(feedback)

@app.command()
def health(
    config: Optional[Path] = typer.Option(None, "--config", help="Ruta al archivo de configuración"),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON"),
):
    """🏥 Verificar estado del sistema y componentes."""
    from rich.panel import Panel
    from rich import box
    
    def check_config():
        try:
            cfg = loader.load_config(str(config) if config else None)
            return ("✓", "green", f"v{cfg.version}")
        except Exception as e: return ("✗", "red", str(e)[:40])
    
    def check_plugins():
        try:
            from ipa_core.plugins import registry
            return ("✓", "green", "Cargados")
        except Exception: return ("✗", "red", "Error")
    
    def check_models():
        try:
            models = storage.scan_models()
            return ("✓", "green", f"{len(models)} instalados") if models else ("⚠", "yellow", "Sin modelos")
        except Exception: return ("✗", "red", "Error")
    
    items = [("Config", check_config), ("Plugins", check_plugins), ("Models", check_models)]
    if json_output:
        _emit_json({k.lower(): {"status": f()[0], "msg": f()[2]} for k, f in items})
    else:
        from rich.table import Table
        table = Table(box=box.ROUNDED)
        table.add_column("Componente"); table.add_column("Estado"); table.add_column("Detalles")
        for k, f in items:
            s, c, d = f()
            table.add_row(k, f"[{c}]{s}[/{c}]", d)
        console.print(Panel(table, title="PronunciaPA Health Check", expand=False))

@app.command()
def interactive():
    """🎮 Iniciar sesión interactiva (TUI)."""
    from ipa_core.interfaces.interactive import run_interactive_session
    asyncio.run(run_interactive_session())

def main():
    app()

if __name__ == "__main__":
    main()
