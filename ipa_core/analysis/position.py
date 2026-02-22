"""Clasificación de errores fonéticos por posición en la secuencia de referencia.

Posiciones reconocidas
----------------------
- ``"word_initial"`` — primer fonema de la secuencia (habitualmente el más saliente).
- ``"word_final"``   — último fonema de la secuencia.
- ``"medial"``       — posición interna.

Posiciones silábicas (se calculan a partir del análisis CV)
- ``"onset"``   — consonante antes del núcleo vocálico.
- ``"nucleus"`` — vocal o diptongo (núcleo silábico).
- ``"coda"``    — consonante tras el núcleo.

Ambas clasificaciones son complementarias. Se incluyen en ``PositionalError``
como campos separados para que la capa de presentación elija cuál mostrar.

Uso típico
----------
::

    from ipa_core.compare.levenshtein import LevenshteinComparator
    from ipa_core.analysis.position import classify_ops_by_position

    result = await comparator.compare(ref_tokens, hyp_tokens)
    positional = classify_ops_by_position(result["ops"], ref_tokens)
    for err in positional:
        print(err.op, err.ref, err.hyp, "→", err.word_position, "/", err.syllabic_position)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence

from ipa_core.types import EditOp, Token


# ---------------------------------------------------------------------------
# Tipos de posición
# ---------------------------------------------------------------------------

WordPosition = Literal["word_initial", "word_final", "medial"]
SyllabicPosition = Literal["onset", "nucleus", "coda", "unknown"]


# ---------------------------------------------------------------------------
# Vocales IPA (reutilizado de syllabic.py para evitar dependencia circular)
# ---------------------------------------------------------------------------

_IPA_VOWELS: frozenset[str] = frozenset(
    "aeiouæœɑɒɔɛɜɝɞɪɨɯʉʊʌʏɐɘɵɤɶ"
)


def _is_vowel(phone: str) -> bool:
    return bool(phone) and phone[0] in _IPA_VOWELS


# ---------------------------------------------------------------------------
# Resultado de clasificación
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionalError:
    """Error fonético anotado con su posición en la secuencia de referencia.

    Campos
    ------
    op : str
        Tipo de operación: ``"sub"``, ``"ins"`` o ``"del"``.
    ref : str | None
        Fonema de referencia (``None`` para inserciones).
    hyp : str | None
        Fonema observado (``None`` para borrados).
    ref_index : int
        Índice en la secuencia de referencia (−1 para inserciones puras).
    word_position : WordPosition
        Posición lineal: ``"word_initial"``, ``"word_final"`` o ``"medial"``.
    syllabic_position : SyllabicPosition
        Posición silábica relativa a vocales cercanas:
        ``"onset"``, ``"nucleus"``, ``"coda"`` o ``"unknown"``.
    """

    op: str
    ref: Optional[Token]
    hyp: Optional[Token]
    ref_index: int
    word_position: WordPosition
    syllabic_position: SyllabicPosition

    def to_dict(self) -> dict:
        return {
            "op": self.op,
            "ref": self.ref,
            "hyp": self.hyp,
            "ref_index": self.ref_index,
            "word_position": self.word_position,
            "syllabic_position": self.syllabic_position,
        }


# ---------------------------------------------------------------------------
# Clasificador
# ---------------------------------------------------------------------------

def _word_position(ref_index: int, ref_len: int) -> WordPosition:
    """Clasificar posición lineal en la secuencia de referencia."""
    if ref_index == 0:
        return "word_initial"
    if ref_index == ref_len - 1:
        return "word_final"
    return "medial"


def _build_syllabic_map(ref_tokens: list[Token]) -> list[SyllabicPosition]:
    """Construir un mapa posición_ref → posición_silábica usando regla CV.

    Algoritmo (máximo ataque simplificado):
    1. Identificar vocales como núcleos.
    2. Consonantes antes de la primera vocal del grupo → onset.
    3. Consonantes tras la última vocal del grupo → coda.
    """
    n = len(ref_tokens)
    if n == 0:
        return []

    vowel_mask = [_is_vowel(t) for t in ref_tokens]
    result: list[SyllabicPosition] = ["unknown"] * n

    # Marcar núcleos
    for i, is_v in enumerate(vowel_mask):
        if is_v:
            result[i] = "nucleus"

    # Marcar onset: consonantes entre dos núcleos o al inicio hasta el primer núcleo
    # Heurística: para cada vocal, mirar hacia atrás hasta la vocal anterior
    vowel_indices = [i for i, v in enumerate(vowel_mask) if v]

    for v_idx in vowel_indices:
        # El onset de esta vocal va desde (vocal_anterior + 1) hasta v_idx − 1
        prev_nucleus = max((p for p in vowel_indices if p < v_idx), default=-1)
        j = v_idx - 1
        while j > prev_nucleus and not vowel_mask[j]:
            result[j] = "onset"
            j -= 1

    # Marcar coda: consonantes después de la última vocal hasta la siguiente vocal
    for v_idx in vowel_indices:
        next_nucleus = min((p for p in vowel_indices if p > v_idx), default=n)
        j = v_idx + 1
        while j < next_nucleus and not vowel_mask[j]:
            result[j] = "coda"
            j += 1

    # Consonantes sin vocal en la secuencia → unknown (ya asignadas)
    return result


def classify_ops_by_position(
    ops: Sequence[EditOp],
    ref_tokens: Sequence[Token],
) -> list[PositionalError]:
    """Clasificar errores de edición por posición fonémica.

    Solo se procesan operaciones que implican error (``sub``, ``ins``, ``del``).
    Las operaciones ``eq`` (correctas) se ignoran.

    Parámetros
    ----------
    ops :
        Lista de operaciones de edición producida por el comparador
        (``CompareResult["ops"]``).
    ref_tokens :
        Secuencia de referencia original (sin modificar, antes de alineación).

    Retorna
    -------
    list[PositionalError]
        Errores anotados con posición lineal y silábica.
    """
    ref_list = list(ref_tokens)
    ref_len = len(ref_list)
    syllabic_map = _build_syllabic_map(ref_list)

    errors: list[PositionalError] = []
    ref_cursor = 0  # posición actual en la secuencia de referencia

    for op_dict in ops:
        op = op_dict.get("op", "")
        ref_phone = op_dict.get("ref")
        hyp_phone = op_dict.get("hyp")

        if op == "eq":
            # Avanzar cursor sin crear error
            if ref_phone is not None:
                ref_cursor += 1
            continue

        if op == "del":
            # Fonema de referencia eliminado
            idx = ref_cursor
            word_pos = _word_position(idx, ref_len)
            syl_pos = syllabic_map[idx] if 0 <= idx < len(syllabic_map) else "unknown"
            errors.append(PositionalError(
                op="del",
                ref=ref_phone,
                hyp=None,
                ref_index=idx,
                word_position=word_pos,
                syllabic_position=syl_pos,
            ))
            ref_cursor += 1

        elif op == "sub":
            # Sustitución: fonema de referencia reemplazado
            idx = ref_cursor
            word_pos = _word_position(idx, ref_len)
            syl_pos = syllabic_map[idx] if 0 <= idx < len(syllabic_map) else "unknown"
            errors.append(PositionalError(
                op="sub",
                ref=ref_phone,
                hyp=hyp_phone,
                ref_index=idx,
                word_position=word_pos,
                syllabic_position=syl_pos,
            ))
            ref_cursor += 1

        elif op == "ins":
            # Inserción: no consume referencia — posición interpolada
            idx = ref_cursor - 1  # inserción ocurre antes del cursor actual
            if idx < 0:
                idx = 0
            word_pos = _word_position(ref_cursor, ref_len) if ref_len > 0 else "medial"
            syl_pos = syllabic_map[idx] if 0 <= idx < len(syllabic_map) else "unknown"
            errors.append(PositionalError(
                op="ins",
                ref=None,
                hyp=hyp_phone,
                ref_index=-1,
                word_position=word_pos,
                syllabic_position=syl_pos,
            ))
            # No avanzar ref_cursor

    return errors


def error_position_summary(errors: list[PositionalError]) -> dict:
    """Resumir errores por posición.

    Retorna
    -------
    dict
        ``{
            "by_word_position": {"word_initial": N, "medial": N, "word_final": N},
            "by_syllabic_position": {"onset": N, "nucleus": N, "coda": N, "unknown": N},
            "total_errors": N,
        }``
    """
    by_word: dict[str, int] = {"word_initial": 0, "medial": 0, "word_final": 0}
    by_syl: dict[str, int] = {"onset": 0, "nucleus": 0, "coda": 0, "unknown": 0}

    for err in errors:
        by_word[err.word_position] = by_word.get(err.word_position, 0) + 1
        by_syl[err.syllabic_position] = by_syl.get(err.syllabic_position, 0) + 1

    return {
        "by_word_position": by_word,
        "by_syllabic_position": by_syl,
        "total_errors": len(errors),
    }


__all__ = [
    "PositionalError",
    "SyllabicPosition",
    "WordPosition",
    "classify_ops_by_position",
    "error_position_summary",
]
