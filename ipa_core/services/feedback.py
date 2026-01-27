"""Feedback service: compare + error report + LLM feedback."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.llm.utils import extract_json_object, load_json, load_text, validate_json_schema
from ipa_core.services.fallback import generate_fallback_feedback
from ipa_core.services.error_report import build_enriched_error_report
from ipa_core.kernel.core import Kernel
from ipa_core.packs.schema import ModelPack
from ipa_core.types import AudioInput, CompareResult, Token


def build_error_report(
    *,
    target_text: str,
    target_tokens: list[Token],
    hyp_tokens: list[Token],
    compare_result: CompareResult,
    lang: str,
    mode: str = "objective",
    evaluation_level: str = "phonemic",
    feedback_level: Optional[str] = None,
    confidence: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the canonical Error Report JSON for the LLM.
    
    Uses the enriched error report with articulatory features
    for better pedagogical feedback generation.
    """
    return build_enriched_error_report(
        target_text=target_text,
        target_tokens=target_tokens,
        hyp_tokens=hyp_tokens,
        compare_result=compare_result,
        lang=lang,
        mode=mode,
        evaluation_level=evaluation_level,
        feedback_level=feedback_level,
        confidence=confidence,
        warnings=warnings,
        meta=meta,
    )


async def generate_feedback(
    report: dict[str, Any],
    *,
    llm,
    model_pack: ModelPack,
    model_pack_dir: Path,
    retry: bool = True,
    prompt_path: Optional[Path] = None,
    output_schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Generate LLM feedback from an Error Report."""
    prompt = _build_prompt(report, model_pack, model_pack_dir, prompt_path=prompt_path)
    output_schema = _load_output_schema(
        model_pack,
        model_pack_dir,
        output_schema_path=output_schema_path,
    )
    raw = await llm.complete(prompt, params=model_pack.params)
    try:
        payload = extract_json_object(raw)
        validate_json_schema(payload, output_schema)
        return payload
    except ValidationError:
        if not retry:
            raise
    # Retry once with a stricter instruction.
    fix_prompt = prompt + "\nReturn ONLY valid JSON. Fix any schema violations.\n"
    raw = await llm.complete(fix_prompt, params=model_pack.params)
    try:
        payload = extract_json_object(raw)
        validate_json_schema(payload, output_schema)
        return payload
    except ValidationError:
        return generate_fallback_feedback(report, schema=output_schema)


class FeedbackService:
    """Orchestrates audio comparison and LLM feedback."""

    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    async def analyze(
        self,
        *,
        audio: AudioInput,
        text: str,
        lang: str,
        mode: str = "objective",
        evaluation_level: str = "phonemic",
        feedback_level: Optional[str] = None,
        prompt_path: Optional[Path] = None,
        output_schema_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        if not self._kernel.llm or not self._kernel.model_pack or not self._kernel.model_pack_dir:
            raise NotReadyError("LLM/model pack not configured.")

        context = _build_feedback_context(
            evaluation_level=evaluation_level,
            feedback_level=feedback_level,
            pack_used=bool(self._kernel.model_pack),
        )
        pre_audio_res = await self._kernel.pre.process_audio(audio)
        processed_audio = pre_audio_res.get("audio", audio)
        asr_result = await self._kernel.asr.transcribe(processed_audio, lang=lang)
        hyp_tokens = asr_result.get("tokens")
        if not hyp_tokens:
            raise ValidationError("ASR no devolvio tokens IPA.")
        hyp_pre_res = await self._kernel.pre.normalize_tokens(hyp_tokens)
        hyp_tokens = hyp_pre_res.get("tokens", [])

        tr_result = await self._kernel.textref.to_ipa(text, lang=lang)
        ref_pre_res = await self._kernel.pre.normalize_tokens(tr_result.get("tokens", []))
        ref_tokens = ref_pre_res.get("tokens", [])

        compare_res = await self._kernel.comp.compare(ref_tokens, hyp_tokens)
        compare_payload = dict(compare_res)
        report = build_error_report(
            target_text=text,
            target_tokens=ref_tokens,
            hyp_tokens=hyp_tokens,
            compare_result=compare_res,
            lang=lang,
            mode=mode,
            evaluation_level=evaluation_level,
            feedback_level=context["feedback_level"],
            confidence=context["confidence"],
            warnings=context["warnings"],
            meta={
                "asr": asr_result.get("meta", {}),
                "feedback_level": context["feedback_level"],
                "tone": context["tone"],
                "confidence": context["confidence"],
                "warnings": context["warnings"],
            },
        )
        feedback = await generate_feedback(
            report,
            llm=self._kernel.llm,
            model_pack=self._kernel.model_pack,
            model_pack_dir=self._kernel.model_pack_dir,
            prompt_path=prompt_path,
            output_schema_path=output_schema_path,
        )
        compare_payload.setdefault("mode", mode)
        compare_payload.setdefault("evaluation_level", evaluation_level)
        compare_payload.setdefault("score", report.get("metrics", {}).get("score"))
        feedback_payload = _apply_feedback_context(feedback, context=context)
        return {
            "report": report,
            "compare": compare_payload,
            "feedback": feedback_payload,
        }


def _resolve_feedback_level(
    feedback_level: Optional[str],
    evaluation_level: str,
) -> str:
    if feedback_level in ("casual", "precise"):
        return feedback_level
    if evaluation_level == "phonetic":
        return "precise"
    return "casual"


def _build_feedback_context(
    *,
    evaluation_level: str,
    feedback_level: Optional[str],
    pack_used: bool = False,
) -> dict[str, Any]:
    level = _resolve_feedback_level(feedback_level, evaluation_level)
    tone = "technical" if level == "precise" else "friendly"
    warnings: list[str] = []
    confidence = "normal"
    if evaluation_level == "phonetic" and not pack_used:
        warnings.append(
            "Aviso: modo fonetico sin pack; confiabilidad baja, comparacion aproximada para IPA general."
        )
        confidence = "low"
    return {
        "feedback_level": level,
        "tone": tone,
        "warnings": warnings,
        "confidence": confidence,
    }


def _apply_feedback_context(
    feedback: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(feedback or {})
    payload.setdefault("feedback_level", context.get("feedback_level"))
    payload.setdefault("tone", context.get("tone"))
    payload.setdefault("confidence", context.get("confidence"))
    warnings = context.get("warnings") or []
    if warnings:
        existing = payload.get("warnings")
        if isinstance(existing, list):
            for warning in warnings:
                if warning not in existing:
                    existing.append(warning)
        else:
            payload["warnings"] = warnings
        warning_text = warnings[0]
        summary = payload.get("summary")
        if isinstance(summary, str) and warning_text not in summary:
            payload["summary"] = f"{warning_text} {summary}"
        else:
            advice_short = payload.get("advice_short")
            if isinstance(advice_short, str) and warning_text not in advice_short:
                payload["advice_short"] = f"{warning_text} {advice_short}"
            elif not summary:
                payload["summary"] = warning_text
    return payload


def _build_prompt(
    report: dict[str, Any],
    model_pack: ModelPack,
    base_dir: Path,
    *,
    prompt_path: Optional[Path] = None,
) -> str:
    prompt_text = ""
    if prompt_path:
        prompt_text = load_text(prompt_path)
    elif model_pack.prompt:
        prompt_path = model_pack.prompt.resolve_path(base_dir)
        prompt_text = load_text(prompt_path)
    payload = json.dumps(report, ensure_ascii=True)
    return f"{prompt_text}\n\nINPUT_JSON:\n{payload}\nOUTPUT_JSON:\n"


def _load_output_schema(
    model_pack: ModelPack,
    base_dir: Path,
    *,
    output_schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    if output_schema_path:
        return load_json(output_schema_path)
    if not model_pack.output_schema:
        raise ValidationError("Model pack is missing output_schema.")
    schema_path = model_pack.output_schema.resolve_path(base_dir)
    return load_json(schema_path)
