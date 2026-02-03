#!/usr/bin/env python
"""CLI para gestión de modelos de PronunciaPA.

Uso:
    python -m ipa_core.cli.models list          # Ver todos los modelos
    python -m ipa_core.cli.models status        # Ver estado de instalación
    python -m ipa_core.cli.models install <id>  # Instalar un modelo
    python -m ipa_core.cli.models setup         # Setup rápido
    python -m ipa_core.cli.models setup --full  # Setup completo
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import List, Optional


def print_table(headers: List[str], rows: List[List[str]], widths: Optional[List[int]] = None) -> None:
    """Imprimir tabla formateada."""
    if not widths:
        widths = [max(len(str(row[i])) for row in [headers] + rows) + 2 for i in range(len(headers))]
    
    # Header
    header_line = "│".join(f" {h:<{w-1}}" for h, w in zip(headers, widths))
    separator = "┼".join("─" * w for w in widths)
    
    print("┌" + "┬".join("─" * w for w in widths) + "┐")
    print("│" + header_line + "│")
    print("├" + separator + "┤")
    
    # Rows
    for row in rows:
        row_line = "│".join(f" {str(cell):<{w-1}}" for cell, w in zip(row, widths))
        print("│" + row_line + "│")
    
    print("└" + "┴".join("─" * w for w in widths) + "┘")


def status_icon(status: str) -> str:
    """Convertir estado a icono."""
    icons = {
        "installed": "✅",
        "not_installed": "❌",
        "installing": "⏳",
        "error": "⚠️",
        "outdated": "🔄",
    }
    return icons.get(status, "❓")


async def cmd_list(args: argparse.Namespace) -> int:
    """Listar modelos disponibles."""
    from ipa_core.services.model_installer import MODEL_CATALOG, ModelCategory
    
    print("\n📦 Modelos disponibles en PronunciaPA\n")
    
    for category in ModelCategory:
        models = [m for m in MODEL_CATALOG.values() if m.category == category]
        if not models:
            continue
        
        print(f"\n{category.value.upper()}")
        print("=" * 60)
        
        for model in models:
            flags = []
            if model.is_required:
                flags.append("📌 Requerido")
            if model.is_recommended:
                flags.append("⭐ Recomendado")
            
            print(f"  {model.id}")
            print(f"    └─ {model.name}: {model.description}")
            print(f"       Tamaño: ~{model.size_mb}MB  {' | '.join(flags)}")
    
    print()
    return 0


async def cmd_status(args: argparse.Namespace) -> int:
    """Ver estado de instalación."""
    from ipa_core.services.model_installer import get_installer, ModelCategory
    
    print("\n🔍 Estado de instalación de modelos\n")
    
    installer = get_installer()
    models = await installer.get_all_status()
    
    # Agrupar por categoría
    for category in ModelCategory:
        cat_models = [m for m in models if m.category == category]
        if not cat_models:
            continue
        
        print(f"\n{category.value.upper()}")
        
        headers = ["Modelo", "Estado", "Notas"]
        rows = []
        
        for model in cat_models:
            notes = []
            if model.is_required:
                notes.append("requerido")
            if model.is_recommended:
                notes.append("recomendado")
            if model.error:
                notes.append(f"error: {model.error[:30]}...")
            
            rows.append([
                model.id,
                f"{status_icon(model.status.value)} {model.status.value}",
                ", ".join(notes) if notes else "-",
            ])
        
        print_table(headers, rows, [20, 18, 35])
    
    # Resumen
    total = len(models)
    installed = sum(1 for m in models if m.status.value == "installed")
    required_missing = [m.id for m in models if m.is_required and m.status.value != "installed"]
    
    print(f"\n📊 Resumen: {installed}/{total} instalados")
    
    if required_missing:
        print(f"⚠️  Faltan modelos requeridos: {', '.join(required_missing)}")
        print("   Ejecuta: python -m ipa_core.cli.models setup")
    else:
        print("✅ Todos los modelos requeridos están instalados")
    
    print()
    return 0


async def cmd_install(args: argparse.Namespace) -> int:
    """Instalar un modelo específico."""
    from ipa_core.services.model_installer import get_installer, MODEL_CATALOG
    
    model_id = args.model_id
    
    if model_id not in MODEL_CATALOG:
        print(f"❌ Modelo no encontrado: {model_id}")
        print(f"   Modelos disponibles: {', '.join(MODEL_CATALOG.keys())}")
        return 1
    
    model = MODEL_CATALOG[model_id]
    print(f"\n📦 Instalando {model.name}...")
    print(f"   {model.description}")
    print(f"   Tamaño aproximado: ~{model.size_mb}MB\n")
    
    def on_progress(mid: str, progress: float, message: str) -> None:
        bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
        print(f"\r   [{bar}] {progress:.0f}% {message}", end="", flush=True)
    
    installer = get_installer()
    installer._on_progress = on_progress
    
    try:
        result = await installer.install(model_id)
        print(f"\n\n✅ {model.name} instalado correctamente")
        return 0
    except Exception as e:
        print(f"\n\n❌ Error instalando {model_id}: {e}")
        return 1


async def cmd_setup(args: argparse.Namespace) -> int:
    """Setup rápido o completo."""
    from ipa_core.services.model_installer import get_installer
    
    installer = get_installer()
    
    if args.full:
        print("\n🚀 Setup completo - Instalando modelos recomendados...\n")
        results = await installer.install_recommended()
    else:
        print("\n⚡ Setup rápido - Instalando modelos requeridos...\n")
        results = await installer.install_required()
    
    # Mostrar resultados
    installed = [r for r in results if r.status.value == "installed"]
    errors = [r for r in results if r.status.value == "error"]
    
    if installed:
        print("\n✅ Instalados correctamente:")
        for r in installed:
            print(f"   • {r.name}")
    
    if errors:
        print("\n⚠️  Errores durante la instalación:")
        for r in errors:
            print(f"   • {r.name}: {r.error}")
    
    # Quick setup adicional (Python packages)
    print("\n📦 Verificando paquetes Python...")
    from ipa_core.services.model_installer import quick_setup
    py_result = await quick_setup()
    
    for component, status in py_result.items():
        icon = "✅" if status in ("installed", "already_installed") else "❌"
        print(f"   {icon} {component}: {status}")
    
    print("\n🎉 Setup completado!")
    print("   Ejecuta 'python -m ipa_core.cli.models status' para verificar.\n")
    
    return 0 if not errors else 1


async def cmd_quick_setup(args: argparse.Namespace) -> int:
    """Setup instantáneo - solo Python packages."""
    from ipa_core.services.model_installer import quick_setup
    
    print("\n⚡ Quick Setup - Instalando dependencias Python...\n")
    
    result = await quick_setup()
    
    for component, status in result.items():
        icon = "✅" if status in ("installed", "already_installed") else "❌"
        print(f"   {icon} {component}: {status}")
    
    print()
    return 0


async def cmd_asr_engines(args: argparse.Namespace) -> int:
    """Listar y gestionar motores ASR con salida IPA."""
    from ipa_core.backends.unified_ipa_backend import UnifiedIPABackend, ASREngine
    from ipa_core.config import loader
    
    print("\n🎤 Motores ASR con salida IPA directa\n")
    
    # Obtener engine actual de config
    try:
        cfg = loader.load_config()
        backend_params = cfg.backend.params if cfg.backend.params else {}
        current_engine = backend_params.get("engine", "allosaurus")
    except Exception:
        current_engine = "allosaurus"
    
    engines_info = {
        "allosaurus": {
            "name": "Allosaurus (Universal IPA)",
            "desc": "ASR universal con 200+ idiomas. Ligero (~500MB), funciona bien en CPU.",
            "pros": ["Fácil de instalar", "Bajo consumo", "Muchos idiomas"],
            "cons": ["Precisión moderada"],
        },
        "wav2vec2-ipa": {
            "name": "Wav2Vec2 Large IPA",
            "desc": "Alta precisión fonética. Modelo grande (~1.2GB).",
            "pros": ["Alta precisión", "Entrenado para IPA"],
            "cons": ["Requiere GPU para velocidad", "Mayor memoria"],
        },
        "xlsr-ipa": {
            "name": "XLS-R 300M IPA (Multilingüe)",
            "desc": "Multilingüe (128 idiomas). Buen balance precisión/velocidad.",
            "pros": ["Buen balance", "Multilingüe", "IPA directo"],
            "cons": ["Requiere torch/transformers"],
        },
    }
    
    for engine in ASREngine:
        status = UnifiedIPABackend.check_engine_ready(engine)
        info = engines_info.get(engine.value, {})
        
        # Indicador de activo
        active = "→ " if engine.value == current_engine else "  "
        icon = "✅" if status["ready"] else "❌"
        
        print(f"{active}{icon} {engine.value}")
        print(f"      {info.get('name', engine.value)}")
        print(f"      {info.get('desc', '')}")
        
        if status["missing"]:
            print(f"      ⚠️  Falta: {', '.join(status['missing'])}")
            print(f"         pip install {' '.join(status['missing'])}")
        
        print()
    
    print(f"🔧 Engine actual: {current_engine}")
    print(f"   Para cambiar, edita configs/local.yaml:")
    print(f"   backend:")
    print(f"     name: unified_ipa")
    print(f"     params:")
    print(f"       engine: <allosaurus|wav2vec2-ipa|xlsr-ipa>")
    print()
    
    return 0


async def cmd_asr_install(args: argparse.Namespace) -> int:
    """Instalar dependencias para un motor ASR."""
    from ipa_core.services.model_installer import get_installer
    
    engine_id = args.engine_id
    
    # Mapear engine a modelos
    engine_to_models = {
        "allosaurus": ["allosaurus"],
        "wav2vec2-ipa": ["torch", "transformers", "wav2vec2-ipa"],
        "xlsr-ipa": ["torch", "transformers", "xlsr-ipa"],
    }
    
    if engine_id not in engine_to_models:
        print(f"❌ Engine no válido: {engine_id}")
        print(f"   Opciones: {', '.join(engine_to_models.keys())}")
        return 1
    
    models = engine_to_models[engine_id]
    print(f"\n📦 Instalando dependencias para {engine_id}...\n")
    
    installer = get_installer()
    errors = []
    
    for model_id in models:
        print(f"   ⏳ Instalando {model_id}...")
        try:
            result = await installer.install(model_id)
            print(f"   ✅ {model_id} instalado")
        except Exception as e:
            print(f"   ❌ Error en {model_id}: {e}")
            errors.append(model_id)
    
    if not errors:
        print(f"\n✅ Engine {engine_id} listo para usar!")
        print(f"   Configura en local.yaml: backend.params.engine: {engine_id}")
    else:
        print(f"\n⚠️  Algunos componentes fallaron: {', '.join(errors)}")
    
    print()
    return 0 if not errors else 1


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Gestión de modelos de PronunciaPA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # list
    list_parser = subparsers.add_parser("list", help="Listar modelos disponibles")
    
    # status
    status_parser = subparsers.add_parser("status", help="Ver estado de instalación")
    
    # install
    install_parser = subparsers.add_parser("install", help="Instalar un modelo")
    install_parser.add_argument("model_id", help="ID del modelo a instalar")
    
    # setup
    setup_parser = subparsers.add_parser("setup", help="Setup automático")
    setup_parser.add_argument("--full", action="store_true", help="Instalar todos los recomendados")
    
    # quick
    quick_parser = subparsers.add_parser("quick", help="Setup rápido (solo Python packages)")
    
    # asr - gestión de engines ASR
    asr_parser = subparsers.add_parser("asr", help="Gestionar motores ASR")
    
    # asr-install - instalar dependencias de un engine
    asr_install_parser = subparsers.add_parser("asr-install", help="Instalar dependencias de un engine ASR")
    asr_install_parser.add_argument("engine_id", help="ID del engine: allosaurus, wav2vec2-ipa, xlsr-ipa")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Mapear comandos a funciones
    commands = {
        "list": cmd_list,
        "status": cmd_status,
        "install": cmd_install,
        "setup": cmd_setup,
        "quick": cmd_quick_setup,
        "asr": cmd_asr_engines,
        "asr-install": cmd_asr_install,
    }
    
    cmd_func = commands.get(args.command)
    if not cmd_func:
        parser.print_help()
        return 1
    
    return asyncio.run(cmd_func(args))


if __name__ == "__main__":
    sys.exit(main())
