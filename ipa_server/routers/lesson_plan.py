"""Endpoints de planificación de lecciones con LLM.

Rutas disponibles
-----------------
POST /v1/lessons/plan
    Genera un plan de lección personalizado basado en el historial del usuario.

GET /v1/lessons/roadmap/{user_id}/{lang}
    Devuelve el estado del roadmap del usuario para un idioma.

POST /v1/lessons/generate/{lang}/{sound_id}
    Genera contenido de lección para un fonema específico (sin necesitar historial).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ipa_server.models import (
    LessonPlanRequest,
    LessonPlanResponse,
    LessonDrillItem,
    RoadmapProgressResponse,
    RoadmapTopicProgress,
)
from ipa_server.kernel_provider import get_or_create_kernel

router = APIRouter(prefix="/v1/lessons", tags=["lessons"])


# ---------------------------------------------------------------------------
# POST /v1/lessons/plan
# ---------------------------------------------------------------------------

@router.post(
    "/plan",
    response_model=LessonPlanResponse,
    summary="Plan de lección personalizado",
    description=(
        "Genera un plan de lección usando el LLM, personalizado según el "
        "historial de pronunciación y el estado del roadmap del usuario."
    ),
)
async def get_lesson_plan(body: LessonPlanRequest) -> LessonPlanResponse:
    kernel = await get_or_create_kernel()

    if not kernel.llm:
        raise HTTPException(
            status_code=503,
            detail="LLM no configurado. Establece PRONUNCIAPA_LLM en el entorno.",
        )

    from ipa_core.services.lesson import plan_lesson  # noqa: PLC0415

    result = await plan_lesson(
        body.user_id,
        body.lang,
        kernel,
        sound_id=body.sound_id,
    )

    return LessonPlanResponse(
        recommended_sound_id=result["recommended_sound_id"],
        topic_id=result["topic_id"],
        intro=result["intro"],
        tips=result.get("tips", []),
        drills=[
            LessonDrillItem(type=d.get("type", "phrase"), text=d.get("text", ""))
            for d in result.get("drills", [])
        ],
    )


# ---------------------------------------------------------------------------
# GET /v1/lessons/roadmap/{user_id}/{lang}
# ---------------------------------------------------------------------------

@router.get(
    "/roadmap/{user_id}/{lang}",
    response_model=RoadmapProgressResponse,
    summary="Estado del roadmap del usuario",
    description=(
        "Devuelve el avance del roadmap de pronunciación para el usuario e idioma dados. "
        "Los temas se ordenan por secuencia pedagógica."
    ),
)
async def get_roadmap_progress(user_id: str, lang: str) -> RoadmapProgressResponse:
    kernel = await get_or_create_kernel()

    if not kernel.history:
        raise HTTPException(
            status_code=503,
            detail="Historial no configurado. Establece history en la configuración del kernel.",
        )

    from ipa_core.services.lesson import load_roadmap  # noqa: PLC0415

    roadmap_def = load_roadmap(lang)
    progress_map = await kernel.history.get_roadmap_progress(user_id, lang)

    topics: list[RoadmapTopicProgress] = []
    if roadmap_def:
        for topic in sorted(roadmap_def.get("topics", []), key=lambda t: t.get("order", 99)):
            topics.append(
                RoadmapTopicProgress(
                    topic_id=topic["id"],
                    name=topic["name"],
                    level=progress_map.get(topic["id"], "not_started"),
                    order=topic.get("order", 0),
                )
            )
    else:
        # No roadmap YAML — return whatever is stored
        for topic_id, level in progress_map.items():
            topics.append(
                RoadmapTopicProgress(topic_id=topic_id, name=topic_id, level=level)
            )

    return RoadmapProgressResponse(user_id=user_id, lang=lang, topics=topics)


# ---------------------------------------------------------------------------
# POST /v1/lessons/generate/{lang}/{sound_id}
# ---------------------------------------------------------------------------

@router.post(
    "/generate/{lang}/{sound_id}",
    response_model=LessonPlanResponse,
    summary="Generar lección para un fonema específico",
    description=(
        "Genera contenido de lección para un fonema IPA concreto usando el LLM, "
        "sin requerir historial de usuario. Útil para previsualizar lecciones."
    ),
)
async def generate_lesson_for_sound(lang: str, sound_id: str) -> LessonPlanResponse:
    kernel = await get_or_create_kernel()

    if not kernel.llm:
        raise HTTPException(
            status_code=503,
            detail="LLM no configurado.",
        )

    from ipa_core.services.lesson import plan_lesson  # noqa: PLC0415

    # Use an anonymous user — no history will be read or written
    result = await plan_lesson(
        "_preview",
        lang,
        kernel,
        sound_id=sound_id,
    )

    return LessonPlanResponse(
        recommended_sound_id=result["recommended_sound_id"],
        topic_id=result["topic_id"],
        intro=result["intro"],
        tips=result.get("tips", []),
        drills=[
            LessonDrillItem(type=d.get("type", "phrase"), text=d.get("text", ""))
            for d in result.get("drills", [])
        ],
    )
