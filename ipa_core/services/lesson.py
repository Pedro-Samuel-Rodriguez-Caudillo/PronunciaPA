"""Lesson planning service: personaliza lecciones usando LLM + historial de progreso.

Responsabilidades
-----------------
1. ``plan_lesson`` — genera un plan de lección personalizado para el usuario,
   seleccionando automáticamente el tema más adecuado del roadmap.
2. ``update_roadmap`` — recalcula y persiste el avance del roadmap basándose en
   los ``phoneme_stats`` actualizados del usuario.
3. ``load_roadmap`` — carga el YAML de roadmap para un idioma dado.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ipa_core.kernel.core import Kernel

logger = logging.getLogger(__name__)

_ROADMAPS_DIR = Path(__file__).parent.parent.parent / "data" / "roadmaps"

# Plan de lección de respaldo cuando no hay LLM o roadmap configurado
_STUB_LESSON: dict[str, Any] = {
    "recommended_sound_id": "s",
    "topic_id": "fricatives",
    "intro": "Practiquemos las fricativas del español.",
    "tips": [
        "Coloca la punta de la lengua cerca de los dientes superiores para /s/.",
        "Escucha la diferencia entre /s/ y /θ/ en variedades del español.",
    ],
    "drills": [
        {"type": "minimal_pair", "text": "caza / casa"},
        {"type": "syllable", "text": "sa se si so su"},
    ],
}


# ---------------------------------------------------------------------------
# Carga de roadmap
# ---------------------------------------------------------------------------

def load_roadmap(lang: str) -> Optional[dict[str, Any]]:
    """Cargar el roadmap YAML para el idioma dado. Retorna None si no existe."""
    try:
        import yaml  # type: ignore[import]
    except ImportError:
        logger.warning("PyYAML no está instalado; no se puede cargar el roadmap.")
        return None

    path = _ROADMAPS_DIR / f"{lang}.yaml"
    if not path.exists():
        logger.debug("Roadmap no encontrado en %s", path)
        return None
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Cálculo de nivel de tema
# ---------------------------------------------------------------------------

def _compute_topic_level(
    topic: dict[str, Any],
    phoneme_stats: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> str:
    """Determinar el nivel de dominio actual de un tema según los phoneme_stats."""
    phonemes: set[str] = set(topic.get("phonemes", []))
    if not phonemes:
        return "not_started"

    by_phoneme = {s["phoneme"]: s for s in phoneme_stats}
    total = len(phonemes)

    with_attempts = sum(
        1 for p in phonemes
        if p in by_phoneme and by_phoneme[p]["attempts"] > 0
    )
    mastered = sum(
        1 for p in phonemes
        if p in by_phoneme and by_phoneme[p]["mastery_level"] == "mastered"
    )
    proficient_plus = sum(
        1 for p in phonemes
        if p in by_phoneme and by_phoneme[p]["mastery_level"] in ("proficient", "mastered")
    )

    thr_completed = thresholds.get("completed", 0.80)
    thr_proficient = thresholds.get("proficient", 0.60)
    thr_in_progress = thresholds.get("in_progress", 0.30)

    if mastered / total >= thr_completed:
        return "completed"
    if proficient_plus / total >= thr_proficient:
        return "proficient"
    if with_attempts / total >= thr_in_progress:
        return "in_progress"
    return "not_started"


# ---------------------------------------------------------------------------
# Actualización automática del roadmap
# ---------------------------------------------------------------------------

async def update_roadmap(
    user_id: str,
    lang: str,
    kernel: "Kernel",
) -> dict[str, str]:
    """Recalcular y persistir el avance del roadmap a partir de phoneme_stats actuales.

    Se llama automáticamente tras cada sesión de feedback.

    Retorna
    -------
    dict[str, str]
        Mapa ``{topic_id: level}`` con los niveles actualizados.
    """
    if not kernel.history:
        return {}

    roadmap = load_roadmap(lang)
    if not roadmap:
        return {}

    phoneme_stats = await kernel.history.get_phoneme_stats(user_id, lang)
    thresholds: dict[str, float] = roadmap.get("thresholds", {})
    updated: dict[str, str] = {}

    for topic in roadmap.get("topics", []):
        topic_id: str = topic["id"]
        new_level = _compute_topic_level(topic, phoneme_stats, thresholds)
        await kernel.history.record_roadmap_progress(
            user_id=user_id,
            lang=lang,
            topic_id=topic_id,
            level=new_level,
        )
        updated[topic_id] = new_level

    logger.debug("Roadmap actualizado para user=%s lang=%s: %s", user_id, lang, updated)
    return updated


# ---------------------------------------------------------------------------
# Selección de siguiente tema
# ---------------------------------------------------------------------------

def _pick_next_topic(
    roadmap: dict[str, Any],
    current_progress: dict[str, str],
) -> Optional[dict[str, Any]]:
    """Elegir el mejor tema para estudiar a continuación, respetando el orden pedagógico."""
    topics = sorted(roadmap.get("topics", []), key=lambda t: t.get("order", 99))

    # Primero: tema en_progreso
    for t in topics:
        if current_progress.get(t["id"], "not_started") == "in_progress":
            return t

    # Segundo: siguiente tema no iniciado
    for t in topics:
        if current_progress.get(t["id"], "not_started") == "not_started":
            return t

    # Todo completado o en proficient: primer tema con menor dominio
    return topics[0] if topics else None


# ---------------------------------------------------------------------------
# Construcción del prompt de lección
# ---------------------------------------------------------------------------

def _build_lesson_prompt(
    *,
    lang: str,
    topic: dict[str, Any],
    phoneme_stats: list[dict[str, Any]],
    roadmap_progress: dict[str, str],
    roadmap: dict[str, Any],
) -> str:
    """Construir el prompt LLM para planificación de lección."""
    roadmap_state = [
        {
            "topic": t["name"],
            "level": roadmap_progress.get(t["id"], "not_started"),
        }
        for t in sorted(roadmap.get("topics", []), key=lambda x: x.get("order", 99))
    ]

    topic_phonemes: set[str] = set(topic.get("phonemes", []))
    weak_phonemes = [
        {
            "phoneme": s["phoneme"],
            "error_rate": s["error_rate"],
            "mastery": s["mastery_level"],
        }
        for s in phoneme_stats
        if s["phoneme"] in topic_phonemes
    ]

    context = {
        "lang": lang,
        "focus_topic": {
            "id": topic["id"],
            "name": topic["name"],
            "description": topic.get("description", ""),
            "phonemes": topic.get("phonemes", []),
        },
        "roadmap_state": roadmap_state,
        "weak_phonemes": weak_phonemes,
    }

    return "\n".join([
        "You are a pronunciation teaching assistant.",
        "Based on the learner's roadmap progress and weak phonemes, generate a personalized lesson plan.",
        "",
        "Return ONLY a JSON object with exactly these fields:",
        '- "recommended_sound_id": string — one IPA phoneme from the focus topic to practice',
        '- "topic_id": string — must equal focus_topic.id',
        '- "intro": string — 1-2 sentences acknowledging the learner\'s progress and introducing the lesson',
        '- "tips": array of 2-3 short, actionable articulation tips for the focus phonemes',
        '- "drills": array of 2-3 objects, each {"type": "minimal_pair"|"syllable"|"phrase", "text": "plain string"}',
        "",
        "Rules:",
        "- Respond in the same language as the 'lang' field (es = Spanish, en = English).",
        "- Return ONLY the JSON object. No markdown, no extra text.",
        f"- If lang=es, write all tips and intro in Spanish.",
        "",
        f"CONTEXT:\n{json.dumps(context, ensure_ascii=False)}",
        "OUTPUT_JSON:",
    ])


# ---------------------------------------------------------------------------
# plan_lesson — punto de entrada principal
# ---------------------------------------------------------------------------

async def plan_lesson(
    user_id: str,
    lang: str,
    kernel: "Kernel",
    *,
    sound_id: Optional[str] = None,
) -> dict[str, Any]:
    """Generar un plan de lección personalizado para el usuario.

    Parámetros
    ----------
    user_id : str
        Identificador del usuario (opaco).
    lang : str
        Idioma del aprendiz ("es", "en", …).
    kernel : Kernel
        Kernel con LLM y opcionalmente history configurados.
    sound_id : str, optional
        Si se especifica, forzar foco en este fonema/sonido concreto.

    Retorna
    -------
    dict con campos: recommended_sound_id, topic_id, intro, tips, drills
    """
    if not kernel.llm:
        return dict(_STUB_LESSON)

    roadmap = load_roadmap(lang)
    if not roadmap:
        logger.warning("Roadmap no encontrado para lang=%s; retornando stub.", lang)
        return dict(_STUB_LESSON)

    # Obtener stats del usuario
    phoneme_stats: list[dict[str, Any]] = []
    roadmap_progress: dict[str, str] = {}
    if kernel.history:
        phoneme_stats = await kernel.history.get_phoneme_stats(user_id, lang)
        roadmap_progress = await kernel.history.get_roadmap_progress(user_id, lang)

    # Elegir tema de foco
    if sound_id:
        topic: Optional[dict[str, Any]] = next(
            (t for t in roadmap.get("topics", []) if sound_id in t.get("phonemes", [])),
            _pick_next_topic(roadmap, roadmap_progress),
        )
    else:
        topic = _pick_next_topic(roadmap, roadmap_progress)

    if not topic:
        return dict(_STUB_LESSON)

    prompt = _build_lesson_prompt(
        lang=lang,
        topic=topic,
        phoneme_stats=phoneme_stats,
        roadmap_progress=roadmap_progress,
        roadmap=roadmap,
    )

    params: dict[str, Any] = kernel.model_pack.params if kernel.model_pack else {}
    raw = await kernel.llm.complete(prompt, params=params)

    # Parsear respuesta
    from ipa_core.llm.utils import extract_json_object  # noqa: PLC0415

    try:
        payload = extract_json_object(raw)
        payload.setdefault("topic_id", topic["id"])
        phonemes_list: list[str] = topic.get("phonemes", [])
        payload.setdefault(
            "recommended_sound_id",
            phonemes_list[0] if phonemes_list else topic["id"],
        )
        if not isinstance(payload.get("tips"), list):
            payload["tips"] = [str(payload.get("tips", ""))]
        if not isinstance(payload.get("drills"), list):
            payload["drills"] = [{"type": "phrase", "text": str(payload.get("drills", ""))}]
        return {
            "recommended_sound_id": str(payload.get("recommended_sound_id", "")),
            "topic_id": str(payload.get("topic_id", topic["id"])),
            "intro": str(payload.get("intro", "")),
            "tips": list(payload.get("tips", [])),
            "drills": list(payload.get("drills", [])),
        }
    except Exception as exc:
        logger.warning("Error parseando respuesta LLM de lección: %s", exc)
        phonemes_list = topic.get("phonemes", [])
        return {
            "recommended_sound_id": str(phonemes_list[0]) if phonemes_list else topic["id"],
            "topic_id": topic["id"],
            "intro": f"Practiquemos {topic['name']}.",
            "tips": [
                f"Concéntrate en los fonemas: {', '.join(str(p) for p in phonemes_list)}"
            ],
            "drills": [
                {"type": "phrase", "text": " / ".join(str(p) for p in phonemes_list[:3])}
            ],
        }


__all__ = ["plan_lesson", "update_roadmap", "load_roadmap"]
