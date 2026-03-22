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
    
    _add_manner_hint(hints, feats.get("manner", ""))
    _add_place_hint(hints, feats.get("place", ""))
    _add_voicing_hint(hints, feats)
    
    return hints


def _add_manner_hint(hints: list[str], manner: str) -> None:
    if manner in _HINTS_BY_MANNER:
        hints.append(_HINTS_BY_MANNER[manner])


def _add_place_hint(hints: list[str], place: str) -> None:
    if place in _HINTS_BY_PLACE:
        hints.append(_HINTS_BY_PLACE[place])


def _add_voicing_hint(hints: list[str], feats: dict[str, Any]) -> None:
    if feats.get("voice") is True:
        hints.append("Activa la vibración de las cuerdas vocales (sonoro).")
    elif feats.get("voice") is False and feats.get("type") == "consonant":
        hints.append("No vibres las cuerdas vocales (sordo).")


def extract_confusion_pairs(
    ops: list[EditOp],
    *,
    min_distance: float = 0.0,
) -> list[dict[str, Any]]:
    """Extrae pares de confusión (ref→hyp) ordenados por frecuencia × distancia."""
    counter = _count_edit_ops(ops)
    
    pairs: list[dict[str, Any]] = []
    for (ref, hyp), count in counter.items():
        dist = _calculate_pair_distance(ref, hyp)
        if dist < min_distance:
            continue
        pairs.append({
            "ref": ref, "hyp": hyp, "count": count,
            "distance": round(dist, 3),
            "impact": round(count * dist, 3),
        })
    pairs.sort(key=lambda p: p["impact"], reverse=True)
    return pairs


def _count_edit_ops(ops: list[EditOp]) -> Counter[tuple[str, str]]:
    counter: Counter[tuple[str, str]] = Counter()
    for op in ops:
        kind = op.get("op")
        ref = op.get("ref") or ""
        hyp = op.get("hyp") or ""
        
        if kind == "sub" and ref and hyp:
            counter[(ref, hyp)] += 1
        elif kind == "del" and ref:
            counter[(ref, "_")] += 1
        elif kind == "ins" and hyp:
            counter[("_", hyp)] += 1
    return counter


def _calculate_pair_distance(ref: str, hyp: str) -> float:
    if ref == "_" or hyp == "_":
        return 1.0
    return calculate_articulatory_distance(ref, hyp)


def generate_drills_from_errors(
    ops: list[EditOp],
    *,
    lang: str = "es",
    max_drills: int = 5,
    max_pairs: int = 4,
) -> DrillSet:
    """Genera un DrillSet focalizado en los errores más impactantes."""
    confusions = extract_confusion_pairs(ops)
    if not confusions:
        return _empty_drill_set(lang)

    items: list[DrillItem] = []
    minimal_pairs: list[MinimalPair] = []
    target_phones: list[str] = []

    lang_base = lang.split("-")[0]
    mp_db = _MINIMAL_PAIRS.get(lang_base, {})

    for confusion in confusions[:max_drills]:
        _process_confusion(confusion, items, minimal_pairs, target_phones, mp_db, max_pairs)

    unique_targets = list(dict.fromkeys(target_phones))
    return DrillSet(
        name=f"Práctica: {', '.join(unique_targets[:3])}",
        description=f"Ejercicios generados a partir de {len(confusions)} confusión(es).",
        lang=lang,
        target_phones=unique_targets,
        items=items,
        minimal_pairs=minimal_pairs,
    )


def _empty_drill_set(lang: str) -> DrillSet:
    return DrillSet(
        name="Sin errores detectados",
        description="¡Excelente! No se detectaron errores de pronunciación.",
        lang=lang,
    )


def _process_confusion(confusion: dict, items: list[DrillItem], mps: list[MinimalPair], targets: list[str], mp_db: dict, max_pairs: int):
    ref, hyp = confusion["ref"], confusion["hyp"]
    if ref != "_":
        targets.append(ref)

    _add_confusion_drill_item(confusion, items, ref, hyp)
    _add_confusion_minimal_pairs(ref, mp_db, mps, max_pairs)


