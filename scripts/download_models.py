"""Script para descargar todos los modelos requeridos.

Modelos:
- Allosaurus uni2005 (ASR → IPA)
- Wav2Vec2 XLSR-53-IPA (ASR alta calidad)
- TinyLlama 1.1B (LLM ejercicios - principal)
- Phi-3 mini (LLM opcional)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MODELS_DIR = Path(__file__).parent.parent / "data" / "models"


def install_package(package: str) -> None:
    """Instalar paquete si no está disponible."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def download_allosaurus() -> None:
    """Descargar modelo Allosaurus uni2005."""
    print("\n=== Descargando Allosaurus uni2005 ===")
    try:
        from allosaurus.app import read_recognizer
        model = read_recognizer("uni2005")
        print("✅ Allosaurus uni2005 descargado")
    except ImportError:
        print("Instalando allosaurus...")
        install_package("allosaurus")
        from allosaurus.app import read_recognizer
        model = read_recognizer("uni2005")
        print("✅ Allosaurus uni2005 descargado")


def download_wav2vec2_ipa() -> None:
    """Descargar Wav2Vec2 XLSR-53-IPA."""
    print("\n=== Descargando Wav2Vec2 XLSR-53-IPA ===")
    try:
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    except ImportError:
        print("Instalando transformers y torch...")
        install_package("transformers")
        install_package("torch")
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    
    MODEL = "facebook/wav2vec2-large-xlsr-53-ipa"
    print(f"Descargando {MODEL}...")
    Wav2Vec2Processor.from_pretrained(MODEL)
    Wav2Vec2ForCTC.from_pretrained(MODEL)
    print("✅ Wav2Vec2 XLSR-53-IPA descargado")


def download_tinyllama() -> None:
    """Descargar TinyLlama via Ollama."""
    print("\n=== Descargando TinyLlama 1.1B ===")
    try:
        result = subprocess.run(
            ["ollama", "pull", "tinyllama"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✅ TinyLlama descargado via Ollama")
    except FileNotFoundError:
        print("❌ Ollama no instalado. Instala desde: https://ollama.ai")
        print("   Luego ejecuta: ollama pull tinyllama")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error descargando TinyLlama: {e}")


def download_phi3_optional() -> None:
    """Descargar Phi-3 mini (opcional)."""
    print("\n=== Descargando Phi-3 Mini (opcional) ===")
    try:
        result = subprocess.run(
            ["ollama", "pull", "phi3:mini"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✅ Phi-3 Mini descargado via Ollama")
    except FileNotFoundError:
        print("⚠️ Ollama no instalado - saltando Phi-3")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error descargando Phi-3: {e}")


def verify_espeak() -> None:
    """Verificar que eSpeak está instalado."""
    print("\n=== Verificando eSpeak NG ===")
    try:
        result = subprocess.run(
            ["espeak-ng", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"✅ eSpeak NG instalado: {result.stdout.strip()}")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print("❌ eSpeak NG no instalado")
        print("   Windows: https://github.com/espeak-ng/espeak-ng/releases")
        print("   Linux: sudo apt install espeak-ng")
        print("   Mac: brew install espeak")


def main(include_optional: bool = False) -> None:
    """Descargar todos los modelos."""
    print("=" * 50)
    print("DESCARGA DE MODELOS - PronunciaPA")
    print("=" * 50)
    
    # Crear directorio
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Modelos principales
    download_allosaurus()
    download_wav2vec2_ipa()
    verify_espeak()
    download_tinyllama()
    
    # Opcional
    if include_optional:
        download_phi3_optional()
    
    print("\n" + "=" * 50)
    print("DESCARGA COMPLETADA")
    print("=" * 50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-phi3", action="store_true", help="Incluir Phi-3 (opcional)")
    args = parser.parse_args()
    main(include_optional=args.with_phi3)
