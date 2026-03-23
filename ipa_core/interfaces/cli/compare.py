from __future__ import annotations
import asyncio
from typing import Optional, List
from pathlib import Path
import typer
from rich.table import Table

from ipa_core.analysis import accent as accent_analysis
from ipa_core.audio.files import ensure_wav, cleanup_temp
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.errors import FileNotFound, NotReadyError, UnsupportedFormat, ValidationError
from ipa_core.services.comparison import ComparisonService
from ipa_core.services.feedback import FeedbackService
from ipa_core.services.feedback_store import FeedbackStore
from ipa_core.services.error_report import build_enriched_error_report
from ipa_core.services.fallback import generate_fallback_feedback
from ipa_core.services.transcription import TranscriptionService
from ipa_core.plugins import registry

from .helpers import (
    console, _COMPARE_MODES, _EVAL_LEVELS, _FEEDBACK_LEVELS,
    _get_kernel, _exit_code_for_error, _emit_json, _print_feedback_payload,
    _print_compare_table, _print_accent_ranking, _print_accent_features,
    _print_feedback, _print_compare_aligned, _normalize_sound
)

def transcribe(
    audio: Optional[str] = typer.Option(None, "--audio", "-a"),
    lang: str = typer.Option("es", "--lang", "-l"),
    backend: Optional[str] = typer.Option(None, "--backend"),
    textref: Optional[str] = typer.Option(None, "--textref"),
    mic: bool = typer.Option(False, "--mic"),
    seconds: float = typer.Option(3.0, "--seconds"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Transcribe audio a tokens IPA."""
    _check_transcribe_inputs(audio, mic)

    kernel = _get_kernel()
    _apply_transcribe_plugins(kernel, backend, textref, lang)
    
    wav_path, is_tmp = _get_wav_path(audio, mic, seconds)
    try:
        payload = _run_transcribe_service(kernel, wav_path, lang)
        _emit_transcribe_res(payload, lang, json_output)
    except Exception as e:
        console.print(f"Error: {e}", style="red"); raise typer.Exit(_exit_code_for_error(e))
    finally:
        if is_tmp and wav_path: cleanup_temp(wav_path)

def _check_transcribe_inputs(audio, mic):
    if not mic and not audio:
        console.print("Error: Debes especificar --audio o --mic", style="red")
        raise typer.Exit(1)

def _apply_transcribe_plugins(kernel, backend, textref, lang):
    if backend: kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
    if textref: kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})

def _run_transcribe_service(kernel, wav_path, lang):
    svc = TranscriptionService(preprocessor=kernel.pre, asr=kernel.asr, textref=kernel.textref, default_lang=lang)
    async def _run():
        await kernel.setup()
        try: return await svc.transcribe_file(wav_path, lang=lang)
        finally: await kernel.teardown()
    with console.status("[bold green]Transcribiendo..."):
        return asyncio.run(_run())

def _get_wav_path(audio, mic, seconds):
    if mic:
        from ipa_core.audio.microphone import record
        path, _ = record(seconds=seconds)
        return path, True
    return audio, False

def _emit_transcribe_res(payload, lang, json_out):
    tokens = payload.tokens if payload else []
    if json_out:
        _emit_json({"ipa": " ".join(tokens), "tokens": tokens, "lang": lang, "audio": payload.audio if payload else {}})
    else:
        console.print(f"IPA ({lang}): [bold cyan]{' '.join(tokens)}[/bold cyan]")

def compare(
    audio: str = typer.Option(..., "--audio", "-a"),
    text: str = typer.Option(..., "--text", "-t"),
    lang: str = typer.Option("es", "--lang", "-l"),
    backend: Optional[str] = typer.Option(None, "--backend"),
    textref: Optional[str] = typer.Option(None, "--textref"),
    comparator: Optional[str] = typer.Option(None, "--comparator"),
    json_output: bool = typer.Option(False, "--json"),
    show_accent: bool = typer.Option(True, "--show-accent"),
    strict_ipa: bool = typer.Option(True, "--strict-ipa"),
):
    """Compara el audio contra un texto de referencia."""
    kernel = _get_kernel()
    _apply_compare_plugins(kernel, backend, textref, comparator, lang)
    
    svc = ComparisonService(preprocessor=kernel.pre, asr=kernel.asr, textref=kernel.textref, comparator=kernel.comp, default_lang=lang)
    profile, accents, features, target_id, target_lang = _load_accent_data(show_accent, lang)

    async def _run():
        await kernel.setup()
        try:
            p = await svc.compare_file_detail(audio, text, lang=target_lang, allow_textref_fallback=not strict_ipa, fallback_lang=lang)
            res = _build_compare_res(p, target_lang, accents, features, target_id, kernel, show_accent, lang, text)
            return res
        finally: await kernel.teardown()

    try:
        with console.status("[bold green]Procesando comparación..."):
            res = asyncio.run(_run())
        _emit_compare_res(res, json_output, show_accent)
    except Exception as e:
        console.print(f"Error: {e}", style="red"); raise typer.Exit(_exit_code_for_error(e))

def _apply_compare_plugins(kernel, backend, textref, comp, lang):
    if backend: kernel.asr = registry.resolve_asr(backend.lower(), {"lang": lang})
    if textref: kernel.textref = registry.resolve_textref(textref.lower(), {"default_lang": lang})
    if comp: kernel.comp = registry.resolve_comparator(comp.lower(), {})

def _load_accent_data(show, lang):
    if not show: return None, [], [], None, lang
    try:
        prof = _try_load_accent_profile(lang)
        if not prof: return None, [], [], None, lang
        
        return _build_accent_data_bundle(prof, lang)
    except Exception: return None, [], [], None, lang

def _build_accent_data_bundle(prof, lang):
    accents = prof.get("accents", [])
    target_id = prof.get("target") or (accents[0].get("id") if accents else None)
    target_lang = _resolve_target_lang(accents, target_id, lang)
    return prof, accents, prof.get("features", []), target_id, target_lang

def _try_load_accent_profile(lang):
    l_key = lang.split("-")[0]
    return accent_analysis.load_profile(None).get("languages", {}).get(l_key, {})

def _resolve_target_lang(accents, target_id, def_lang):
    for acc in accents:
        if acc.get("id") == target_id:
            return acc.get("textref_lang", def_lang)
    return def_lang

async def _get_accent_payload(accents, features, target_id, hyp_tokens, kernel, lang, text):
    per_by_acc, acc_res, labels = {}, {}, {}
    for acc in accents:
        a_id = acc.get("id")
        if not a_id: continue
        labels[a_id] = acc.get("label", a_id)
        a_lang = acc.get("textref_lang", lang)
        a_ref = await _get_norm_ref(kernel, text, a_lang, lang)
        ares = await kernel.comp.compare(a_ref, hyp_tokens)
        acc_res[a_id], per_by_acc[a_id] = ares, ares["per"]
    
    ranking = accent_analysis.rank_accents(per_by_acc, labels)
    f_data = accent_analysis.extract_features(acc_res.get(target_id, {}).get("alignment", []) if target_id else [], features)
    return {"target": target_id, "ranking": ranking, "features": f_data}

async def _get_norm_ref(kernel, text, a_lang, def_lang):
    try: tr = await kernel.textref.to_ipa(text, lang=a_lang)
    except Exception: tr = await kernel.textref.to_ipa(text, lang=def_lang)
    norm = await kernel.pre.normalize_tokens(tr.get("tokens", []))
    return norm.get("tokens", [])

def _build_compare_res(p, t_lang, accents, features, t_id, kernel, show, def_lang, text):
    res = dict(p.result)
    res.update({"ref": {"tokens": p.ref_tokens, "ipa": " ".join(p.ref_tokens), "lang": t_lang},
                "hyp": {"tokens": p.hyp_tokens, "ipa": " ".join(p.hyp_tokens)},
                "feedback": accent_analysis.build_feedback(res.get("ops", []))})
    if show and accents:
        res["accent"] = asyncio.run(_get_accent_payload(accents, features, t_id, p.hyp_tokens, kernel, def_lang, text))
    return res

def _emit_compare_res(res, json_out, show_acc):
    if json_out: _emit_json(res)
    else:
        _print_compare_table(res)
        _print_feedback(res.get("feedback", []))
        if show_acc and "accent" in res:
            _print_accent_ranking(res["accent"].get("ranking", []))
            _print_accent_features(res["accent"].get("features", []))

def feedback(
    audio: str = typer.Option(..., "--audio", "-a"),
    text: str = typer.Option(..., "--text", "-t"),
    lang: str = typer.Option("es", "--lang", "-l"),
    mode: str = typer.Option("objective", "--mode"),
    evaluation_level: str = typer.Option("phonemic", "--evaluation"),
    model_pack: Optional[str] = typer.Option(None, "--model-pack"),
    llm_name: Optional[str] = typer.Option(None, "--llm"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Genera feedback LLM para un intento de pronunciación."""
    kernel = _get_kernel(model_pack, llm_name)
    try:
        wav_path, is_tmp = ensure_wav(audio)
        audio_in = to_audio_input(wav_path)
        
        async def _run():
            await kernel.setup()
            try: return await FeedbackService(kernel).analyze(audio=audio_in, text=text, lang=lang, mode=mode, evaluation_level=evaluation_level)
            finally: await kernel.teardown()
        
        with console.status("[bold green]Generating feedback..."):
            res = asyncio.run(_run())
        if json_output: _emit_json(res)
        else: _print_feedback_payload(res)
    except Exception as e:
        console.print(f"Error: {e}", style="red"); raise typer.Exit(1)
    finally:
        if is_tmp and wav_path: cleanup_temp(wav_path)
