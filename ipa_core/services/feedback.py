"""Feedback service: compare + error report + LLM feedback."""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.llm.utils import extract_json_object, load_json, load_text, validate_json_schema
from ipa_core.services.fallback import generate_fallback_feedback
from ipa_core.services.error_report import build_enriched_error_report
from ipa_core.services.audio_quality import assess_audio_quality
from ipa_core.services.adaptation import adapt_settings
from ipa_core.kernel.core import Kernel
from ipa_core.packs.schema import ModelPack
from ipa_core.types import AudioInput, CompareResult, Token
from ipa_core.normalization.resolve import load_inventory_for
from ipa_core.services.user_profile import UserAudioProfile

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedbackGenerationAssets:
    prompt: str
    output_schema: dict[str, Any]
    llm_params: dict[str, Any]


@dataclass(frozen=True)
class FeedbackRuntimeContext:
    quality_res: Any
    profile_meta: Optional[dict[str, Any]]
    inventory: Any
    pack_id: Optional[str]
    allophone_rules: Optional[dict[str, Any]]
    effective_mode: str
    effective_level: str
    adaptive_meta: dict[str, Any]
    context: dict[str, Any]
    roadmap_progress: dict[str, Any]


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


def _normalize_llm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce common LLM formatting quirks to match the output schema.

    Some small models return ``drills[].text`` as a list instead of a string.
    This normalises it in-place so schema validation doesn't fail.
    """
    drills = payload.get("drills")
    if isinstance(drills, list):
        for drill in drills:
            if isinstance(drill, dict) and isinstance(drill.get("text"), list):
                drill["text"] = " / ".join(str(t) for t in drill["text"])
    return payload


async def generate_feedback(
    report: dict[str, Any],
    *,
    llm,
    model_pack: Optional[ModelPack] = None,
    model_pack_dir: Optional[Path] = None,
    retry: bool = True,
    prompt_path: Optional[Path] = None,
    output_schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Generate LLM feedback from an Error Report.

    Cuando ``llm`` es un ``RuleBasedFeedbackAdapter`` (``llm.rule_based``
    es True), el reporte se pasa directamente como JSON y no se requiere
    ``model_pack`` ni ``model_pack_dir``.
    """
    # Path de respaldo basado en reglas: no requiere model_pack ni prompt
    if getattr(llm, "rule_based", False):
        raw = await llm.complete(json.dumps(report, ensure_ascii=False), params={})
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return generate_fallback_feedback(report)

    # Path LLM normal: requiere model_pack
    if model_pack is None or model_pack_dir is None:
        raise ValidationError("model_pack y model_pack_dir son requeridos para LLM.")

    assets = _resolve_feedback_generation_assets(
        report,
        model_pack,
        model_pack_dir,
        prompt_path=prompt_path,
        output_schema_path=output_schema_path,
    )
    raw = await llm.complete(assets.prompt, params=assets.llm_params)
    try:
        payload = _normalize_llm_payload(extract_json_object(raw))
        validate_json_schema(payload, assets.output_schema)
        return payload
    except ValidationError:
        if not retry:
            raise
    # Retry once with a stricter instruction.
    fix_prompt = assets.prompt + "\nReturn ONLY valid JSON. Fix any schema violations.\n"
    raw = await llm.complete(fix_prompt, params=assets.llm_params)
    try:
        payload = _normalize_llm_payload(extract_json_object(raw))
        validate_json_schema(payload, assets.output_schema)
        return payload
    except ValidationError:
        return generate_fallback_feedback(report, schema=assets.output_schema)


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
        lang_source: Optional[str] = None,
        lang_target: Optional[str] = None,
        target_ipa: Optional[str] = None,
        mode: str = "objective",
        evaluation_level: str = "phonemic",
        force_phonetic: Optional[bool] = None,
        allow_quality_downgrade: Optional[bool] = None,
        feedback_level: Optional[str] = None,
        prompt_path: Optional[Path] = None,
        output_schema_path: Optional[Path] = None,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        effective_source_lang = lang_source or lang
        effective_target_lang = lang_target or lang

        _ensure_feedback_kernel_ready(self._kernel)
        runtime = await _prepare_feedback_runtime_context(
            kernel=self._kernel,
            audio=audio,
            user_id=user_id,
            lang=effective_target_lang,
            mode=mode,
            evaluation_level=evaluation_level,
            force_phonetic=force_phonetic,
            allow_quality_downgrade=allow_quality_downgrade,
            feedback_level=feedback_level,
        )

        pre_audio_res = await self._kernel.pre.process_audio(audio)
        processed_audio = pre_audio_res.get("audio", audio)
        asr_result = await self._kernel.asr.transcribe(processed_audio, lang=effective_source_lang)
        hyp_tokens = asr_result.get("tokens")
        if not hyp_tokens:
            raise ValidationError("ASR no devolvio tokens IPA.")
        hyp_pre_res = await self._kernel.pre.normalize_tokens(
            hyp_tokens,
            inventory=runtime.inventory,
            allophone_rules=runtime.allophone_rules,
        )
        hyp_tokens = hyp_pre_res.get("tokens", [])
        hyp_oov = hyp_pre_res.get("meta", {}).get("oov_tokens", [])
        if hyp_oov:
            preview = ", ".join(hyp_oov[:6])
            runtime.context["warnings"] = list(dict.fromkeys((runtime.context.get("warnings") or []) + [
                f"Tokens IPA fuera del inventario: {preview}",
            ]))

        if target_ipa and target_ipa.strip():
            ref_tokens_raw = [tok for tok in target_ipa.strip().split() if tok]
        else:
            tr_result = await self._kernel.textref.to_ipa(text, lang=effective_target_lang)
            ref_tokens_raw = tr_result.get("tokens", [])

        ref_pre_res = await self._kernel.pre.normalize_tokens(
            ref_tokens_raw,
            inventory=runtime.inventory,
            allophone_rules=runtime.allophone_rules,
        )
        ref_tokens = ref_pre_res.get("tokens", [])

        compare_res = await self._kernel.comp.compare(ref_tokens, hyp_tokens)
        compare_payload = _build_compare_payload(
            compare_result=compare_res,
            hyp_tokens=hyp_tokens,
            ref_tokens=ref_tokens,
            mode=runtime.effective_mode,
            evaluation_level=runtime.effective_level,
            quality_res=runtime.quality_res,
            inventory_used=bool(runtime.inventory),
            pack_id=runtime.pack_id,
            hyp_pre_meta=hyp_pre_res.get("meta", {}),
            context=runtime.context,
            adaptive_meta=runtime.adaptive_meta,
            profile_meta=runtime.profile_meta,
        )

        report = build_error_report(
            target_text=text,
            target_tokens=ref_tokens,
            hyp_tokens=hyp_tokens,
            compare_result=compare_res,
            lang=effective_target_lang,
            mode=runtime.effective_mode,
            evaluation_level=runtime.effective_level,
            feedback_level=runtime.context["feedback_level"],
            confidence=runtime.context["confidence"],
            warnings=runtime.context.get("warnings"),
            meta=_build_report_meta(
                asr_meta=asr_result.get("meta", {}),
                context=runtime.context,
                quality_res=runtime.quality_res,
                inventory_used=bool(runtime.inventory),
                pack_id=runtime.pack_id,
                hyp_pre_meta=hyp_pre_res.get("meta", {}),
                adaptive_meta=runtime.adaptive_meta,
                profile_meta=runtime.profile_meta,
                roadmap_progress=runtime.roadmap_progress,
                lang_source=effective_source_lang,
                lang_target=effective_target_lang,
                target_ipa_manual=bool(target_ipa and target_ipa.strip()),
            ),
        )
        feedback = await generate_feedback(
            report,
            llm=self._kernel.llm,
            model_pack=self._kernel.model_pack or None,
            model_pack_dir=self._kernel.model_pack_dir or None,
            prompt_path=prompt_path,
            output_schema_path=output_schema_path,
        )
        feedback_payload = _apply_feedback_context(feedback, context=runtime.context)

        await _persist_feedback_attempt(
            kernel=self._kernel,
            user_id=user_id,
            lang=effective_target_lang,
            text=text,
            compare_payload=compare_payload,
            compare_result=compare_res,
            effective_mode=runtime.effective_mode,
            effective_level=runtime.effective_level,
            feedback_level=runtime.context["feedback_level"],
        )

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


