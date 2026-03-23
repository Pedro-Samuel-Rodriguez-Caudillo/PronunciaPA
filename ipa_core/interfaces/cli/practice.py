from __future__ import annotations
import asyncio
import random
from typing import Optional, List, Any
from pathlib import Path
import typer
from rich.table import Table

from ipa_core.audio.files import ensure_wav
from ipa_core.audio.microphone import record
from ipa_core.backends.audio_io import to_audio_input
from ipa_core.ipa_catalog import load_catalog, normalize_lang, resolve_sound_entry
from ipa_core.services.comparison import ComparisonService
from ipa_core.services.feedback import FeedbackService
from ipa_core.services.error_report import build_enriched_error_report
from ipa_core.services.fallback import generate_fallback_feedback
from ipa_core.llm.utils import extract_json_object, validate_json_schema

from .helpers import (
    console, _COMPARE_MODES, _EVAL_LEVELS, _FEEDBACK_LEVELS, CatalogOutput,
    _prompt_lang, _prompt_sound, _prompt_context, _normalize_context,
    _prompt_count, _get_kernel, _normalize_sound, _build_confidence,
    _slugify, _build_request_payload, _emit_json, _sound_payload,
    _build_meta, _resolve_feedback_level, _print_feedback_payload,
    _IPA_SCHEMA_VERSION, _match_context
)

async def _generate_llm_candidates(kernel, lang, sound, context, count, before=None, after=None) -> List[str]:
    if not kernel.llm: return []
    
    prompt = _build_llm_prompt(sound, context, count, before, after)
    res = await kernel.llm.generate(prompt)
    return [w.strip() for w in res.split(",") if w.strip()][:count]

def _build_llm_prompt(sound, context, count, before, after) -> str:
    prompt = f"Genera {count} palabras que contengan /{sound.get('ipa')}/ en posición {context}."
    if context == "vowel-context":
        prompt += f" Entre las vocales {before or 'cualquiera'} y {after or 'cualquiera'}."
    return prompt

async def _validate_examples(kernel, lang, sound, context, candidates, before=None, after=None) -> List[dict]:
    validated = []
    for cand in candidates:
        text = cand.get("text")
        if not text: continue
        ipa_res = await kernel.textref.to_ipa(text, lang=lang)
        ipa = "".join(ipa_res.get("tokens", []))
        if _match_context(ipa, sound, context, before, after):
            validated.append({"text": text, "ipa": ipa, "context": context, "source": cand.get("source"), "validated": True})
    return validated

def _validate_args(inter, non_inter, audio, mic):
    if inter and non_inter: raise typer.BadParameter("interactive y non-interactive son excluyentes")
    if audio and mic: raise typer.BadParameter("audio y mic son excluyentes")

def _validate_modes(mode, eval_lvl, fb_lvl):
    if mode not in _COMPARE_MODES: raise typer.BadParameter(f"mode invalido: {mode}")
    if eval_lvl not in _EVAL_LEVELS: raise typer.BadParameter(f"evaluation invalido: {eval_lvl}")
    if fb_lvl and fb_lvl not in _FEEDBACK_LEVELS: raise typer.BadParameter(f"feedback-level invalido: {fb_lvl}")

