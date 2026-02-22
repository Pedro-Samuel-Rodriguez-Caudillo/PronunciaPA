"""Clasificación de errores por posición fonémica.

Enriquece el reporte de comparación indicando la posición de cada error
dentro de la palabra: inicial, medial, final, onset, coda o núcleo.

Esta información es pedagógicamente valiosa porque:
- Los errores en posición inicial son más salientes perceptivamente.
- Los errores en onset requieren habilidades articulatorias distintas
  a los errores en coda.
- El análisis por posición permite al instructor focalizar ejercicios.

Niveles de posición
-------------------
``word_position``
    Posición dentro de la secuencia completa:
    - ``"initial"``   — primeros 25% de tokens
    - ``"medial"``    — tokens del 25%-75%
    - ``"final"``     — últimos 25% de tokens

``syllabic_role``
    Rol dentro de la sílaba (requiere análisis silábico):
    - ``"onset"``     — consonante antes del núcleo vocálico
    - ``"nucleus"``   — vocal (núcleo silábico)
    - ``"coda"``      — consonante después del núcleo
    - ``"unknown"``   — si no se pudo determinar

Uso
---
::

    from ipa_core.analysis.position import classify_errors_by_position
    ops = [{"op": "sub", "ref": "r", "hyp": "l", "ref_pos": 2}, ...]
    enriched = classify_errors_by_position(ops, ref_tokens=["p", "a", "r", "a"])
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from ipa_core.types import Token


def _word_position(index: int, total: int) -> str:
    """Clasificar posición lineal del token dentro de la secuencia."""
    if total <= 1:
        return "monosyllabic"
    frac = index / (total - 1)
    if frac <= 0.25:
        return "initial"
    if frac >= 0.75:
        return "final"
    return "medial"


def classify_errors_by_position(
    ops: list[dict[str, Any]],
    *,
    ref_tokens: Sequence[Token],
    use_syllabic: bool = True,
) -> list[dict[str, Any]]:
    """Enriquecer operaciones de edición con información de posición.

    Parámetros
    ----------
    ops : list[dict]
        Lista de operaciones de edición (salida de LevenshteinComparator).
        Cada op debe tener: {``op``, ``ref``, ``hyp``, opcionalmente ``ref_pos``},
        donde ``ref_pos`` es el índice del token en la referencia.
    ref_tokens : Sequence[Token]
        Secuencia de tokens de referencia (para calcular posiciones).
    use_syllabic : bool
        Si True, intentar calcular también el rol silábico (onset/nucleus/coda).
        Requiere ``ipa_core.analysis.syllabic``.

    Retorna
    -------
    list[dict]
        Mismas ops con campos adicionales:
        - ``word_position`` : str
        - ``syllabic_role`` : str  (si use_syllabic=True)
        - ``syllable_index`` : int (si use_syllabic=True)
        - ``is_error`` : bool
    """
    total = len(ref_tokens)
    syllabic_fn = None
    if use_syllabic:
        try:
            from ipa_core.analysis.syllabic import get_syllabic_position
            syllabic_fn = get_syllabic_position
        except ImportError:
            pass

    # Construir índice ref_pos si no está en las ops
    # Las ops del comparador Levenshtein no siempre incluyen ref_pos explícito;
    # lo reconstruimos siguiendo el cursor de referencia secuencialmente.
    enriched: list[dict[str, Any]] = []
    ref_cursor = 0

    for op in ops:
        new_op = dict(op)
        op_type = op.get("op", "")
        new_op["is_error"] = op_type != "eq"

        # Índice en la referencia
        ref_pos = op.get("ref_pos")
        if ref_pos is None:
            if op_type in ("eq", "sub", "del"):
                ref_pos = ref_cursor
                ref_cursor += 1
            else:  # ins
                ref_pos = ref_cursor  # inserción ocurre en este punto

        new_op["ref_pos"] = ref_pos
        new_op["word_position"] = _word_position(ref_pos, total) if total > 0 else "unknown"

        if syllabic_fn is not None:
            try:
                syll_info = syllabic_fn(list(ref_tokens), ref_pos)
                new_op["syllabic_role"] = syll_info.get("position", "unknown")
                new_op["syllable_index"] = syll_info.get("syllable_index", -1)
                new_op["syllable_position"] = syll_info.get("syllable_position", "unknown")
            except Exception:
                new_op["syllabic_role"] = "unknown"
                new_op["syllable_index"] = -1
                new_op["syllable_position"] = "unknown"
        else:
            new_op["syllabic_role"] = "unknown"

        enriched.append(new_op)

    return enriched


def error_distribution(
    ops: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Calcular distribución de errores por posición y tipo.

    Parámetros
    ----------
    ops : list[dict]
        Ops enriquecidas por ``classify_errors_by_position`` (con
        campos ``word_position``, ``syllabic_role``, ``is_error``).

    Retorna
    -------
    dict con dos claves:
    - ``by_word_position`` : {position: error_count}
    - ``by_syllabic_role`` : {role: error_count}
    """
    by_word: dict[str, int] = {}
    by_role: dict[str, int] = {}

    for op in ops:
        if not op.get("is_error"):
            continue
        wpos = op.get("word_position", "unknown")
        role = op.get("syllabic_role", "unknown")
        by_word[wpos] = by_word.get(wpos, 0) + 1
        by_role[role] = by_role.get(role, 0) + 1

    return {"by_word_position": by_word, "by_syllabic_role": by_role}


def initial_vs_final_error_ratio(ops: list[dict[str, Any]]) -> float:
    """Ratio de errores iniciales vs finales.

    Retorna
    -------
    float
        > 1.0 = más errores iniciales; < 1.0 = más errores finales.
        1.0 = distribución equitativa.  0.0 si no hay errores finales.
    """
    dist = error_distribution(ops)["by_word_position"]
    initial = dist.get("initial", 0)
    final = dist.get("final", 0)
    if final == 0:
        return float("inf") if initial > 0 else 1.0
    return initial / final


__all__ = [
    "classify_errors_by_position",
    "error_distribution",
    "initial_vs_final_error_ratio",
]
