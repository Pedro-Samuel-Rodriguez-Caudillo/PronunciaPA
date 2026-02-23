#!/usr/bin/env python3
"""Depuración concisa del pipeline de PronunciaPA.

Ejecuta el pipeline completo etapa por etapa e imprime una tabla compacta
que muestra en qué punto falla algo y cuánto tarda cada etapa.

Uso rápido (sin audio, ASR stub)::

    python scripts/debug_pipeline.py "hola mundo" --lang es

Con audio real::

    python scripts/debug_pipeline.py "hola" --lang es --audio path/to/audio.wav --asr allosaurus

Opciones::

    positional TEXT          Texto de referencia a transcribir
    --lang   LANG            Código de idioma (default: es)
    --asr    NAME            Backend ASR: stub (default), allosaurus, wav2vec2
    --textref NAME           TextRef: espeak (default), grapheme, cmudict
    --audio  PATH            Archivo de audio (si se omite, usa ASR stub con tokens inventados)
    --tokens IPA,...         Tokens IPA para usar con ASR stub (ej: m,a,l)
    --json                   Salida JSON en lugar de tabla ASCII
    -v / --verbose           Incluir detalles extra (tokens completos, meta)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ipa_core.debug.tracer import PipelineTracer


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

def _fmt_tokens(tokens: list, *, max_n: int = 5, verbose: bool = False) -> str:
    if not tokens:
        return "[]"
    n = len(tokens)
    shown = tokens if verbose else tokens[:max_n]
    suffix = f"…+{n - max_n}" if not verbose and n > max_n else ""
    return f"[{','.join(shown)}{suffix}] ({n})"


# ---------------------------------------------------------------------------
# Creación de audio de prueba mínimo (16kHz mono WAV silencioso)
# ---------------------------------------------------------------------------

def _create_stub_wav(duration_ms: int = 800) -> str:
    """Crea un WAV silencioso mínimo para pasar al pipeline cuando no hay audio real."""
    import struct, wave
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sr = 16000
    n_frames = sr * duration_ms // 1000
    with wave.open(tmp.name, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))
    return tmp.name


# ---------------------------------------------------------------------------
# Pipeline instrumented
# ---------------------------------------------------------------------------

async def run_debug(
    text: str,
    *,
    lang: str = "es",
    asr_name: str = "stub",
    textref_name: str = "espeak",
    audio_path: str | None = None,
    stub_tokens: list[str] | None = None,
    verbose: bool = False,
) -> PipelineTracer:
    """Ejecuta el pipeline completo con tracing.

    Retorna el tracer con todos los StageRecords rellenos.
    """
    from ipa_core.plugins import registry as reg

    tracer = PipelineTracer(label=text[:40], lang=lang)

    # ── Resolve components ─────────────────────────────────────────────
    asr, textref, comp, pre = None, None, None, None

    with tracer.stage("resolve") as s:
        asr      = reg.resolve_asr(asr_name, {})
        textref  = reg.resolve_textref(textref_name, {"default_lang": lang})
        comp     = reg.resolve_comparator("levenshtein", {})
        pre      = reg.resolve_preprocessor("basic", {})
        s.detail = f"asr={asr_name} textref={textref_name}"

    # ── Setup ──────────────────────────────────────────────────────────
    with tracer.stage("setup") as s:
        await asyncio.gather(
            asr.setup(),
            textref.setup(),
            comp.setup(),
            pre.setup(),
        )
        s.detail = "all components ready"

    # ── Preprocess ────────────────────────────────────────────────────
    tmp_wav = None
    audio_input: dict | None = None

    with tracer.stage("preprocess") as s:
        if audio_path:
            wav_path = audio_path
        else:
            tmp_wav = _create_stub_wav(800)
            wav_path = tmp_wav
        res = await pre.process_audio({"path": wav_path, "sample_rate": 16000, "channels": 1})
        audio_input = res.get("audio", {"path": wav_path, "sample_rate": 16000, "channels": 1})
        pa = audio_input
        dur = res.get("meta", {}).get("duration_ms", "?")
        s.detail = f"{pa.get('sample_rate', '?')}Hz mono dur={dur}ms"

    # ── ASR ────────────────────────────────────────────────────────────
    hyp_tokens: list[str] = []

    with tracer.stage("asr") as s:
        if asr_name == "stub" and stub_tokens:
            # Override stub tokens via monkey-patch
            asr._tokens = stub_tokens  # type: ignore[attr-defined]
        asr_result = await asr.transcribe(audio_input, lang=lang)  # type: ignore[arg-type]
        hyp_tokens = asr_result.get("tokens", [])
        s.detail = _fmt_tokens(hyp_tokens, verbose=verbose)
        if verbose:
            s.extra["meta"] = asr_result.get("meta", {})

    # ── TextRef ────────────────────────────────────────────────────────
    ref_tokens: list[str] = []

    with tracer.stage("textref") as s:
        tr_result = await textref.to_ipa(text, lang=lang)
        ref_tokens = tr_result.get("tokens", [])
        s.detail = _fmt_tokens(ref_tokens, verbose=verbose)
        if verbose:
            s.extra["meta"] = tr_result.get("meta", {})

    # ── Normalize tokens ───────────────────────────────────────────────
    with tracer.stage("normalize") as s:
        hyp_res = await pre.normalize_tokens(hyp_tokens)
        ref_res = await pre.normalize_tokens(ref_tokens)
        hyp_tokens = hyp_res.get("tokens", hyp_tokens)
        ref_tokens = ref_res.get("tokens", ref_tokens)
        hyp_oov = hyp_res.get("meta", {}).get("oov_tokens", [])
        s.detail = f"hyp={len(hyp_tokens)} ref={len(ref_tokens)}" + (
            f" oov={hyp_oov[:3]}" if hyp_oov else ""
        )

    # ── Compare ────────────────────────────────────────────────────────
    with tracer.stage("compare") as s:
        cmp_result = await comp.compare(ref_tokens, hyp_tokens)
        per = cmp_result.get("per", 0.0)
        score = round((1 - per) * 100, 1)
        ops = cmp_result.get("ops", [])
        n_err = sum(1 for o in ops if o.get("op") != "eq")
        s.detail = f"PER={per:.2f} score={score} errors={n_err}"
        if verbose:
            s.extra["ops"] = ops

    # ── Teardown ───────────────────────────────────────────────────────
    try:
        await asyncio.gather(
            asr.teardown(),
            textref.teardown(),
            comp.teardown(),
            pre.teardown(),
        )
    except Exception:
        pass

    if tmp_wav:
        try:
            os.unlink(tmp_wav)
        except OSError:
            pass

    return tracer


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="debug_pipeline",
        description="Traza el pipeline de PronunciaPA etapa a etapa.",
    )
    parser.add_argument("text", help="Texto de referencia")
    parser.add_argument("--lang",    default="es",      metavar="LANG")
    parser.add_argument("--asr",     default="stub",    metavar="NAME")
    parser.add_argument("--textref", default="espeak",  metavar="NAME")
    parser.add_argument("--audio",   default=None,      metavar="PATH")
    parser.add_argument("--tokens",  default=None,      metavar="IPA,...",
                        help="Tokens IPA para stub ASR (coma-separados)")
    parser.add_argument("--json",    action="store_true",
                        help="Salida en formato JSON")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    stub_tokens = [t.strip() for t in args.tokens.split(",")] if args.tokens else None

    try:
        tracer = asyncio.run(run_debug(
            args.text,
            lang=args.lang,
            asr_name=args.asr,
            textref_name=args.textref,
            audio_path=args.audio,
            stub_tokens=stub_tokens,
            verbose=args.verbose,
        ))
    except Exception as exc:
        # run_debug already records the failure in the tracer;
        # but if it never got created, handle gracefully.
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(tracer.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(tracer.as_text())

    sys.exit(0 if tracer.passed else 1)


if __name__ == "__main__":
    main()