def _ensure_feedback_kernel_ready(kernel: Kernel) -> None:
    if not kernel.llm:
        raise NotReadyError("LLM not configured.")
    if not _is_rule_based_llm(kernel.llm) and (not kernel.model_pack or not kernel.model_pack_dir):
        raise NotReadyError("LLM/model pack not configured.")


def _is_rule_based_llm(llm: Any) -> bool:
    return bool(getattr(llm, "rule_based", False))


async def _prepare_feedback_runtime_context(
    *,
    kernel: Kernel,
    audio: AudioInput,
    user_id: Optional[str],
    lang: str,
    mode: str,
    evaluation_level: str,
    force_phonetic: Optional[bool],
    allow_quality_downgrade: Optional[bool],
    feedback_level: Optional[str],
) -> FeedbackRuntimeContext:
    roadmap_progress = await _load_roadmap_progress(kernel, user_id, lang)
    quality_res, quality_warnings, profile_meta = assess_audio_quality(
        audio.get("path"),
        user_id=user_id,
    )
    profile = _profile_from_meta(profile_meta)
    inventory, pack_id = _load_feedback_inventory(kernel, lang)
    effective_mode, effective_level, adaptive_meta = adapt_settings(
        requested_mode=mode,
        requested_level=evaluation_level,
        quality=quality_res,
        profile=profile,
        force_phonetic=force_phonetic,
        allow_quality_downgrade=allow_quality_downgrade,
    )
    context = _build_feedback_context(
        evaluation_level=effective_level,
        feedback_level=feedback_level,
        pack_used=bool(inventory),
    )
    context = _merge_feedback_warnings(
        context,
        quality_warnings=quality_warnings,
        quality_res=quality_res,
    )
    return FeedbackRuntimeContext(
        quality_res=quality_res,
        profile_meta=profile_meta,
        inventory=inventory,
        pack_id=pack_id,
        allophone_rules=_resolve_allophone_rules(inventory, effective_level),
        effective_mode=effective_mode,
        effective_level=effective_level,
        adaptive_meta=adaptive_meta,
        context=context,
        roadmap_progress=roadmap_progress,
    )


