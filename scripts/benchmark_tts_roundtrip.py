#!/usr/bin/env python3
"""Benchmark TTS → ASR → IPA round-trip.

Mide la exactitud del sistema midiendo cuánto difiere el IPA que el ASR
devuelve de lo que eSpeak (referencia) esperaría, para audio generado
automáticamente con TTS.

Flujo por palabra
-----------------
1. eSpeak TTS  → WAV temporal  (audio sintético)
2. TextRef     → IPA_ref       (IPA esperada de eSpeak)
3. ASR         → IPA_hyp       (IPA reconocida por Allosaurus)
4. Levenshtein → PER           (Phone Error Rate)

Uso rápido
----------
    # Stub mode (no necesita modelos — útil para CI)
    PRONUNCIAPA_ASR=stub python scripts/benchmark_tts_roundtrip.py --lang es --stub

    # Modo real (requiere Allosaurus instalado + eSpeak-NG en PATH)
    python scripts/benchmark_tts_roundtrip.py --lang es

    # Inglés con CMU Dict
    python scripts/benchmark_tts_roundtrip.py --lang en --textref cmudict

    # Guardar resultados
    python scripts/benchmark_tts_roundtrip.py --lang es --output results_es.json

Opciones
--------
    --lang LANG         Idioma a evaluar (es, en, fr, de). Default: es
    --words N           Número de palabras a usar del conjunto de test. Default: 30
    --textref NAME      Backend TextRef a usar (espeak, cmudict). Default: espeak
    --output FILE       Guardar resultados en JSON.
    --stub              Usar StubASR (no requiere modelos — solo mide pipeline)
    --verbose           Mostrar tokens por palabra
    --help              Mostrar esta ayuda

Requisitos
----------
    pip install -e '.[dev]'                 # instalación mínima
    pip install -e '.[dev,asr,speech]'      # con Allosaurus + eSpeak

    # eSpeak-NG en PATH (para TTS):
    #   Ubuntu/Debian:  sudo apt install espeak-ng
    #   macOS:          brew install espeak-ng
    #   Windows:        https://github.com/espeak-ng/espeak-ng/releases

Interpretación de resultados
-----------------------------
    PER (Phone Error Rate):
        0.00  → IPA perfectamente igual a la referencia
        0.10  → 10 % de fonemas diferentes (excelente para ASR real)
        0.20  → 20 % (bueno para ASR con TTS limpio)
        > 0.4 → Problema serio en el pipeline (configurar e investigar)

    Un PER alto en audio TTS (sin ruido, dicción perfecta) indica:
    - Allosaurus usa inventario fonético incorrecto para el idioma
    - eSpeak y Allosaurus representan los mismos sonidos de forma diferente
    - Bugs en postprocesamiento o normalización de tokens
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Asegurar que el proyecto está en el path
_repo = Path(__file__).parent.parent
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger("benchmark")

# ---------------------------------------------------------------------------
# Palabras de test por idioma
# Se eligieron palabras cortas, frecuentes y con fonemas representativos.
# ---------------------------------------------------------------------------
BENCHMARK_WORDS: Dict[str, List[str]] = {
    "es": [
        "hola", "casa", "pero", "bien", "todo", "como", "para", "este",
        "vida", "tiempo", "lugar", "agua", "madre", "padre", "noche",
        "gente", "mundo", "color", "grande", "pequeño", "ciudad",
        "trabajo", "hablar", "comer", "caminar", "correr", "escribir",
        "leer", "dormir", "pensar",
    ],
    "en": [
        "hello", "world", "good", "time", "people", "water", "night",
        "light", "house", "speak", "write", "read", "sleep", "think",
        "color", "large", "small", "city", "work", "walk", "run",
        "mother", "father", "place", "life", "great", "little",
        "different", "between", "through",
    ],
    "fr": [
        "bonjour", "monde", "bien", "temps", "gens", "eau", "nuit",
        "lumière", "maison", "parler", "écrire", "lire", "dormir",
        "penser", "couleur", "grand", "petit", "ville", "travail",
        "marcher", "courir", "mère", "père", "lieu", "vie",
    ],
    "de": [
        "hallo", "welt", "gut", "zeit", "leute", "wasser", "nacht",
        "licht", "haus", "sprechen", "schreiben", "lesen", "schlafen",
        "denken", "farbe", "groß", "klein", "stadt", "arbeit",
        "gehen", "laufen", "mutter", "vater", "ort", "leben",
    ],
}

# Voces eSpeak por idioma para TTS
_ESPEAK_VOICES: Dict[str, str] = {
    "es": "es",
    "en": "en-us",
    "fr": "fr",
    "de": "de",
}


# ---------------------------------------------------------------------------
# Generación de audio con eSpeak TTS
# ---------------------------------------------------------------------------

def _find_espeak() -> Optional[str]:
    """Buscar binario eSpeak-NG en PATH."""
    for name in ("espeak-ng", "espeak"):
        result = subprocess.run(
            ["which", name], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    return None


def generate_tts_audio(word: str, lang: str, espeak_bin: str) -> Optional[str]:
    """Generar WAV temporal con eSpeak TTS.

    Retorna la ruta al archivo temporal (el llamador es responsable de eliminarlo),
    o None si la generación falló.
    """
    voice = _ESPEAK_VOICES.get(lang, lang)
    tmp = tempfile.NamedTemporaryFile(
        prefix="bench_tts_", suffix=".wav", delete=False
    )
    tmp.close()

    cmd = [
        espeak_bin,
        "-v", voice,
        "-s", "130",          # 130 palabras/minuto (velocidad normal)
        "-a", "80",           # amplitud moderada
        "-w", tmp.name,       # output WAV
        word,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("eSpeak TTS falló para '%s': %s", word, result.stderr)
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        return None
    return tmp.name


# ---------------------------------------------------------------------------
# Pipeline PronunciaPA (ASR + TextRef)
# ---------------------------------------------------------------------------

async def _run_word_benchmark(
    word: str,
    lang: str,
    asr,
    textref,
    pre,
    espeak_bin: str,
) -> Tuple[str, Optional[float], List[str], List[str], str]:
    """Evaluar una sola palabra. Retorna (word, per, ref_tokens, hyp_tokens, error)."""
    from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens, clean_textref_tokens
    from ipa_core.compare.levenshtein import LevenshteinComparator

    # 1. TTS → WAV
    wav_path = generate_tts_audio(word, lang, espeak_bin)
    if wav_path is None:
        return word, None, [], [], "TTS failed"

    try:
        # 2. Preprocesar audio
        audio_input = {"path": wav_path, "sample_rate": 16000, "channels": 1}
        pre_res = await pre.process_audio(audio_input)
        processed_audio = pre_res.get("audio", audio_input)

        # 3. ASR → IPA hipótesis
        try:
            asr_result = await asr.transcribe(processed_audio, lang=lang)
            raw_hyp = asr_result.get("tokens", [])
            hyp_tokens = clean_asr_tokens(raw_hyp, lang=lang)
            norm_hyp = await pre.normalize_tokens(hyp_tokens)
            hyp_tokens = norm_hyp.get("tokens", hyp_tokens)
        except Exception as exc:
            return word, None, [], [], f"ASR error: {exc}"

        # 4. TextRef → IPA referencia (modo fonémico)
        try:
            ref_result = await textref.to_ipa(word, lang=lang)
            raw_ref = ref_result.get("tokens", [])
            ref_tokens = clean_textref_tokens(raw_ref, lang=lang, preserve_allophones=False)
            norm_ref = await pre.normalize_tokens(ref_tokens)
            ref_tokens = norm_ref.get("tokens", ref_tokens)
        except Exception as exc:
            return word, None, [], [], f"TextRef error: {exc}"

        # 5. Comparar
        if not ref_tokens:
            return word, None, hyp_tokens, [], "Empty reference"

        comp = LevenshteinComparator(use_articulatory=False)
        comp_result = await comp.compare(ref_tokens, hyp_tokens)
        per = comp_result.get("per", 1.0)

        return word, per, ref_tokens, hyp_tokens, ""

    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


async def run_benchmark(
    lang: str,
    n_words: int,
    textref_name: str,
    use_stub: bool,
    verbose: bool,
) -> Dict[str, Any]:
    """Ejecutar benchmark completo y retornar resultados."""
    from ipa_core.backends.asr_stub import StubASR
    from ipa_core.preprocessor_basic import BasicPreprocessor
    from ipa_core.plugins import registry

    registry._register_defaults()

    # Seleccionar ASR
    if use_stub:
        asr = StubASR()
        asr_name = "stub"
    else:
        asr_name = os.environ.get("PRONUNCIAPA_ASR", "allosaurus")
        asr = registry.resolve_asr(asr_name, {"lang": lang})
        asr_name = type(asr).__name__

    # Seleccionar TextRef
    textref = registry.resolve_textref(textref_name, {"default_lang": lang})

    # Preprocessor
    pre = BasicPreprocessor()

    # Setup
    await asr.setup()
    await textref.setup()
    await pre.setup()

    espeak_bin = _find_espeak()
    if espeak_bin is None:
        print(
            "ERROR: eSpeak-NG no encontrado en PATH.\n"
            "Instala con: sudo apt install espeak-ng  (Linux)\n"
            "             brew install espeak-ng        (macOS)",
            file=sys.stderr,
        )
        sys.exit(1)

    words = BENCHMARK_WORDS.get(lang, BENCHMARK_WORDS["es"])[:n_words]

    print(f"\nBenchmark PronunciaPA — TTS round-trip")
    print(f"  Idioma  : {lang}")
    print(f"  ASR     : {asr_name}")
    print(f"  TextRef : {textref_name}")
    print(f"  TTS     : {espeak_bin}")
    print(f"  Palabras: {len(words)}")
    print("-" * 50)

    results = []
    pers = []

    for word in words:
        word_result, per, ref_tokens, hyp_tokens, error = await _run_word_benchmark(
            word, lang, asr, textref, pre, espeak_bin
        )

        row: Dict[str, Any] = {
            "word": word,
            "per": per,
            "ref": ref_tokens,
            "hyp": hyp_tokens,
            "error": error,
        }
        results.append(row)

        if error:
            status = f"  ERROR: {error}"
        elif per is not None:
            pers.append(per)
            bar = "█" * int((1 - per) * 20)
            status = f"  PER={per:.3f}  |{bar:<20}|"
        else:
            status = "  –"

        line = f"  {word:<18} {status}"
        if verbose and not error:
            line += f"\n    ref: {' '.join(ref_tokens)}"
            line += f"\n    hyp: {' '.join(hyp_tokens)}"
        print(line)

    # Teardown
    await asr.teardown()
    await textref.teardown()
    await pre.teardown()

    # Estadísticas
    avg_per = sum(pers) / len(pers) if pers else 1.0
    score = (1 - avg_per) * 100
    evaluated = len(pers)
    failed = len(words) - evaluated

    print("-" * 50)
    print(f"  Evaluadas : {evaluated}/{len(words)} palabras")
    if failed:
        print(f"  Fallidas  : {failed}")
    print(f"  PER media : {avg_per:.4f}")
    print(f"  Score     : {score:.1f} / 100")

    if avg_per < 0.10:
        rating = "Excelente ✓"
    elif avg_per < 0.20:
        rating = "Bueno"
    elif avg_per < 0.35:
        rating = "Aceptable (revisar postprocesamiento)"
    else:
        rating = "Problema detectado — investigar pipeline"

    print(f"  Calidad   : {rating}")
    print()

    return {
        "lang": lang,
        "asr": asr_name,
        "textref": textref_name,
        "words_evaluated": evaluated,
        "words_failed": failed,
        "avg_per": avg_per,
        "score": score,
        "rating": rating,
        "words": results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark TTS→ASR round-trip para PronunciaPA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--lang", default="es", choices=list(BENCHMARK_WORDS), help="Idioma (default: es)")
    parser.add_argument("--words", type=int, default=30, help="Número de palabras a evaluar (default: 30)")
    parser.add_argument("--textref", default="espeak", help="Backend TextRef: espeak, cmudict (default: espeak)")
    parser.add_argument("--output", help="Guardar resultados en archivo JSON")
    parser.add_argument("--stub", action="store_true", help="Usar StubASR (sin modelos reales)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar tokens por palabra")
    args = parser.parse_args()

    results = asyncio.run(run_benchmark(
        lang=args.lang,
        n_words=args.words,
        textref_name=args.textref,
        use_stub=args.stub,
        verbose=args.verbose,
    ))

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()
