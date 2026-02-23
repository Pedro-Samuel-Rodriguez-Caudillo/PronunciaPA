"""Endpoints de debug — estado de componentes y traza del pipeline.

``GET /debug/components``
    Verifica cada componente individualmente.  Respuesta concisa: una entrada
    por componente con estado y latencia de setup.

``GET /debug/trace``
    Ejecuta el pipeline completo (ASR stub + TextRef real) con un texto de
    prueba y retorna la traza etapa a etapa.  Útil para verificar que todo
    el sistema funciona de extremo a extremo sin necesitar audio real.

Diseño
------
- Sin verbosidad innecesaria: solo lo que importa para diagnosticar fallos.
- Los errores se capturan en el JSON de respuesta, no se convierten en HTTP 5xx.
- Sin autenticación: solo para entornos de desarrollo/local.
"""
from __future__ import annotations

import asyncio
import os
import time
import tempfile
import struct
import wave
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/debug", tags=["debug"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_stub_wav(duration_ms: int = 800) -> str:
    sr = 16000
    n = sr * duration_ms // 1000
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{n}h", *([0] * n)))
    return tmp.name


async def _check_component(category: str, name: str, params: dict) -> dict[str, Any]:
    """Instanciar y hacer setup de un componente; medir latencia."""
    from ipa_core.plugins import registry as reg

    t = time.monotonic()
    try:
        inst = reg.resolve(category, name, params)
        await inst.setup()
        ms = round((time.monotonic() - t) * 1000, 1)
        await inst.teardown()
        return {"name": name, "status": "ok", "ms": ms}
    except Exception as exc:
        ms = round((time.monotonic() - t) * 1000, 1)
        return {
            "name": name,
            "status": "fail",
            "ms": ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


# ---------------------------------------------------------------------------
# GET /debug/components
# ---------------------------------------------------------------------------

@router.get(
    "/components",
    summary="Estado de componentes",
    description="Verifica cada componente del sistema de forma independiente. "
                "Una fila por componente: nombre | ok/fail | ms | error?",
)
async def debug_components(
    lang: str = Query(default="es", description="Idioma para los providers"),
) -> dict[str, Any]:
    asr_name     = os.environ.get("PRONUNCIAPA_ASR", "stub")
    textref_name = os.environ.get("PRONUNCIAPA_TEXTREF", "espeak")
    llm_name     = os.environ.get("PRONUNCIAPA_LLM", "rule_based")

    checks = await asyncio.gather(
        _check_component("asr",          asr_name,     {}),
        _check_component("textref",      textref_name, {"default_lang": lang}),
        _check_component("comparator",   "levenshtein", {}),
        _check_component("preprocessor", "basic",       {}),
        _check_component("llm",          llm_name,      {}),
    )

    all_ok = all(c["status"] == "ok" for c in checks)
    return {
        "status":     "ok" if all_ok else "degraded",
        "components": list(checks),
    }


# ---------------------------------------------------------------------------
# GET /debug/trace
# ---------------------------------------------------------------------------

@router.get(
    "/trace",
    summary="Traza del pipeline completo",
    description="Ejecuta el pipeline con ASR stub y retorna la traza etapa a etapa. "
                "Úsalo para verificar que todo funciona sin necesitar audio real.",
)
async def debug_trace(
    text: str  = Query(default="hola mundo", description="Texto de referencia"),
    lang: str  = Query(default="es",         description="Código de idioma"),
    textref: str = Query(default="espeak",   description="TextRef backend"),
    tokens: str  = Query(default="",         description="Tokens IPA para stub (coma-separados)"),
) -> dict[str, Any]:
    """Traza el pipeline completo y devuelve el resultado."""
    from ipa_core.debug.tracer import PipelineTracer
    from ipa_core.plugins import registry as reg

    stub_tokens = [t.strip() for t in tokens.split(",") if t.strip()] or None
    tracer = PipelineTracer(label=text[:40], lang=lang)
    tmp_wav = None

    try:
        # Resolve
        with tracer.stage("resolve") as s:
            asr_inst  = reg.resolve_asr("stub", {})
            tr_inst   = reg.resolve_textref(textref, {"default_lang": lang})
            comp_inst = reg.resolve_comparator("levenshtein", {})
            pre_inst  = reg.resolve_preprocessor("basic", {})
            s.detail  = f"asr=stub textref={textref}"

        # Setup
        with tracer.stage("setup") as s:
            await asyncio.gather(
                asr_inst.setup(), tr_inst.setup(),
                comp_inst.setup(), pre_inst.setup(),
            )
            s.detail = "ok"

        # Preprocess
        with tracer.stage("preprocess") as s:
            tmp_wav = _create_stub_wav(800)
            res = await pre_inst.process_audio({
                "path": tmp_wav, "sample_rate": 16000, "channels": 1
            })
            audio_in = res.get("audio", {"path": tmp_wav, "sample_rate": 16000, "channels": 1})
            s.detail = f"{audio_in.get('sample_rate', '?')}Hz mono"

        # ASR
        hyp_tokens: list[str] = []
        with tracer.stage("asr") as s:
            if stub_tokens:
                asr_inst._tokens = stub_tokens  # type: ignore[attr-defined]
            asr_res    = await asr_inst.transcribe(audio_in, lang=lang)
            hyp_tokens = asr_res.get("tokens", [])
            s.detail   = f"tokens={hyp_tokens[:5]} ({len(hyp_tokens)})"

        # TextRef
        ref_tokens: list[str] = []
        with tracer.stage("textref") as s:
            tr_res     = await tr_inst.to_ipa(text, lang=lang)
            ref_tokens = tr_res.get("tokens", [])
            s.detail   = f"tokens={ref_tokens[:5]} ({len(ref_tokens)})"

        # Normalize
        with tracer.stage("normalize") as s:
            h = await pre_inst.normalize_tokens(hyp_tokens)
            r = await pre_inst.normalize_tokens(ref_tokens)
            hyp_tokens = h.get("tokens", hyp_tokens)
            ref_tokens = r.get("tokens", ref_tokens)
            oov = h.get("meta", {}).get("oov_tokens", [])
            s.detail = f"hyp={len(hyp_tokens)} ref={len(ref_tokens)}" + (
                f" oov={oov[:3]}" if oov else ""
            )

        # Compare
        with tracer.stage("compare") as s:
            cmp = await comp_inst.compare(ref_tokens, hyp_tokens)
            per   = cmp.get("per", 0.0)
            score = round((1 - per) * 100, 1)
            ops   = cmp.get("ops", [])
            n_err = sum(1 for o in ops if o.get("op") != "eq")
            s.detail = f"PER={per:.2f} score={score} errors={n_err}"

        # Teardown
        await asyncio.gather(
            asr_inst.teardown(), tr_inst.teardown(),
            comp_inst.teardown(), pre_inst.teardown(),
        )

    except Exception:
        pass  # tracer.failed ya captura el error

    finally:
        if tmp_wav:
            try:
                os.unlink(tmp_wav)
            except OSError:
                pass

    return tracer.as_dict()