async def _load_roadmap_progress(
    kernel: Kernel,
    user_id: Optional[str],
    lang: str,
) -> dict[str, Any]:
    if not user_id or not kernel.history:
        return {}
    try:
        return await kernel.history.get_roadmap_progress(user_id, lang)
    except Exception:
        logger.debug("No se pudo obtener roadmap_progress para user=%s", user_id)
        return {}


def _profile_from_meta(profile_meta: Optional[dict[str, Any]]) -> Optional[UserAudioProfile]:
    if profile_meta and isinstance(profile_meta.get("profile"), dict):
        return UserAudioProfile.from_dict(profile_meta["profile"])
    return None


def _load_feedback_inventory(kernel: Kernel, lang: str) -> tuple[Any, Optional[str]]:
    pack_hint = None
    if kernel.language_pack:
        pack_hint = getattr(kernel.language_pack, "id", None) or getattr(kernel.language_pack, "dialect", None)
    return load_inventory_for(lang=lang, pack=pack_hint)


def _resolve_allophone_rules(inventory: Any, evaluation_level: str) -> Optional[dict[str, Any]]:
    if inventory and evaluation_level == "phonemic":
        return inventory.allophone_collapse
    return None


def _merge_feedback_warnings(
    context: dict[str, Any],
    *,
    quality_warnings: list[str],
    quality_res: Any,
) -> dict[str, Any]:
    merged = dict(context)
    if quality_warnings:
        merged["warnings"] = list(dict.fromkeys(merged.get("warnings", []) + quality_warnings))
    if quality_res and not quality_res.passed:
        merged["confidence"] = "low"
    return merged


