"""Fallback feedback generator using templates.

This module provides deterministic feedback when the LLM fails or
is not available. It generates useful phonetic advice based on
the error report without requiring an LLM.
"""
from __future__ import annotations

from typing import Any, Optional


# ========================================================================
# Templates for Spanish (default) - can be extended per language pack
# ========================================================================

TEMPLATES = {
    "es": {
        "perfect": "¡Excelente! Tu pronunciación es correcta.",
        "good": "Muy bien. Tienes una buena base, solo trata de ajustar un poco la posición de tu lengua o tus labios.",
        "needs_work": "Buen intento. Sin embargo, intenta observar la posición de tu lengua o tu apertura de boca para los sonidos marcados. Escucha con atención y trata de imitar.",
        "sub": "Sustituiste [{ref}] por [{hyp}]. Intenta cambiar la forma en la que posicionas tu lengua o tus labios para producir [{ref}] correctamente.",
        "ins": "Añadiste el sonido [{hyp}] donde no va. Trata de relajar la articulación y emitir un flujo de aire más limpio para evitar ese sonido extra.",
        "del": "Omitiste el sonido [{ref}]. Asegúrate de dar el esfuerzo necesario con tus labios y tu lengua para pronunciar todas las sílabas.",
        "drill_header": "Practica estos sonidos:",
        "no_errors": "No se detectaron errores significativos.",
    },
    "en": {
        "perfect": "Excellent! Your pronunciation is correct.",
        "good": "Good job. You have a solid base, just consider adjusting your tongue position or lip shape slightly.",
        "needs_work": "Nice try. However, try observing your tongue position or mouth opening for the marked sounds. Listen carefully and mimic.",
        "sub": "You substituted [{ref}] with [{hyp}]. Try changing how you place your tongue or lips to produce [{ref}] properly.",
        "ins": "You added the sound [{hyp}] where it doesn't belong. Try to relax your articulation and release a cleaner airflow to avoid that extra sound.",
        "del": "You omitted the sound [{ref}]. Make sure to put enough effort with your lips and tongue to pronounce all syllables.",
        "drill_header": "Practice these sounds:",
        "no_errors": "No significant errors detected.",
    },
}


def get_templates(lang: str) -> dict[str, str]:
    """Get templates for the given language, fallback to Spanish."""
    lang_key = lang.split("-")[0].lower()  # es-mx -> es
    return TEMPLATES.get(lang_key, TEMPLATES["es"])


def _resolve_feedback_level(error_report: dict[str, Any]) -> str:
    level = error_report.get("feedback_level")
    if not level:
        meta = error_report.get("meta") or {}
        if isinstance(meta, dict):
            level = meta.get("feedback_level")
    if level not in ("casual", "precise"):
        return "casual"
    return level


def _build_comparison_note(
    *,
    tone: str,
    per: float,
    counts: dict[str, int],
    evaluation_level: str,
    mode: str,
) -> str:
    errors = counts.get("sub", 0) + counts.get("ins", 0) + counts.get("del", 0)
    level_label = "fonetico" if evaluation_level == "phonetic" else "fonemico"
    if tone == "technical":
        return (
            "Comparacion tecnica: "
            f"PER {per * 100:.1f}%, errores {errors} "
            f"(sub {counts.get('sub', 0)}, ins {counts.get('ins', 0)}, del {counts.get('del', 0)}). "
            f"Nivel {level_label}, modo {mode}."
        )
    return (
        f"Comparacion general en nivel {level_label}. "
        "Enfocate en los sonidos marcados."
    )


class FallbackPayloadAdapter:
    """Aplica el patrón Adapter para transformar representaciones internas."""

    @staticmethod
    def adapt_drills(raw_drills: list[dict[str, Any]]) -> list[dict[str, str]]:
        adapted = []
        for d in raw_drills:
            adapted.append(_adapt_single_drill(d))
        return adapted

def _adapt_single_drill(d: dict[str, Any]) -> dict[str, str]:
    if d.get("type") == "contrast" and "pair" in d:
        ref, hyp = d["pair"]
        return {"type": "contrast", "text": f"Contraste {ref} vs {hyp}"}
    if d.get("type") == "practice" and "sound" in d:
        return {"type": "practice", "text": f"Práctica del sonido {d['sound']}"}
    return d # type: ignore


