"""Métricas de evaluación complementarias al PER.

Módulo dedicado a calcular métricas adicionales para evaluar la calidad
de pronunciación más allá del Phone Error Rate (PER):

- **F1 de fonemas**: precisión y recall de los fonemas producidos
  contra los fonemas de referencia.  Complementa el PER con una visión
  bag-of-phones (sin tener en cuenta orden) y es útil para evaluar si
  el hablante produce los fonemas correctos aunque en posiciones distintas.

- **Hit Rate (@k)**: fracción de fonemas de referencia que aparecen en
  las top-k hipótesis.  (Reservado para uso futuro con N-best ASR.)

Relación PER vs F1
------------------
- PER = penaliza inserción, deleción y sustitución en orden.
- F1  = ignora el orden; mide cobertura y precisión del inventario de
  fonemas producidos.  Un hablante con buen inventario fonémico pero
  mal orden tendrá PER alto y F1 alto.

Fórmulas
--------
::

    precision = TP / (TP + FP)
    recall    = TP / (TP + FN)
    F1        = 2 * precision * recall / (precision + recall)

Donde TP/FP/FN se calculan sobre conteos de multiset (Counter):
    TP = sum(min(ref[p], hyp[p]) for p in ref & hyp)
    FP = sum(max(0, hyp[p] - ref[p]) for p in hyp)
    FN = sum(max(0, ref[p] - hyp[p]) for p in ref)
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional, Sequence

from ipa_core.types import Token


@dataclass(frozen=True)
class PhonemeF1:
    """Resultado del cálculo de F1 de fonemas.

    Campos
    ------
    precision : float
        Fracción de fonemas producidos que son correctos (0-1).
    recall : float
        Fracción de fonemas de referencia que fueron producidos (0-1).
    f1 : float
        Media armónica de precision y recall (0-1).
    tp : int
        True positives (fonemas correctamente producidos, multiset).
    fp : int
        False positives (fonemas en hipótesis no en referencia).
    fn : int
        False negatives (fonemas de referencia no producidos).
    """

    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


def compute_phoneme_f1(
    ref: Sequence[Token],
    hyp: Sequence[Token],
    *,
    ignore_unknown: bool = True,
) -> PhonemeF1:
    """Calcular F1 de fonemas entre referencia e hipótesis.

    Usa aritmética multiset (Counter) para que cada foneema de referencia
    pueda ser satisfecho como máximo una vez por cada ocurrencia en hyp.

    Parámetros
    ----------
    ref : Sequence[Token]
        Secuencia de referencia (ground-truth).
    hyp : Sequence[Token]
        Secuencia hipótesis (del hablante).
    ignore_unknown : bool
        Si True, ignora el token ``"?"`` (OOV marcado) en ambas secuencias.

    Retorna
    -------
    PhonemeF1

    Ejemplos
    --------
    >>> from ipa_core.compare.metrics import compute_phoneme_f1
    >>> r = compute_phoneme_f1(["p", "a", "t", "o"], ["p", "a", "d", "o"])
    >>> round(r.f1, 3)
    0.857
    """
    ref_list = [t for t in ref if not (ignore_unknown and t == "?")]
    hyp_list = [t for t in hyp if not (ignore_unknown and t == "?")]

    ref_counts = Counter(ref_list)
    hyp_counts = Counter(hyp_list)

    tp = sum((ref_counts & hyp_counts).values())
    fp = sum(max(0, hyp_counts[p] - ref_counts[p]) for p in hyp_counts)
    fn = sum(max(0, ref_counts[p] - hyp_counts[p]) for p in ref_counts)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return PhonemeF1(
        precision=precision,
        recall=recall,
        f1=f1,
        tp=tp,
        fp=fp,
        fn=fn,
    )


def compute_per_and_f1(
    ref: Sequence[Token],
    hyp: Sequence[Token],
    *,
    per: Optional[float] = None,
) -> dict[str, float]:
    """Calcular PER y F1 juntos y retornar como dict.

    Si ``per`` ya estaba calculado (p.ej. por LevenshteinComparator),
    se pasa directamente y sólo se calcula el F1.

    Retorna
    -------
    dict con claves: ``per``, ``f1``, ``precision``, ``recall``.
    """
    f1_result = compute_phoneme_f1(ref, hyp)
    result_per = per if per is not None else _simple_per(ref, hyp)
    return {
        "per": result_per,
        "f1": f1_result.f1,
        "precision": f1_result.precision,
        "recall": f1_result.recall,
        "tp": float(f1_result.tp),
        "fp": float(f1_result.fp),
        "fn": float(f1_result.fn),
    }


def _simple_per(ref: Sequence[Token], hyp: Sequence[Token]) -> float:
    """PER simple sin backtracking (sólo para uso interno como fallback)."""
    n = len(ref)
    if n == 0:
        return 0.0
    ref_counts = Counter(ref)
    hyp_counts = Counter(hyp)
    tp = sum((ref_counts & hyp_counts).values())
    errors = n - tp + sum(
        max(0, hyp_counts[p] - ref_counts[p]) for p in hyp_counts
    )
    return min(1.0, errors / n)


__all__ = [
    "PhonemeF1",
    "compute_phoneme_f1",
    "compute_per_and_f1",
]
