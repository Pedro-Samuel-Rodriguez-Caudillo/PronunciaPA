"""Feedback service: compare + error report + LLM feedback."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.llm.utils import build_fallback, extract_json_object, load_json, load_text, validate_json_schema
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
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the canonical Error Report JSON for the LLM."""
    return {
        "target_text": target_text,
        "target_ipa": " ".join(target_tokens),
        "observed_ipa": " ".join(hyp_tokens),
        "metrics": {"per": compare_result.get("per")},
        "ops": compare_result.get("ops", []),
        "alignment": compare_result.get("alignment", []),
        "lang": lang,
        "meta": meta or {},
    }


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
        return build_fallback(output_schema, summary="Feedback no disponible.")


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
        prompt_path: Optional[Path] = None,
        output_schema_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        if not self._kernel.llm or not self._kernel.model_pack or not self._kernel.model_pack_dir:
            raise NotReadyError("LLM/model pack not configured.")

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
        report = build_error_report(
            target_text=text,
            target_tokens=ref_tokens,
            hyp_tokens=hyp_tokens,
            compare_result=compare_res,
            lang=lang,
            meta={"asr": asr_result.get("meta", {})},
        )
        feedback = await generate_feedback(
            report,
            llm=self._kernel.llm,
            model_pack=self._kernel.model_pack,
            model_pack_dir=self._kernel.model_pack_dir,
            prompt_path=prompt_path,
            output_schema_path=output_schema_path,
        )
        return {
            "report": report,
            "compare": compare_res,
            "feedback": feedback,
        }


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
