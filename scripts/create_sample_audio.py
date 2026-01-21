#!/usr/bin/env python3
"""Genera archivos de audio de muestra para pruebas y demos.

Este script crea archivos WAV simples con tonos de diferentes frecuencias
que representan sílabas básicas. Útil para testing sin dependencias de TTS.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import numpy as np
    from scipy.io import wavfile
except ImportError:
    print("❌ Error: numpy o scipy no están instalados.")
    print("Instálalos con: pip install numpy scipy")
    sys.exit(1)


def generate_tone_sequence(
    frequencies: list[float],
    duration_per_tone: float = 0.3,
    sample_rate: int = 16000,
    amplitude: float = 0.3,
) -> np.ndarray:
    """Genera una secuencia de tonos.
    
    Args:
        frequencies: Lista de frecuencias en Hz
        duration_per_tone: Duración de cada tono en segundos
        sample_rate: Frecuencia de muestreo en Hz
        amplitude: Amplitud de la onda (0-1)
        
    Returns:
        Array NumPy con los samples de audio
    """
    samples = []
    samples_per_tone = int(duration_per_tone * sample_rate)
    fade_samples = int(0.01 * sample_rate)  # 10ms fade in/out
    
    for freq in frequencies:
        t = np.linspace(0, duration_per_tone, samples_per_tone, False)
        tone = amplitude * np.sin(2 * np.pi * freq * t)
        
        # Aplicar fade in/out para evitar clicks
        if fade_samples > 0:
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)
            tone[:fade_samples] *= fade_in
            tone[-fade_samples:] *= fade_out
        
        samples.extend(tone)
    
    # Silencio al final
    silence = np.zeros(int(0.2 * sample_rate))
    samples.extend(silence)
    
    return np.array(samples, dtype=np.float32)


def create_sample_audio(
    output_path: Path,
    phrase: str,
    lang: str,
    frequencies: list[float],
) -> None:
    """Crea un archivo WAV de muestra.
    
    Args:
        output_path: Ruta donde guardar el archivo
        phrase: Frase que representa el audio
        lang: Idioma (es, en)
        frequencies: Frecuencias de tonos a generar
    """
    audio = generate_tone_sequence(frequencies)
    
    # Normalizar a int16
    audio_int = (audio * 32767).astype(np.int16)
    
    # Guardar
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(output_path, 16000, audio_int)
    
    print(f"✅ Creado: {output_path}")
    print(f"   Frase: {phrase}")
    print(f"   Idioma: {lang}")
    print(f"   Duración: {len(audio) / 16000:.2f}s")


def create_manifest(
    manifest_path: Path,
    samples: list[dict],
) -> None:
    """Crea un archivo manifest.jsonl con metadatos de los samples.
    
    Args:
        manifest_path: Ruta al archivo manifest
        samples: Lista de diccionarios con metadata de cada sample
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    
    print(f"\n✅ Creado manifest: {manifest_path}")
    print(f"   Samples: {len(samples)}")


def main():
    parser = argparse.ArgumentParser(
        description="Genera archivos de audio de muestra para demos y tests"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/sample"),
        help="Directorio de salida (default: data/sample)",
    )
    
    args = parser.parse_args()
    
    # Samples a crear (frecuencias aproximadas de formantes para vocales)
    samples_to_create = [
        {
            "filename": "sample_es.wav",
            "phrase": "hola mundo",
            "lang": "es",
            "ipa_expected": "o l a m u n d o",
            # Frecuencias que suenan como vocales: o-a-u-o
            "frequencies": [500, 700, 300, 500],
        },
        {
            "filename": "sample_en.wav",
            "phrase": "hello world",
            "lang": "en",
            "ipa_expected": "h ɛ l o w ɜː l d",
            # Frecuencias: e-o-u
            "frequencies": [600, 500, 300],
        },
        {
            "filename": "sample_short.wav",
            "phrase": "test",
            "lang": "en",
            "ipa_expected": "t ɛ s t",
            "frequencies": [600],
        },
    ]
    
    manifest_entries = []
    
    print("🎵 Generando archivos de audio de muestra...\n")
    
    for sample in samples_to_create:
        output_path = args.output_dir / sample["filename"]
        
        create_sample_audio(
            output_path,
            sample["phrase"],
            sample["lang"],
            sample["frequencies"],
        )
        
        # Preparar entrada para manifest
        manifest_entry = {
            "audio_filepath": str(output_path),
            "text": sample["phrase"],
            "lang": sample["lang"],
            "ipa_expected": sample["ipa_expected"],
            "duration": len(sample["frequencies"]) * 0.3 + 0.2,
        }
        manifest_entries.append(manifest_entry)
        print()
    
    # Crear manifest
    manifest_path = args.output_dir / "manifest.jsonl"
    create_manifest(manifest_path, manifest_entries)
    
    print("\n" + "=" * 60)
    print("✅ ¡Listo! Archivos de muestra creados.")
    print(f"\nPruébalos con:")
    print(f"  python scripts/demo_client.py --audio {args.output_dir}/sample_es.wav")
    print("=" * 60)


if __name__ == "__main__":
    main()
