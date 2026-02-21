#!/usr/bin/env python3
"""Cliente demo para probar la API de transcripción de PronunciaPA.

Uso:
    python scripts/demo_client.py [--audio AUDIO_FILE] [--server URL] [--lang LANG]

Ejemplos:
    # Usar audio de ejemplo
    python scripts/demo_client.py
    
    # Usar tu propio archivo de audio
    python scripts/demo_client.py --audio mi_audio.wav --lang es
    
    # Conectar a servidor personalizado
    python scripts/demo_client.py --server http://localhost:8000
"""
import argparse
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' no está instalado.")
    print("Instálalo con: pip install requests")
    sys.exit(1)


def transcribe_audio(
    audio_path: Path,
    server_url: str = "http://localhost:8000",
    lang: str = "es",
) -> dict:
    """Envía un archivo de audio al servidor para transcribirlo.
    
    Args:
        audio_path: Ruta al archivo de audio
        server_url: URL base del servidor
        lang: Idioma del audio (es, en, etc.)
        
    Returns:
        Diccionario con la respuesta JSON del servidor
    """
    endpoint = f"{server_url}/v1/transcribe"
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {audio_path}")
    
    with open(audio_path, "rb") as f:
        files = {"audio": (audio_path.name, f, "audio/wav")}
        data = {"lang": lang}
        
        print(f"📤 Enviando audio a {endpoint}...")
        print(f"   Archivo: {audio_path}")
        print(f"   Idioma: {lang}")
        
        try:
            response = requests.post(endpoint, files=files, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Error: No se pudo conectar al servidor en {server_url}")
            print("   Asegúrate de que el servidor esté corriendo:")
            print("   - Con Docker: docker-compose up")
            print("   - Local: uvicorn ipa_server.main:get_app --reload")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"\n❌ Error HTTP {response.status_code}:")
            try:
                error_data = response.json()
                print(f"   {error_data.get('detail', 'Error desconocido')}")
            except:
                print(f"   {response.text}")
            sys.exit(1)


def print_results(result: dict) -> None:
    """Imprime los resultados de la transcripción de forma legible."""
    print("\n" + "=" * 60)
    print("✅ TRANSCRIPCIÓN COMPLETADA")
    print("=" * 60)
    
    # IPA completo
    ipa = result.get("ipa", "")
    print(f"\n📝 IPA: {ipa}")
    
    # Tokens individuales
    tokens = result.get("tokens", [])
    if tokens:
        print(f"\n🔤 Tokens ({len(tokens)}): {' '.join(tokens)}")
    
    # Metadatos
    meta = result.get("meta", {})
    if meta:
        print("\n📊 Metadatos:")
        print(f"   Backend: {meta.get('backend', 'N/A')}")
        print(f"   Método: {meta.get('method', 'N/A')}")
        if "duration" in result:
            print(f"   Duración: {result['duration']:.2f}s")
    
    # Timestamps si existen  (campo 'time_stamps' en ASRResult TypedDict)
    timestamps = result.get("time_stamps", [])
    if timestamps:
        print(f"\n⏱️  Timestamps: {len(timestamps)} segmentos")
        for i, ts in enumerate(timestamps[:5], 1):  # Mostrar solo los primeros 5
            print(f"   {i}. {ts}")
        if len(timestamps) > 5:
            print(f"   ... y {len(timestamps) - 5} más")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Cliente demo para la API de transcripción de PronunciaPA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s
  %(prog)s --audio mi_audio.wav --lang es
  %(prog)s --audio recording.mp3 --lang en --server http://api.example.com:8000
        """
    )
    
    parser.add_argument(
        "--audio",
        type=Path,
        help="Ruta al archivo de audio (default: data/sample/sample_es.wav si existe)",
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="URL del servidor (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--lang",
        default="es",
        choices=["es", "en", "es-mx", "en-us"],
        help="Idioma del audio (default: es)",
    )
    
    args = parser.parse_args()
    
    # Si no se especifica audio, buscar uno de ejemplo
    if args.audio is None:
        sample_paths = [
            Path("data/sample/sample_es.wav"),
            Path("inputs/ejemplo.wav"),
            Path("inputs/sample.wav"),
        ]
        
        for path in sample_paths:
            if path.exists():
                args.audio = path
                print(f"ℹ️  Usando audio de ejemplo: {args.audio}")
                break
        else:
            print("❌ Error: No se especificó archivo de audio y no se encontró ninguno de ejemplo.")
            print("\nOpciones:")
            print("  1. Especifica un archivo: --audio TU_ARCHIVO.wav")
            print("  2. Crea un audio de ejemplo en: data/sample/sample_es.wav")
            print("  3. Graba uno con: python scripts/record_wav.py")
            sys.exit(1)
    
    # Realizar transcripción
    result = transcribe_audio(args.audio, args.server, args.lang)
    
    # Mostrar resultados
    print_results(result)


if __name__ == "__main__":
    main()
