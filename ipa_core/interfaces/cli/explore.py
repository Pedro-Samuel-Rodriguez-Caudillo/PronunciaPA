from __future__ import annotations
import asyncio
from typing import Optional
import typer
from rich.table import Table

from ipa_core.ipa_catalog import load_catalog, list_sounds, resolve_sound_entry
from .helpers import (
    console, CatalogOutput, _prompt_lang, _prompt_sound, _emit_json,
    _sound_payload, _normalize_context, _position_label
)

def ipa_list_sounds(
    lang: Optional[str] = typer.Option(None, "--lang", "-l"),
    output: CatalogOutput = typer.Option(CatalogOutput.human, "--output", "-o"),
):
    """Listar todos los sonidos disponibles para un idioma."""
    lang_key = _prompt_lang(lang)
    try:
        sounds = list_sounds(lang_key)
    except FileNotFoundError as exc:
        console.print(f"Error: {exc}", style="red"); raise typer.Exit(1)

    if output == CatalogOutput.json:
        _emit_json({"language": lang_key, "total": len(sounds), "sounds": sounds})
    else:
        table = Table(title=f"Sonidos disponibles ({lang_key})")
        table.add_column("IPA", style="cyan"); table.add_column("Nombre", style="green")
        for s in sounds: table.add_row(s.get("ipa", ""), s.get("common_name", ""))
        console.print(table)

def ipa_explore(
    lang: Optional[str] = typer.Option(None, "--lang", "-l"),
    sound: Optional[str] = typer.Option(None, "--sound", "-s"),
    output: CatalogOutput = typer.Option(CatalogOutput.human, "--output", "-o"),
):
    """Explorar detalles de un sonido específico."""
    lang_key = _prompt_lang(lang)
    catalog = load_catalog(lang_key)
    sound_q = _prompt_sound(sound, catalog)
    
    entry = resolve_sound_entry(catalog, sound_q)
    if not entry:
        console.print(f"Error: sonido no encontrado: {sound_q}", style="red"); raise typer.Exit(1)

    if output == CatalogOutput.json:
        _emit_json({"language": lang_key, "sound": entry})
    else:
        _print_explore_human(entry)

def _print_explore_human(entry: dict):
    console.print(f"Detalles de [bold cyan]/{entry.get('ipa')}/[/bold cyan] ({entry.get('common_name')})", style="bold")
    if entry.get("description"): console.print(f"\n{entry['description']}")
    
    _print_contexts_table(entry.get("contexts", {}))
    _print_minimal_pairs_table(entry.get("minimal_pairs", []))

def _print_contexts_table(contexts: dict):
    if not contexts: return
    table = Table(title="Contextos y Ejemplos")
    table.add_column("Posición", style="magenta"); table.add_column("Ejemplos", style="green")
    for pos, data in contexts.items():
        seeds = ", ".join([s.get("text", "") for s in data.get("seeds", []) if isinstance(s, dict)])
        table.add_row(_position_label(_normalize_context(pos)), seeds)
    console.print(table)

def _print_minimal_pairs_table(pairs: list):
    if not pairs: return
    table = Table(title="Pares Mínimos")
    table.add_column("Palabra A", style="green"); table.add_column("IPA A", style="dim")
    table.add_column("Palabra B", style="cyan"); table.add_column("IPA B", style="dim")
    for p in pairs:
        if isinstance(p, list) and len(p) >= 4:
            table.add_row(p[1], p[0], p[3], p[2])
    console.print(table)