def ipa_practice(
    lang: Optional[str] = typer.Option(None, "--lang", "-l"),
    sound: Optional[str] = typer.Option(None, "--sound", "-s"),
    context: Optional[str] = typer.Option(None, "--context", "-c"),
    count: int = typer.Option(10, "--count"),
    mode: str = typer.Option("phonetic", "--mode"),
    evaluation_level: str = typer.Option("phonetic", "--evaluation"),
    feedback_level: Optional[str] = typer.Option(None, "--feedback-level"),
    before: Optional[str] = typer.Option(None, "--before"),
    after: Optional[str] = typer.Option(None, "--after"),
    audio: Optional[str] = typer.Option(None, "--audio", "-a"),
    mic: bool = typer.Option(False, "--mic"),
    seconds: float = typer.Option(3.0, "--seconds"),
    loop: bool = typer.Option(False, "--loop"),
    example_index: Optional[int] = typer.Option(None, "--example-index"),
    output: CatalogOutput = typer.Option(CatalogOutput.human, "--output", "-o"),
    seed: Optional[int] = typer.Option(None, "--seed"),
    interactive: bool = typer.Option(False, "--interactive"),
    non_interactive: bool = typer.Option(False, "--non-interactive"),
    model_pack: Optional[str] = typer.Option(None, "--model-pack"),
    llm_name: Optional[str] = typer.Option(None, "--llm"),
    prompt_path: Optional[Path] = typer.Option(None, "--prompt-path"),
    output_schema_path: Optional[Path] = typer.Option(None, "--schema-path"),
):
    """Genera práctica por sonido y contexto."""
    _validate_args(interactive, non_interactive, audio, mic)
    _validate_modes(mode, evaluation_level, feedback_level)
    
    lang_key = _get_lang_key(lang, interactive, non_interactive)
    catalog = load_catalog(lang_key)
    
    entry = _resolve_sound_entry_with_prompt(sound, catalog, interactive, non_interactive)
    ctx_key = _get_context_key(context, entry, non_interactive)
    count = _prompt_count(count, non_interactive)
    
    kernel = _get_kernel(model_pack, llm_name)
    validated = _run_practice_session(kernel, lang_key, entry, ctx_key, count, before, after, seed)
    
    if not audio and not mic:
        _handle_no_audio_output(output, lang_key, entry, ctx_key, count, mode, evaluation_level, feedback_level, seed, validated, kernel)
        return

    _run_audio_evaluation(validated, loop, mic, non_interactive, example_index, seconds, audio, kernel, lang_key, mode, evaluation_level, feedback_level, prompt_path, output_schema_path, output)

def _resolve_sound_entry_with_prompt(sound, catalog, inter, non_inter):
    sound_q = _prompt_sound(sound, catalog, non_inter) if (inter or not sound) else sound
    entry = resolve_sound_entry(catalog, sound_q)
    if not entry:
        console.print(f"Error: sonido no encontrado: {sound_q}", style="red"); raise typer.Exit(1)
    return entry

def _get_lang_key(lang, inter, non_inter):
    return _prompt_lang(lang, non_inter) if (inter or not lang) else normalize_lang(lang)

def _get_context_key(ctx, entry, non_inter):
    raw = ctx or (_prompt_context(ctx, entry, non_inter) if not non_inter else _pick_default_context(entry))
    return _normalize_context(raw)

def _run_practice_session(kernel, lang, entry, ctx_key, count, before, after, seed):
    sound_ipa = _normalize_sound(entry.get("ipa", ""))
    seeds = entry.get("contexts", {}).get(ctx_key, {}).get("seeds", [])
    candidates = [{"text": s.get("text"), "source": "curated"} for s in seeds if isinstance(s, dict)]
    
    async def _run():
        await kernel.setup()
        try:
            extra = max(0, count - len(candidates))
            if extra:
                llm_items = await _generate_llm_candidates(kernel, lang, entry, ctx_key, extra, before, after)
                candidates.extend([{"text": i, "source": "llm"} for i in llm_items])
            res = await _validate_examples(kernel, lang, sound_ipa, ctx_key, candidates, before, after)
            if seed is not None: random.Random(seed).shuffle(res)
            return res
        finally: await kernel.teardown()
    
    res = asyncio.run(_run())
    if not res: console.print("No se encontraron ejemplos validados.", style="yellow"); raise typer.Exit(1)
    return res[:count]

def _handle_no_audio_output(output, lang, entry, ctx_key, count, mode, eval_lvl, fb_lvl, seed, validated, kernel):
    for item in validated:
        item["id"] = f"{entry.get('id')}/{item.get('context')}/{_slugify(item.get('text', ''))}"
    
    if output == CatalogOutput.json:
        _emit_json_practice(lang, entry, ctx_key, count, mode, eval_lvl, fb_lvl, seed, validated, kernel)
    else:
        _print_practice_table(entry, ctx_key, validated)

