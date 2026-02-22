"""Generador de drills a partir de errores de pronunciación.

Analiza los errores del comparador y genera ejercicios focalizados
en las confusiones fonéticas más frecuentes del usuario.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Optional

from ipa_core.drill_types import DrillItem, DrillSet, MinimalPair
from ipa_core.services.error_report import (
    calculate_articulatory_distance,
    get_phone_features,
)
from ipa_core.textref.g2p_generator import MINIMAL_PAIRS_EN, MINIMAL_PAIRS_ES
from ipa_core.types import EditOp

_MINIMAL_PAIRS = {
    "en": MINIMAL_PAIRS_EN,
    "es": MINIMAL_PAIRS_ES,
}

# Tips de producción por rasgo articulatorio
_HINTS_BY_MANNER: dict[str, str] = {
    "stop": "Bloquea completamente el flujo de aire y luego suéltalo de golpe.",
    "fricative": "Estrecha el paso del aire sin bloquearlo para producir fricción audible.",
    "affricate": "Comienza como una oclusiva y termina como fricativa.",
    "nasal": "Baja el velo del paladar para que el aire salga por la nariz.",
    "lateral": "Baja los lados de la lengua para que el aire pase por los costados.",
    "trill": "Vibra la punta de la lengua contra los alvéolos repetidamente.",
    "tap": "Un solo toque rápido de la punta de la lengua contra los alvéolos.",
    "approximant": "Acerca los articuladores sin crear fricción.",
}

_HINTS_BY_PLACE: dict[str, str] = {
    "bilabial": "Usa ambos labios juntos.",
    "labiodental": "Coloca los dientes superiores sobre el labio inferior.",
    "dental": "Coloca la punta de la lengua contra los dientes superiores.",
    "alveolar": "Coloca la punta de la lengua contra la cresta alveolar.",
    "postalveolar": "Coloca la lengua justo detrás de la cresta alveolar.",
    "palatal": "Eleva el cuerpo de la lengua hacia el paladar duro.",
    "velar": "Eleva la parte posterior de la lengua hacia el paladar blando.",
    "glottal": "Produce el sonido en la glotis (cuerdas vocales).",
}


def _build_hints(phone: str) -> list[str]:
    """Genera hints de articulación para un fonema."""
    feats = get_phone_features(phone)
    hints: list[str] = []
    manner = feats.get("manner", "")
    place = feats.get("place", "")
    if manner in _HINTS_BY_MANNER:
        hints.append(_HINTS_BY_MANNER[manner])
    if place in _HINTS_BY_PLACE:
        hints.append(_HINTS_BY_PLACE[place])
    if feats.get("voice") is True:
        hints.append("Activa la vibración de las cuerdas vocales (sonoro).")
    elif feats.get("voice") is False and feats.get("type") == "consonant":
        hints.append("No vibres las cuerdas vocales (sordo).")
    return hints


def extract_confusion_pairs(
    ops: list[EditOp],
    *,
    min_distance: float = 0.0,
) -> list[dict[str, Any]]:
    """Extrae pares de confusión (ref→hyp) ordenados por frecuencia × distancia.

    Parameters
    ----------
    ops : list[EditOp]
        Operaciones de edición del comparador.
    min_distance : float
        Distancia articulatoria mínima para considerar (filtra ruido).

    Returns
    -------
    list[dict]
        Pares con ``ref``, ``hyp``, ``count``, ``distance``, ``impact``.
    """
    counter: Counter[tuple[str, str]] = Counter()
    for op in ops:
        if op.get("op") == "sub":
            ref = op.get("ref") or ""
            hyp = op.get("hyp") or ""
            if ref and hyp:
                counter[(ref, hyp)] += 1
        elif op.get("op") == "del":
            ref = op.get("ref") or ""
            if ref:
                counter[(ref, "_")] += 1
        elif op.get("op") == "ins":
            hyp = op.get("hyp") or ""
            if hyp:
                counter[("_", hyp)] += 1

    pairs: list[dict[str, Any]] = []
    for (ref, hyp), count in counter.items():
        dist = calculate_articulatory_distance(ref, hyp) if ref != "_" and hyp != "_" else 1.0
        if dist < min_distance:
            continue
        pairs.append({
            "ref": ref,
            "hyp": hyp,
            "count": count,
            "distance": round(dist, 3),
            "impact": round(count * dist, 3),
        })
    pairs.sort(key=lambda p: p["impact"], reverse=True)
    return pairs


def generate_drills_from_errors(
    ops: list[EditOp],
    *,
    lang: str = "es",
    max_drills: int = 5,
    max_pairs: int = 4,
) -> DrillSet:
    """Genera un DrillSet focalizado en los errores más impactantes.

    Parameters
    ----------
    ops : list[EditOp]
        Operaciones de edición (de CompareResult.ops).
    lang : str
        Código de idioma base (``es`` o ``en``).
    max_drills : int
        Máximo de DrillItems a generar.
    max_pairs : int
        Máximo de MinimalPairs por confusión.

    Returns
    -------
    DrillSet
        Conjunto de ejercicios listos para el frontend.
    """
    confusions = extract_confusion_pairs(ops)
    if not confusions:
        return DrillSet(
            name="Sin errores detectados",
            description="¡Excelente! No se detectaron errores de pronunciación.",
            lang=lang,
        )

    target_phones: list[str] = []
    items: list[DrillItem] = []
    minimal_pairs: list[MinimalPair] = []

    lang_base = lang.split("-")[0]  # en-us → en
    mp_db = _MINIMAL_PAIRS.get(lang_base, {})

    for confusion in confusions[:max_drills]:
        ref_phone = confusion["ref"]
        hyp_phone = confusion["hyp"]

        if ref_phone != "_":
            target_phones.append(ref_phone)

        # Generar DrillItem con hints articulatorios
        if ref_phone == "_":
            desc = f"Evita insertar [{hyp_phone}] donde no corresponde."
        elif hyp_phone == "_":
            desc = f"Pronuncia [{ref_phone}] — no lo omitas."
        else:
            desc = f"Diferencia [{ref_phone}] de [{hyp_phone}]."

        hints = _build_hints(ref_phone) if ref_phone != "_" else _build_hints(hyp_phone)
        difficulty = _confusion_difficulty(confusion["distance"])

        items.append(DrillItem(
            text=desc,
            ipa=ref_phone if ref_phone != "_" else hyp_phone,
            target_phones=[ref_phone] if ref_phone != "_" else [hyp_phone],
            difficulty=difficulty,
            hints=hints,
        ))

        # Buscar pares mínimos en la base de datos
        if ref_phone in mp_db:
            for entry in mp_db[ref_phone][:max_pairs]:
                word_a, word_b, contrast, position = entry
                minimal_pairs.append(MinimalPair(
                    word_a=word_a,
                    word_b=word_b,
                    ipa_a="",  # Se llenaría con TextRef en producción
                    ipa_b="",
                    target_phone=ref_phone,
                    contrast_phone=contrast,
                    position=position,
                ))

    unique_targets = list(dict.fromkeys(target_phones))

    drill_set = DrillSet(
        name=f"Práctica: {', '.join(unique_targets[:3])}",
        description=f"Ejercicios generados a partir de {len(confusions)} confusión(es) detectada(s).",
        lang=lang,
        target_phones=unique_targets,
        items=items,
        minimal_pairs=minimal_pairs,
    )
    return drill_set


def _confusion_difficulty(distance: float) -> int:
    """Calcula dificultad 1-5 según distancia articulatoria."""
    if distance < 0.2:
        return 5  # Muy similar → muy difícil de distinguir
    elif distance < 0.4:
        return 4
    elif distance < 0.6:
        return 3
    elif distance < 0.8:
        return 2
    else:
        return 1  # Muy diferente → fácil


# ---------------------------------------------------------------------------
# Agrupación por proximidad articulatoria
# ---------------------------------------------------------------------------

def group_phones_by_articulatory_proximity(
    phones: list[str],
    *,
    threshold: float = 0.35,
) -> list[list[str]]:
    """Agrupar fonemas por similitud articulatoria usando clustering greedy.

    Fonemas articulatoriamente cercanos (distancia < threshold) se
    colocan en el mismo grupo.  Útil para:
    - Ejercicios de minimal pairs dentro del mismo lugar de articulación.
    - Ordenar drills de fácil a difícil dentro de un grupo fonémico.
    - Identificar fonemas que comparte el alumno con su L1.

    Parámetros
    ----------
    phones : list[str]
        Lista de símbolos IPA a agrupar.
    threshold : float
        Distancia articulatoria máxima para pertenecer al mismo cluster.
        Defecto 0.35 (fonemas bastante similares).

    Retorna
    -------
    list[list[str]]
        Lista de grupos.  Cada grupo es una lista de fonemas similares
        ordenados de menor a mayor distancia al centroide (primero = más
        representativo).

    Ejemplo
    -------
    >>> group_phones_by_articulatory_proximity(["p","b","m","t","d","n"])
    [["p","b","m"], ["t","d","n"]]  # bilabiales vs alveolares
    """
    if not phones:
        return []

    remaining = list(phones)
    groups: list[list[str]] = []

    while remaining:
        seed = remaining.pop(0)
        group = [seed]
        still_remaining = []
        for candidate in remaining:
            dist = calculate_articulatory_distance(seed, candidate)
            if dist <= threshold:
                group.append(candidate)
            else:
                still_remaining.append(candidate)
        remaining = still_remaining
        groups.append(group)

    return groups


def generate_drills_by_proximity(
    phones: list[str],
    *,
    lang: str = "es",
    threshold: float = 0.35,
    max_drills_per_group: int = 3,
) -> list[DrillSet]:
    """Generar DrillSets agrupados por proximidad articulatoria.

    A diferencia de ``generate_drills_from_errors``, esta función toma
    una lista de fonemas objetivo (p.ej. del perfil del alumno) y genera
    conjuntos de ejercicios organizados por grupo articulatorio.

    Parámetros
    ----------
    phones : list[str]
        Fonemas a practicar.
    lang : str
        Idioma base.
    threshold : float
        Umbral de distancia para agrupar.
    max_drills_per_group : int
        Máximo de DrillItems por grupo.

    Retorna
    -------
    list[DrillSet]
        Un DrillSet por grupo articulatorio encontrado.
    """
    groups = group_phones_by_articulatory_proximity(phones, threshold=threshold)
    drill_sets: list[DrillSet] = []

    for group in groups:
        if not group:
            continue

        seed = group[0]
        items: list[DrillItem] = []
        minimal_pairs: list[MinimalPair] = []

        lang_base = lang.split("-")[0]
        mp_db = _MINIMAL_PAIRS.get(lang_base, {})

        for i, phone_a in enumerate(group[:max_drills_per_group]):
            hints = _build_hints(phone_a)
            items.append(DrillItem(
                text=f"Practica el sonido [{phone_a}]",
                ipa=phone_a,
                target_phones=[phone_a],
                difficulty=1 + (i % 5),
                hints=hints,
            ))

            # Pares mínimos intragrupo (contraste entre sonidos del mismo grupo)
            for phone_b in group[i + 1 : i + 3]:
                dist = calculate_articulatory_distance(phone_a, phone_b)
                difficulty_pair = _confusion_difficulty(dist)
                items.append(DrillItem(
                    text=f"Distingue [{phone_a}] de [{phone_b}]",
                    ipa=f"{phone_a} ~ {phone_b}",
                    target_phones=[phone_a, phone_b],
                    difficulty=difficulty_pair,
                    hints=hints,
                ))

            # Buscar pares mínimos en la BD
            if phone_a in mp_db:
                for entry in mp_db[phone_a][:2]:
                    word_a, word_b, contrast, position = entry
                    minimal_pairs.append(MinimalPair(
                        word_a=word_a,
                        word_b=word_b,
                        ipa_a="",
                        ipa_b="",
                        target_phone=phone_a,
                        contrast_phone=contrast,
                        position=position,
                    ))

        feats = get_phone_features(seed)
        group_name = (
            f"{feats.get('place', '')} {feats.get('manner', '')}".strip()
            or f"Grupo '{seed}'"
        )
        drill_sets.append(DrillSet(
            name=f"Fonemas {group_name}: {', '.join(f'[{p}]' for p in group[:5])}",
            description=(
                f"Ejercicios para el grupo articulatorio de [{seed}]. "
                f"{len(group)} fonema(s) similares."
            ),
            lang=lang,
            target_phones=group,
            items=items,
            minimal_pairs=minimal_pairs,
        ))

    return drill_sets


__all__ = [
    "extract_confusion_pairs",
    "generate_drills_from_errors",
    "group_phones_by_articulatory_proximity",
    "generate_drills_by_proximity",
]