def generate_fallback_feedback(
    error_report: dict[str, Any],
    *,
    schema: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate deterministic feedback from an error report."""
    lang = error_report.get("lang", "es")
    templates = get_templates(lang)
    
    per = error_report.get("metrics", {}).get("per", 0.0)
    ops = error_report.get("ops", [])
    feedback_level = _resolve_feedback_level(error_report)
    tone = "technical" if feedback_level == "precise" else "friendly"
    
    counts = _count_ops(ops)
    summary, severity = _build_summary(templates, per, counts, error_report, tone)
    
    advice_long, drills = _build_advice_and_drills(ops, templates, counts, error_report, tone)
    
    feedback = {
        "summary": summary, "advice_short": summary, "advice_long": advice_long,
        "drills": FallbackPayloadAdapter.adapt_drills(drills[:5]),
        "severity": severity, "feedback_level": feedback_level,
        "tone": tone, "source": "fallback_templates",
    }
    
    if schema:
        _apply_schema_defaults(feedback, schema)
    return feedback


def _count_ops(ops: list[dict]) -> dict[str, int]:
    counts = {"eq": 0, "sub": 0, "ins": 0, "del": 0}
    for op in ops:
        op_type = op.get("op", "")
        if op_type in counts:
            counts[op_type] += 1
    return counts


def _build_summary(templates, per, counts, error_report, tone) -> tuple[str, str]:
    if tone == "technical":
        return _build_technical_summary(per, counts, error_report)
    return _build_friendly_summary(per, templates)


def _build_technical_summary(per, counts, error_report) -> tuple[str, str]:
    eval_lvl = error_report.get("evaluation_level", "phonemic")
    lvl_label = "fonetico" if eval_lvl == "phonetic" else "fonemico"
    err_count = counts["sub"] + counts["ins"] + counts["del"]
    summary = f"PER {per * 100:.1f}%, errores {err_count}. Nivel {lvl_label}."
    return summary, "needs_work" if per >= 0.15 else "good"


def _build_friendly_summary(per, templates) -> tuple[str, str]:
    if per == 0.0: return templates["perfect"], "perfect"
    if per < 0.15: return templates["good"], "good"
    return templates["needs_work"], "needs_work"


def _get_hints_text(phone: str, prefix: str = "") -> str:
    try:
        from ipa_core.analysis.drill_generator import _build_hints
    except ImportError:
        return ""
    
    hints = _build_hints(phone)
    return f"{prefix} {' '.join(hints)}" if hints else ""


def _build_advice_and_drills(ops, templates, counts, error_report, tone) -> tuple[str, list]:
    advice_lines, drills = [], []
    shown = {"sub": 0, "ins": 0, "del": 0}
    
    for op in ops:
        _process_op_advice(op, tone, templates, advice_lines, drills, shown)

    if not advice_lines:
        advice_lines.append(templates["no_errors"])
    else:
        note = _build_comparison_note(
            tone=tone, per=error_report.get("metrics", {}).get("per", 0.0),
            counts=counts, evaluation_level=error_report.get("evaluation_level", "phonemic"),
            mode=error_report.get("mode", "objective")
        )
        advice_lines.insert(0, note)
    
    return "\n".join(advice_lines), drills


def _process_op_advice(op, tone, templates, advice_lines, drills, shown):
    op_type = op.get("op", "")
    ref, hyp = op.get("ref", ""), op.get("hyp", "")
    
    if op_type == "sub":
        _handle_sub_op(ref, hyp, tone, templates, advice_lines, drills, shown)
    elif op_type == "ins":
        _handle_ins_op(hyp, tone, templates, advice_lines, shown)
    elif op_type == "del":
        _handle_del_op(ref, tone, templates, advice_lines, drills, shown)


def _handle_sub_op(ref, hyp, tone, templates, advice_lines, drills, shown):
    if shown["sub"] < 3:
        _add_sub_advice(ref, hyp, tone, templates, advice_lines, drills)
        shown["sub"] += 1


def _handle_ins_op(hyp, tone, templates, advice_lines, shown):
    if shown["ins"] < 2:
        _add_ins_advice(hyp, tone, templates, advice_lines)
        shown["ins"] += 1


def _handle_del_op(ref, tone, templates, advice_lines, drills, shown):
    if shown["del"] < 2:
        _add_del_advice(ref, tone, templates, advice_lines, drills)
        shown["del"] += 1


def _add_sub_advice(ref, hyp, tone, templates, advice_lines, drills):
    if tone == "technical":
        advice_lines.append(f"sub {ref}->{hyp}")
    else:
        h_str = f" {_get_hints_text(hyp, 'Posiblemente lo hiciste así: ')} {_get_hints_text(ref, 'Debería ser: ')}".strip()
        advice_lines.append(templates["sub"].format(ref=ref, hyp=hyp) + (f" ({h_str})" if h_str else ""))
    drills.append({"type": "contrast", "pair": [ref, hyp]})


def _add_ins_advice(hyp, tone, templates, advice_lines):
    if tone == "technical":
        advice_lines.append(f"ins {hyp}")
    else:
        h_str = _get_hints_text(hyp, "Posiblemente moviste tus articuladores así: ")
        advice_lines.append(templates["ins"].format(hyp=hyp) + (f" ({h_str})" if h_str else ""))


def _add_del_advice(ref, tone, templates, advice_lines, drills):
    if tone == "technical":
        advice_lines.append(f"del {ref}")
    else:
        h_str = _get_hints_text(ref, "Para no omitirlo, intenta: ")
        advice_lines.append(templates["del"].format(ref=ref) + (f" ({h_str})" if h_str else ""))
    drills.append({"type": "practice", "sound": ref})


def _apply_schema_defaults(feedback, schema):
    properties = schema.get("properties", {})
    for key, rule in properties.items():
        if key not in feedback:
            feedback[key] = _default_for_type(rule.get("type", "string"))


def _default_for_type(t: str) -> Any:
    if t == "array": return []
    if t == "object": return {}
    if t in ("number", "integer"): return 0
    if t == "boolean": return False
    return ""


def can_use_fallback(error_report: dict[str, Any]) -> bool:
    """Check if the error report has enough data for fallback."""
    return bool(error_report.get("ops")) or bool(error_report.get("metrics"))


__all__ = [
    "generate_fallback_feedback",
    "can_use_fallback",
    "get_templates",
    "TEMPLATES",
]