def _emit_json_practice(lang, entry, ctx_key, count, mode, eval_lvl, fb_lvl, seed, validated, kernel):
    req = _build_request_payload(lang=lang, sound=entry.get("ipa", ""), context=ctx_key, count=count, mode=mode, evaluation_level=eval_lvl, feedback_level=fb_lvl, seed=seed)
    conf, warnings = _build_confidence(mode, kernel.model_pack is not None)
    _emit_json({
        "schema_version": _IPA_SCHEMA_VERSION, "kind": "ipa.practice.set", "request": req, "sound": _sound_payload(entry),
        "items": [{k: v for k, v in i.items() if k in ["id", "text", "ipa", "position", "context", "source", "validated"]} for i in validated],
        "warnings": warnings, "confidence": conf, "meta": _build_meta(kernel),
    })

def _print_practice_table(entry, ctx_key, validated):
    console.print(f"Modo IPA ({entry.get('ipa')}) - contexto {ctx_key}", style="bold")
    table = Table(title="Practica sugerida")
    table.add_column("Texto", style="green"); table.add_column("IPA", style="cyan")
    for item in validated: table.add_row(str(item.get("text", "")), str(item.get("ipa", "")))
    console.print(table)

def _run_audio_evaluation(validated, loop, mic, non_inter, ex_idx, seconds, audio, kernel, lang, mode, eval_lvl, fb_lvl, prompt_p, schema_p, output):
    indices = _select_indices(validated, loop, non_inter, ex_idx)
    fb_lvl = _resolve_feedback_level(fb_lvl, eval_lvl)
    conf, warnings = _build_confidence(mode, kernel.model_pack is not None)

    for idx in indices:
        item = validated[idx]
        wav_path = _get_audio_path(item, mic, non_inter, seconds, audio)
        
        async def _eval():
            await kernel.setup()
            try:
                if kernel.llm:
                    return await FeedbackService(kernel).analyze(audio=to_audio_input(wav_path), text=item.get("text", ""), lang=lang, mode=mode, evaluation_level=eval_lvl, feedback_level=fb_lvl, prompt_path=prompt_p, output_schema_path=schema_p)
                return _run_fallback_eval(kernel, wav_path, item, lang, mode, eval_lvl, fb_lvl, conf, warnings)
            finally: await kernel.teardown()
        
        res = asyncio.run(_eval())
        _emit_practice_result(res, output, warnings)

def _select_indices(validated, loop, non_inter, ex_idx):
    if loop: return list(range(len(validated)))
    if ex_idx is not None: return _validate_example_index(ex_idx, len(validated))
    if non_inter: return [0]
    return [_prompt_example_index(validated)]

def _validate_example_index(idx, total):
    if idx < 0 or idx >= total: raise typer.BadParameter("example-index fuera de rango")
    return [idx]

def _prompt_example_index(validated):
    for i, item in enumerate(validated, start=1):
        console.print(f"{i}. {item.get('text')}")
    return int(typer.prompt("Selecciona ejemplo", default="1")) - 1

def _emit_practice_result(payload, output, warnings):
    if output == CatalogOutput.json:
        _emit_json(payload)
        return
    
    _print_warnings(warnings)
    _print_compare_metrics(payload)
    _print_feedback_payload(payload)
    _print_report_confidence(payload)

def _print_warnings(warnings):
    for w in warnings:
        console.print(w, style="yellow")

def _print_compare_metrics(payload):
    per = payload.get("compare", {}).get("per")
    if per is not None:
        console.print(f"PER: {per:.2%}")

def _print_report_confidence(payload):
    conf = payload.get("report", {}).get("confidence")
    if conf:
        console.print(f"Confiabilidad: {conf}")
