"""Script para descargar todos los modelos requeridos.

POLÍTICA DE MODELOS:
PronunciaPA es un sistema microkernel para evaluación de pronunciación.
El kernel requiere modelos ASR que produzcan IPA directo desde audio,
no texto que requiera post-procesamiento G2P (pérdida de alófonos).

MODELOS PRINCIPALES (obligatorios):
- Allosaurus uni2005: ASR → IPA multilingüe (2000+ lenguas)
- eSpeak-ng: G2P texto → IPA para generar referencias fonémicas

MODELOS OPCIONALES:
- TinyLlama 1.1B: LLM para generar ejercicios y feedback pedagógico
- Phi-3 mini: LLM alternativo (más capaz, mayor consumo)
- Wav2Vec2 IPA: ASR → IPA (requiere token HF, gated)
  Ejemplo: facebook/wav2vec2-large-xlsr-53-ipa

MODELOS NO RECOMENDADOS (producen texto, no IPA):
- Wav2Vec2 texto (xlsr-53, variantes por idioma)
- Vosk, Whisper: útiles para transcripción, no para análisis fonético

NOTA: TinyLlama/Phi NO se usan para ASR, solo para:
  1. Generar ejercicios personalizados (drill generation)
  2. Retroalimentación pedagógica (feedback textual)
"""
from __future__ import annotations

import os
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


def download_wav2vec2_ipa(model_id: str, hf_token: str | None = None) -> None:
    """Descargar modelo Wav2Vec2 IPA (OPCIONAL).

    ADVERTENCIA: Solo descarga modelos que produzcan IPA, no texto.
    Modelos recomendados:
    - facebook/wav2vec2-large-xlsr-53-ipa (gated, requiere token)
    - Otros modelos fine-tuned para fonemas/IPA

    Para modelos privados (gated), pasa un token de Hugging Face
    o exporta HUGGINGFACEHUB_API_TOKEN / HF_TOKEN en el entorno.
    """
    print(f"\n=== Descargando Wav2Vec2: {model_id} ===")
    try:
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    except ImportError:
        print("Instalando transformers y torch...")
        install_package("transformers")
        install_package("torch")
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    hf_token = hf_token or os.environ.get("HUGGINGFACEHUB_API_TOKEN") or os.environ.get("HF_TOKEN")
    print(f"Descargando {model_id}...")
    Wav2Vec2Processor.from_pretrained(model_id, use_auth_token=hf_token)
    Wav2Vec2ForCTC.from_pretrained(model_id, use_auth_token=hf_token)
    print("✅ Wav2Vec2 descargado")


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


def main(
    include_llms: bool = False,
    include_phi3: bool = False,
    wav2vec2_ipa_model: str | None = None,
    hf_token: str | None = None,
) -> None:
    """Descargar modelos según configuración.
    
    Por defecto descarga solo lo esencial:
    - Allosaurus (ASR → IPA)
    - Verifica eSpeak (G2P texto → IPA)
    
    Opcionales:
    - TinyLlama/Phi-3: para ejercicios y feedback (no ASR)
    - Wav2Vec2 IPA: ASR alternativo (requiere token si es gated)
    """
    print("=" * 70)
    print("DESCARGA DE MODELOS - PronunciaPA (Microkernel Architecture)")
    print("=" * 70)
    
    # Crear directorio
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Modelos principales (OBLIGATORIOS para pipeline IPA)
    print("\n📦 MODELOS PRINCIPALES (ASR → IPA):")
    download_allosaurus()
    verify_espeak()
    
    # Modelos opcionales ASR
    if wav2vec2_ipa_model:
        print("\n📦 MODELO ASR OPCIONAL:")
        download_wav2vec2_ipa(model_id=wav2vec2_ipa_model, hf_token=hf_token)
    
    # LLMs para ejercicios/feedback (NO para ASR)
    if include_llms or include_phi3:
        print("\n📦 MODELOS LLM (ejercicios y feedback, NO ASR):")
        if include_llms:
            download_tinyllama()
        if include_phi3:
            download_phi3_optional()
    
    print("\n" + "=" * 70)
    print("✅ DESCARGA COMPLETADA")
    print("=" * 70)
    print("\nNOTA: TinyLlama/Phi se usan para generar ejercicios y feedback,")
    print("      NO para reconocimiento de audio (ASR).")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Descargar modelos para PronunciaPA (ASR→IPA + LLMs opcionales)"
    )
    parser.add_argument(
        "--with-llms",
        action="store_true",
        help="Incluir TinyLlama (LLM para ejercicios/feedback, no ASR)",
    )
    parser.add_argument(
        "--with-phi3",
        action="store_true",
        help="Incluir Phi-3 mini (LLM alternativo, no ASR)",
    )
    parser.add_argument(
        "--wav2vec2-ipa-model",
        default=None,
        help=(
            "Modelo Wav2Vec2 IPA opcional (debe producir IPA, no texto). "
            "Ejemplo: facebook/wav2vec2-large-xlsr-53-ipa (requiere token HF)"
        ),
    )
    parser.add_argument(
        "--hf-token",
        default=None,
        help="Token de Hugging Face para modelos gated (opcional)",
    )
    args = parser.parse_args()
    main(
        include_llms=args.with_llms,
        include_phi3=args.with_phi3,
        wav2vec2_ipa_model=args.wav2vec2_ipa_model,
        hf_token=args.hf_token,
    )