def _add_confusion_drill_item(confusion: dict, items: list[DrillItem], ref: str, hyp: str):
    desc = _describe_confusion(ref, hyp)
    phone = ref if ref != "_" else hyp
    items.append(DrillItem(
        text=desc,
        ipa=phone,
        target_phones=[ref] if ref != "_" else [hyp],
        difficulty=_confusion_difficulty(confusion["distance"]),
        hints=_build_hints(phone),
    ))


def _add_confusion_minimal_pairs(ref: str, mp_db: dict, mps: list[MinimalPair], max_pairs: int):
    if ref not in mp_db:
        return
    for entry in mp_db[ref][:max_pairs]:
        word_a, word_b, contrast, pos = entry
        mps.append(MinimalPair(
            word_a=word_a, word_b=word_b, ipa_a="", ipa_b="",
            target_phone=ref, contrast_phone=contrast, position=pos,
        ))


def _describe_confusion(ref: str, hyp: str) -> str:
    if ref == "_":
        return f"Evita insertar [{hyp}] donde no corresponde."
    if hyp == "_":
        return f"Pronuncia [{ref}] — no lo omitas."
    return f"Diferencia [{ref}] de [{hyp}]."


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
    """Generar DrillSets agrupados por proximidad articulatoria."""
    groups = group_phones_by_articulatory_proximity(phones, threshold=threshold)
    drill_sets: list[DrillSet] = []

    for group in groups:
        if not group:
            continue
        drill_sets.append(_process_articulator_group(group, lang, max_drills_per_group))

    return drill_sets


def _process_articulator_group(group: list[str], lang: str, max_drills: int) -> DrillSet:
    seed = group[0]
    items: list[DrillItem] = []
    minimal_pairs: list[MinimalPair] = []
    mp_db = _MINIMAL_PAIRS.get(lang.split("-")[0], {})

    for i, phone_a in enumerate(group[:max_drills]):
        # Single phone drill
        items.append(_build_single_phone_drill(phone_a, i))
        # Contrasts
        _add_intragroup_contrasts(group, phone_a, i, items)
        # DB minimal pairs
        _add_db_minimal_pairs(phone_a, mp_db, minimal_pairs)

    return _build_group_drill_set(group, seed, items, minimal_pairs, lang)


def _build_single_phone_drill(phone: str, idx: int) -> DrillItem:
    return DrillItem(
        text=f"Practica el sonido [{phone}]",
        ipa=phone,
        target_phones=[phone],
        difficulty=1 + (idx % 5),
        hints=_build_hints(phone),
    )


def _add_intragroup_contrasts(group: list[str], phone_a: str, idx: int, items: list[DrillItem]):
    for phone_b in group[idx + 1 : idx + 3]:
        dist = calculate_articulatory_distance(phone_a, phone_b)
        items.append(DrillItem(
            text=f"Distingue [{phone_a}] de [{phone_b}]",
            ipa=f"{phone_a} ~ {phone_b}",
            target_phones=[phone_a, phone_b],
            difficulty=_confusion_difficulty(dist),
            hints=_build_hints(phone_a),
        ))


def _add_db_minimal_pairs(phone: str, mp_db: dict, mps: list[MinimalPair]):
    if phone in mp_db:
        for entry in mp_db[phone][:2]:
            word_a, word_b, contrast, pos = entry
            mps.append(MinimalPair(
                word_a=word_a, word_b=word_b, ipa_a="", ipa_b="",
                target_phone=phone, contrast_phone=contrast, position=pos,
            ))


def _build_group_drill_set(group: list[str], seed: str, items: list[DrillItem], mps: list[MinimalPair], lang: str) -> DrillSet:
    feats = get_phone_features(seed)
    place = feats.get('place', '')
    manner = feats.get('manner', '')
    group_name = f"{place} {manner}".strip() or f"Grupo '{seed}'"
    
    return DrillSet(
        name=f"Fonemas {group_name}: {', '.join(f'[{p}]' for p in group[:5])}",
        description=f"Ejercicios para el grupo de [{seed}]. {len(group)} fonema(s) similares.",
        lang=lang,
        target_phones=group,
        items=items,
        minimal_pairs=mps,
    )


__all__ = [
    "extract_confusion_pairs",
    "generate_drills_from_errors",
    "group_phones_by_articulatory_proximity",
    "generate_drills_by_proximity",
]

