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
        "good": "Muy bien. Solo pequeños detalles por mejorar.",
        "needs_work": "Buen intento. Enfócate en los sonidos marcados.",
        "sub": "Sustituiste [{ref}] por [{hyp}]. Intenta articular más claramente.",
        "ins": "Añadiste el sonido [{hyp}] donde no va. Intenta ser más preciso.",
        "del": "Omitiste el sonido [{ref}]. Asegúrate de pronunciar todas las sílabas.",
        "drill_header": "Practica estos sonidos:",
        "no_errors": "No se detectaron errores significativos.",
    },
    "en": {
        "perfect": "Excellent! Your pronunciation is correct.",
        "good": "Good job. Just minor details to improve.",
        "needs_work": "Nice try. Focus on the marked sounds.",
        "sub": "You substituted [{ref}] with [{hyp}]. Try to articulate more clearly.",
        "ins": "You added the sound [{hyp}] where it doesn't belong. Try to be more precise.",
        "del": "You omitted the sound [{ref}]. Make sure to pronounce all syllables.",
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


def generate_fallback_feedback(
    error_report: dict[str, Any],
    *,
    schema: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate deterministic feedback from an error report.

    Args:
        error_report: The canonical error report with ops, alignment, etc.
        schema: Optional output schema to match structure.

    Returns:
        A feedback dict with advice_short, advice_long, drills, etc.
    """
    lang = error_report.get("lang", "es")
    templates = get_templates(lang)
    
    per = error_report.get("metrics", {}).get("per", 0.0)
    ops = error_report.get("ops", [])
    mode = error_report.get("mode", "objective")
    evaluation_level = error_report.get("evaluation_level", "phonemic")
    feedback_level = _resolve_feedback_level(error_report)
    tone = "technical" if feedback_level == "precise" else "friendly"
    
    counts = {"eq": 0, "sub": 0, "ins": 0, "del": 0}
    for op in ops:
        op_type = op.get("op", "")
        if op_type in counts:
            counts[op_type] += 1
    error_count = counts["sub"] + counts["ins"] + counts["del"]
    
    # Determine overall feedback based on PER
    if tone == "technical":
        level_label = "fonetico" if evaluation_level == "phonetic" else "fonemico"
        summary = (
            f"PER {per * 100:.1f}%, errores {error_count}. Nivel {level_label}."
        )
        severity = "needs_work" if per >= 0.15 else "good"
    else:
        if per == 0.0:
            summary = templates["perfect"]
            severity = "perfect"
        elif per < 0.15:
            summary = templates["good"]
            severity = "good"
        else:
            summary = templates["needs_work"]
            severity = "needs_work"
    
    # Build detailed advice from operations
    advice_lines = []
    drills = []
    shown = {"sub": 0, "ins": 0, "del": 0}
    
    for op in ops:
        op_type = op.get("op", "")
        ref = op.get("ref", "")
        hyp = op.get("hyp", "")
        
        if op_type == "sub" and shown["sub"] < 3:
            if tone == "technical":
                advice_lines.append(f"sub {ref}->{hyp}")
            else:
                advice_lines.append(
                    templates["sub"].format(ref=ref, hyp=hyp)
                )
            drills.append({"type": "contrast", "pair": [ref, hyp]})
            shown["sub"] += 1
            
        elif op_type == "ins" and shown["ins"] < 2:
            if tone == "technical":
                advice_lines.append(f"ins {hyp}")
            else:
                advice_lines.append(
                    templates["ins"].format(hyp=hyp)
                )
            shown["ins"] += 1
            
        elif op_type == "del" and shown["del"] < 2:
            if tone == "technical":
                advice_lines.append(f"del {ref}")
            else:
                advice_lines.append(
                    templates["del"].format(ref=ref)
                )
            drills.append({"type": "practice", "sound": ref})
            shown["del"] += 1

    if not advice_lines:
        advice_lines.append(templates["no_errors"])
    else:
        comparison_note = _build_comparison_note(
            tone=tone,
            per=per,
            counts=counts,
            evaluation_level=evaluation_level,
            mode=mode,
        )
        advice_lines.insert(0, comparison_note)
    
    advice_long = "\n".join(advice_lines)
    
    # Build the feedback payload
    feedback = {
        "summary": summary,
        "advice_short": summary,
        "advice_long": advice_long,
        "drills": drills[:5],  # Max 5 drills
        "severity": severity,
        "feedback_level": feedback_level,
        "tone": tone,
        "source": "fallback_templates",
    }
    
    # If schema provided, ensure all required keys exist
    if schema:
        properties = schema.get("properties", {})
        for key, rule in properties.items():
            if key not in feedback:
                expected = rule.get("type", "string")
                if expected == "array":
                    feedback[key] = []
                elif expected == "object":
                    feedback[key] = {}
                elif expected == "string":
                    feedback[key] = ""
                elif expected in ("number", "integer"):
                    feedback[key] = 0
                elif expected == "boolean":
                    feedback[key] = False
    
    return feedback


def can_use_fallback(error_report: dict[str, Any]) -> bool:
    """Check if the error report has enough data for fallback."""
    return bool(error_report.get("ops")) or bool(error_report.get("metrics"))


__all__ = [
    "generate_fallback_feedback",
    "can_use_fallback",
    "get_templates",
    "TEMPLATES",
]