async def _persist_feedback_attempt(
    *,
    kernel: Kernel,
    user_id: Optional[str],
    lang: str,
    text: str,
    compare_payload: dict[str, Any],
    compare_result: CompareResult,
    effective_mode: str,
    effective_level: str,
    feedback_level: str,
) -> None:
    if not user_id or not kernel.history:
        return

    try:
        score_val = float(compare_payload.get("score") or 0.0)
        per_val = float(compare_result.get("per", 1.0))
        ops_val: list[dict[str, Any]] = list(compare_result.get("ops", []))
        await kernel.history.record_attempt(
            user_id=user_id,
            lang=lang,
            text=text,
            score=score_val,
            per=per_val,
            ops=ops_val,
            meta={
                "mode": effective_mode,
                "evaluation_level": effective_level,
                "feedback_level": feedback_level,
            },
        )
        from ipa_core.services.lesson import update_roadmap  # noqa: PLC0415
        await update_roadmap(user_id, lang, kernel)
    except Exception as exc:
        logger.warning("Error en auto-persistencia de historial: %s", exc)


def _resolve_feedback_generation_assets(
    report: dict[str, Any],
    model_pack: ModelPack,
    base_dir: Path,
    *,
    prompt_path: Optional[Path] = None,
    output_schema_path: Optional[Path] = None,
) -> FeedbackGenerationAssets:
    return FeedbackGenerationAssets(
        prompt=_build_prompt(report, model_pack, base_dir, prompt_path=prompt_path),
        output_schema=_load_output_schema(
            model_pack,
            base_dir,
            output_schema_path=output_schema_path,
        ),
        llm_params=dict(model_pack.params or {}),
    )


def _build_compare_payload(
    *,
    compare_result: CompareResult,
    hyp_tokens: list[Token],
    ref_tokens: list[Token],
    mode: str,
    evaluation_level: str,
    quality_res: Any,
    inventory_used: bool,
    pack_id: Optional[str],
    hyp_pre_meta: dict[str, Any],
    context: dict[str, Any],
    adaptive_meta: dict[str, Any],
    profile_meta: Optional[dict[str, Any]],
) -> dict[str, Any]:
    compare_payload = dict(compare_result)
    compare_payload["ipa"] = " ".join(hyp_tokens)
    compare_payload["tokens"] = list(hyp_tokens)
    compare_payload["target_ipa"] = " ".join(ref_tokens)
    compare_payload.setdefault("mode", mode)
    compare_payload.setdefault("evaluation_level", evaluation_level)
    compare_payload["score"] = max(
        0.0,
        (1.0 - float(compare_result.get("per", 0.0) or 0.0)) * 100.0,
    )
    compare_payload.setdefault("meta", {})
    if quality_res:
        compare_payload["meta"]["audio_quality"] = quality_res.to_dict()
    if inventory_used:
        compare_payload["meta"]["normalization"] = {
            "pack": pack_id,
            "oov_tokens": hyp_pre_meta.get("oov_tokens", []),
        }
    if context.get("warnings"):
        compare_payload["meta"]["warnings"] = context["warnings"]
    compare_payload["meta"]["adaptive"] = adaptive_meta
    if profile_meta:
        compare_payload["meta"]["user_profile"] = profile_meta
    return compare_payload


def _build_report_meta(
    *,
    asr_meta: dict[str, Any],
    context: dict[str, Any],
    quality_res: Any,
    inventory_used: bool,
    pack_id: Optional[str],
    hyp_pre_meta: dict[str, Any],
    adaptive_meta: dict[str, Any],
    profile_meta: Optional[dict[str, Any]],
    roadmap_progress: dict[str, Any],
    lang_source: Optional[str] = None,
    lang_target: Optional[str] = None,
    target_ipa_manual: bool = False,
) -> dict[str, Any]:
    return {
        "asr": asr_meta,
        "feedback_level": context["feedback_level"],
        "tone": context["tone"],
        "confidence": context["confidence"],
        "warnings": context.get("warnings"),
        "audio_quality": quality_res.to_dict() if quality_res else {},
        "normalization": {
            "pack": pack_id,
            "oov_tokens": hyp_pre_meta.get("oov_tokens", []),
        } if inventory_used else {},
        "adaptive": adaptive_meta,
        "lang_source": lang_source,
        "lang_target": lang_target,
        "target_ipa_manual": target_ipa_manual,
        "user_profile": profile_meta or {},
        "roadmap_context": roadmap_progress or {},
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
