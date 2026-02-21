#!/usr/bin/env python3
"""Script de configuración offline para PronunciaPA.

Flujo
-----
1. Detectar RAM disponible → recomendar tier de modelo LLM.
2. Mostrar tabla con requisitos y pedir confirmación.
3. Descargar modelo GGUF + Piper TTS + verificar eSpeak.
4. Probar el stack completo con una frase de prueba.

Uso
---
    python scripts/offline_setup.py
    python scripts/offline_setup.py --tier 3B
    python scripts/offline_setup.py --skip-llm       # solo TTS + eSpeak
    python scripts/offline_setup.py --dry-run        # sin descargar nada
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

# Asegurar que ipa_core se pueda importar desde el directorio raíz
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Imports internos (con carga diferida para evitar errores si no instalado)
# ---------------------------------------------------------------------------

def _import_model_selector():
    try:
        from ipa_core.llm.model_selector import (
            recommend_model,
            get_available_ram_gb,
            get_total_ram_gb,
            select_tier,
            get_runtime_config,
            print_tier_table,
            _TIERS,
            _STUB_TIER,
        )
        return {
            "recommend_model": recommend_model,
            "get_available_ram_gb": get_available_ram_gb,
            "get_total_ram_gb": get_total_ram_gb,
            "select_tier": select_tier,
            "get_runtime_config": get_runtime_config,
            "print_tier_table": print_tier_table,
            "_TIERS": _TIERS,
            "_STUB_TIER": _STUB_TIER,
        }
    except ImportError as e:
        print(f"[ERROR] No se pudo importar ipa_core: {e}")
        print("  Asegúrate de haber instalado el paquete: pip install -e '.'")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Constantes de URLs de descarga
# ---------------------------------------------------------------------------

# Modelos GGUF en Hugging Face (versiones open, cuantizadas Q4_K_M)
MODEL_URLS: dict[str, str] = {
    "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf": (
        "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/"
        "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    ),
    "phi-3-mini-4k-instruct-q4.gguf": (
        "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/"
        "Phi-3-mini-4k-instruct-q4.gguf"
    ),
    "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf": (
        "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/"
        "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    ),
}

# Voz Piper para es-MX
PIPER_VOICE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "es/es_MX/onnx/es_MX-claude-medium.onnx"
)
PIPER_VOICE_CONFIG_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "es/es_MX/onnx/es_MX-claude-medium.onnx.json"
)

MODELS_DIR = ROOT / "data" / "models"
VOICES_DIR = ROOT / "data" / "voices"


# ---------------------------------------------------------------------------
# Helpers de descarga
# ---------------------------------------------------------------------------

def _download_file(url: str, dest: Path, *, dry_run: bool = False) -> bool:
    """Descargar un archivo con barra de progreso simple.

    Retorna True si la descarga fue exitosa (o si dry_run=True).
    """
    if dry_run:
        print(f"  [dry-run] Descargaría: {url}")
        print(f"            → {dest}")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  [OK] Ya existe: {dest.name}")
        return True

    print(f"  Descargando {dest.name} ...")
    try:
        req = Request(url, headers={"User-Agent": "PronunciaPA-setup/1.0"})
        with urlopen(req, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 256  # 256 KB

            with open(dest, "wb") as fh:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        bar = "=" * int(pct / 2) + " " * (50 - int(pct / 2))
                        print(f"\r  [{bar}] {pct:5.1f}%", end="", flush=True)

        print(f"\r  [{('=' * 50)}] 100.0%")
        print(f"  [OK] {dest.name} descargado ({downloaded / 1024 / 1024:.1f} MB)")
        return True

    except URLError as e:
        print(f"\n  [ERROR] No se pudo descargar {url}: {e}")
        if dest.exists():
            dest.unlink()
        return False
    except KeyboardInterrupt:
        print("\n  Descarga cancelada por el usuario.")
        if dest.exists():
            dest.unlink()
        return False


# ---------------------------------------------------------------------------
# Verificación de eSpeak
# ---------------------------------------------------------------------------

def _check_espeak() -> bool:
    """Verificar que eSpeak-NG esté instalado y accesible."""
    print("\n--- Verificando eSpeak-NG ---")
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if binary:
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_line = result.stdout.strip() or result.stderr.strip()
            print(f"  [OK] {binary}: {version_line[:60]}")
            return True
        except (subprocess.TimeoutExpired, OSError):
            pass

    print("  [WARN] eSpeak-NG no encontrado.")
    print("  Instala con:")
    if sys.platform.startswith("linux"):
        print("    sudo apt install espeak-ng   # Debian/Ubuntu")
        print("    sudo dnf install espeak-ng   # Fedora")
    elif sys.platform == "darwin":
        print("    brew install espeak-ng")
    else:
        print("    https://github.com/espeak-ng/espeak-ng/releases")
    return False


# ---------------------------------------------------------------------------
# Verificación de Piper
# ---------------------------------------------------------------------------

def _check_piper() -> bool:
    """Verificar que el binario piper esté disponible."""
    binary = shutil.which("piper")
    if binary:
        print(f"  [OK] piper encontrado: {binary}")
        return True
    print("  [WARN] piper no encontrado en PATH.")
    print("  Descarga el binario desde: https://github.com/rhasspy/piper/releases")
    return False


# ---------------------------------------------------------------------------
# Prueba del stack completo
# ---------------------------------------------------------------------------

def _smoke_test(model_path: Optional[Path] = None) -> bool:
    """Probar el stack completo con una frase de prueba."""
    print("\n--- Prueba del stack completo ---")

    # Test 1: importar ipa_core
    try:
        import ipa_core  # noqa: F401
        print("  [OK] ipa_core importado correctamente")
    except ImportError as e:
        print(f"  [ERROR] No se pudo importar ipa_core: {e}")
        return False

    # Test 2: eSpeak G2P
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if binary:
        try:
            result = subprocess.run(
                [binary, "-q", "-v", "es", "--ipa=3", "hola mundo"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            ipa_output = result.stdout.strip()
            if ipa_output:
                print(f"  [OK] eSpeak G2P: 'hola mundo' → {ipa_output!r}")
            else:
                print("  [WARN] eSpeak no produjo salida IPA")
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"  [WARN] eSpeak falló: {e}")

    # Test 3: léxico inline del pack
    try:
        import yaml  # type: ignore[import]
        pack_path = ROOT / "configs" / "ipa" / "pack_es-mx.yaml"
        if pack_path.exists():
            with open(pack_path, encoding="utf-8") as fh:
                pack_data = yaml.safe_load(fh)
            lexicon = pack_data.get("inline_lexicon", {})
            sample = {k: lexicon[k] for k in list(lexicon)[:3]}
            print(f"  [OK] Léxico inline cargado ({len(lexicon)} entradas). Muestra: {sample}")
        else:
            print("  [WARN] pack_es-mx.yaml no encontrado")
    except ImportError:
        print("  [WARN] PyYAML no instalado; saltando test de léxico")
    except Exception as e:
        print(f"  [WARN] Error cargando léxico: {e}")

    # Test 4: modelo LLM (si se proporcionó)
    if model_path and model_path.exists():
        llama_bin = shutil.which("llama-cli") or shutil.which("llama.cpp")
        if llama_bin:
            try:
                result = subprocess.run(
                    [
                        llama_bin,
                        "-m", str(model_path),
                        "-p", "Di hola en español:",
                        "-n", "20",
                        "--temp", "0.1",
                        "-q",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                output = result.stdout.strip()[:80]
                print(f"  [OK] Modelo LLM respondió: {output!r}")
            except (subprocess.TimeoutExpired, OSError) as e:
                print(f"  [WARN] Test LLM falló: {e}")
        else:
            print("  [INFO] llama-cli no encontrado; saltando test de LLM")

    print("\n  Stack verificado. PronunciaPA listo para uso offline.")
    return True


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configuración offline de PronunciaPA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tier",
        choices=["stub", "1B", "3B", "7B"],
        default=None,
        help="Forzar un tier de modelo en lugar de la detección automática",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Saltar la descarga del modelo LLM",
    )
    parser.add_argument(
        "--skip-piper",
        action="store_true",
        help="Saltar la descarga de la voz Piper",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar qué se descargaría sin descargar nada",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="No pedir confirmación; usar la recomendación automática",
    )
    args = parser.parse_args()

    ms = _import_model_selector()

    print("\n" + "=" * 70)
    print("  PronunciaPA — Configuración Offline")
    print("=" * 70)

    # ---- Selección de tier ----
    available_ram = ms["get_available_ram_gb"]()
    total_ram = ms["get_total_ram_gb"]()
    print(f"\n  RAM total: {total_ram:.1f} GB  |  RAM disponible: {available_ram:.1f} GB")

    if args.tier:
        tier_map = {t.name: t for t in ms["_TIERS"]}
        tier_map["stub"] = ms["_STUB_TIER"]
        selected = tier_map.get(args.tier, ms["_STUB_TIER"])
        print(f"\n  Tier forzado por argumento: {selected.name}")
    elif args.no_interactive:
        selected = ms["select_tier"](available_ram)
        ms["print_tier_table"](available_ram, selected)
    else:
        selected = ms["recommend_model"](interactive=True)

    print(f"\n  Tier seleccionado: {selected.name}")

    success = True

    # ---- Descargar modelo LLM ----
    model_path: Optional[Path] = None
    if not args.skip_llm and selected.name != "stub":
        print("\n--- Descarga del modelo LLM ---")
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        model_filename = selected.suggested_models[0]
        model_url = MODEL_URLS.get(model_filename)

        if model_url:
            model_path = MODELS_DIR / model_filename
            ok = _download_file(model_url, model_path, dry_run=args.dry_run)
            if not ok:
                print("  [WARN] Descarga del modelo falló. El sistema usará stub LLM.")
                success = False
        else:
            print(f"  [WARN] URL no configurada para {model_filename}")
            print(f"  Descarga manualmente y coloca en: {MODELS_DIR}/")
    elif args.skip_llm:
        print("\n  [INFO] Descarga LLM omitida (--skip-llm)")
    else:
        print("\n  [INFO] Tier stub seleccionado — sin descarga de modelo LLM")

    # ---- Descargar voz Piper ----
    if not args.skip_piper:
        print("\n--- Descarga de voz Piper (es-MX) ---")
        VOICES_DIR.mkdir(parents=True, exist_ok=True)

        voice_file = VOICES_DIR / "es_MX-claude-medium.onnx"
        voice_config = VOICES_DIR / "es_MX-claude-medium.onnx.json"

        ok1 = _download_file(PIPER_VOICE_URL, voice_file, dry_run=args.dry_run)
        ok2 = _download_file(PIPER_VOICE_CONFIG_URL, voice_config, dry_run=args.dry_run)

        if not (ok1 and ok2):
            print("  [WARN] Descarga de voz Piper falló. TTS puede no estar disponible.")
            success = False
    else:
        print("\n  [INFO] Descarga de Piper omitida (--skip-piper)")

    # ---- Verificar herramientas del sistema ----
    print("\n--- Verificando herramientas del sistema ---")
    espeak_ok = _check_espeak()
    piper_ok = _check_piper()

    if not espeak_ok:
        print("\n  [WARN] eSpeak es necesario para el fallback G2P offline.")
        success = False

    # ---- Prueba del stack ----
    _smoke_test(model_path)

    # ---- Resumen ----
    print("\n" + "=" * 70)
    print("  RESUMEN DE CONFIGURACIÓN")
    print("=" * 70)
    runtime = ms["get_runtime_config"](selected)
    print(f"  Tier LLM:       {selected.name}")
    print(f"  Runtime:        {runtime.get('kind', 'stub')}")
    if model_path:
        print(f"  Modelo:         {model_path}")
    print(f"  eSpeak:         {'OK' if espeak_ok else 'NO ENCONTRADO'}")
    print(f"  Piper binario:  {'OK' if piper_ok else 'NO ENCONTRADO'}")
    print(f"  Léxico es-MX:   configs/ipa/pack_es-mx.yaml")

    if success:
        print("\n  [OK] Configuración offline completada exitosamente.")
        print("  Inicia el servidor con:")
        print("    PRONUNCIAPA_ASR=stub PRONUNCIAPA_TEXTREF=grapheme \\")
        print("    uvicorn ipa_server.main:get_app --reload --port 8000")
    else:
        print("\n  [WARN] Configuración completada con advertencias.")
        print("  Algunas funciones pueden no estar disponibles.")

    print("=" * 70)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
