"""Métricas de evaluación fonética complementarias al PER.

Métricas disponibles
--------------------
- **F1 de fonemas** (micro y macro): mide precisión y exhaustividad de los
  fonemas reconocidos respecto a la referencia.
- **Precisión fonémica**: fracción de fonemas reconocidos que son correctos.
- **Exhaustividad fonémica**: fracción de fonemas de referencia correctamente
  reconocidos.

Relación con PER
----------------
``PER = (S + I + D) / N`` penaliza por igual sustituciones, inserciones y
borrados.  F1 descompone eso en precisión y recall, dando una visión más
completa del tipo de error predominante:

- Alta recall + baja precisión → el hablante produce demasiados fonemas.
- Baja recall + alta precisión → el hablante omite fonemas de la referencia.
- Ambas bajas → errores mixtos / ASR deficiente.

Definiciones
------------
Dado un alineamiento de operaciones de edición:

- TP (verdadero positivo) = operaciones ``eq`` (fonema correcto)
- FP (falso positivo)     = ``ins`` + ``sub`` (fonema extra o incorrecto)
- FN (falso negativo)     = ``del`` + ``sub`` (fonema omitido o incorrecto)

Nótese que ``sub`` incrementa tanto FP como FN, lo que es la convención
estándar para F1 en secuencias etiquetadas.

F1 per fonema
-------------
``compute_phoneme_f1()`` calcula también F1 por cada fonema del inventario
para identificar qué sonidos concretos presentan más dificultad.
"""
from __future__ import annotations

from typing import Sequence

from ipa_core.types import EditOp, Token


# ---------------------------------------------------------------------------
# Métricas globales (micro-averaged)
# ---------------------------------------------------------------------------

def compute_phoneme_f1(ops: Sequence[EditOp]) -> dict:
    """Calcular precisión, recall y F1 micro-promediadas sobre los fonemas.

    Parámetros
    ----------
    ops :
        Lista de operaciones de edición del comparador
        (``CompareResult["ops"]``).

    Retorna
    -------
    dict
        ``{
            "precision": float,   # TP / (TP + FP)
            "recall": float,      # TP / (TP + FN)
            "f1": float,          # 2*P*R / (P+R)  o 0 si P+R=0
            "tp": int,
            "fp": int,
            "fn": int,
        }``
    """
    tp = 0
    fp = 0
    fn = 0

    for op_dict in ops:
        op = op_dict.get("op", "")
        if op == "eq":
            tp += 1
        elif op == "ins":
            fp += 1
        elif op == "del":
            fn += 1
        elif op == "sub":
            # Una sustitución es simultáneamente un FP y un FN
            fp += 1
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


# ---------------------------------------------------------------------------
# F1 por fonema (macro)
# ---------------------------------------------------------------------------

def compute_per_phoneme_f1(ops: Sequence[EditOp]) -> dict[Token, dict]:
    """Calcular F1 individual para cada fonema que aparece en las operaciones.

    Útil para identificar qué sonidos concretos son problemáticos.

    Parámetros
    ----------
    ops :
        Lista de ``EditOp`` del comparador.

    Retorna
    -------
    dict[Token, dict]
        Mapa ``fonema → {"precision", "recall", "f1", "tp", "fp", "fn"}``.
        Solo incluye fonemas que aparecen al menos una vez.
    """
    # Acumular TP/FP/FN por fonema
    tp_map: dict[Token, int] = {}
    fp_map: dict[Token, int] = {}
    fn_map: dict[Token, int] = {}

    for op_dict in ops:
        op = op_dict.get("op", "")
        ref: Token | None = op_dict.get("ref")
        hyp: Token | None = op_dict.get("hyp")

        if op == "eq" and ref:
            tp_map[ref] = tp_map.get(ref, 0) + 1
        elif op == "ins" and hyp:
            fp_map[hyp] = fp_map.get(hyp, 0) + 1
        elif op == "del" and ref:
            fn_map[ref] = fn_map.get(ref, 0) + 1
        elif op == "sub":
            if hyp:
                fp_map[hyp] = fp_map.get(hyp, 0) + 1
            if ref:
                fn_map[ref] = fn_map.get(ref, 0) + 1

    all_phones: set[Token] = set(tp_map) | set(fp_map) | set(fn_map)
    result: dict[Token, dict] = {}

    for phone in sorted(all_phones):
        tp = tp_map.get(phone, 0)
        fp = fp_map.get(phone, 0)
        fn = fn_map.get(phone, 0)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        result[phone] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    return result


def compute_macro_f1(ops: Sequence[EditOp]) -> float:
    """Calcular F1 macro-promediado sobre todos los fonemas del inventario.

    Promedia el F1 de cada fonema sin ponderar por frecuencia, de modo que
    fonemas raros cuentan igual que los comunes.

    Retorna ``0.0`` si no hay fonemas en las operaciones.
    """
    per_phone = compute_per_phoneme_f1(ops)
    if not per_phone:
        return 0.0
    return round(sum(v["f1"] for v in per_phone.values()) / len(per_phone), 4)


# ---------------------------------------------------------------------------
# Integración con CompareResult
# ---------------------------------------------------------------------------

def enrich_with_f1(compare_result: dict) -> dict:
    """Añadir métricas F1 a un ``CompareResult`` existente.

    Modifica el campo ``meta`` del resultado in-place agregando:
    - ``f1`` (micro-averaged)
    - ``precision``
    - ``recall``
    - ``macro_f1``

    Parámetros
    ----------
    compare_result :
        Resultado de ``Comparator.compare()`` (modifica en lugar).

    Retorna
    -------
    dict
        El mismo diccionario con ``meta`` enriquecido.
    """
    ops = compare_result.get("ops", [])
    f1_metrics = compute_phoneme_f1(ops)
    macro = compute_macro_f1(ops)

    meta = compare_result.setdefault("meta", {})
    meta["f1"] = f1_metrics["f1"]
    meta["precision"] = f1_metrics["precision"]
    meta["recall"] = f1_metrics["recall"]
    meta["macro_f1"] = macro
    meta["f1_tp"] = f1_metrics["tp"]
    meta["f1_fp"] = f1_metrics["fp"]
    meta["f1_fn"] = f1_metrics["fn"]

    return compare_result


__all__ = [
    "compute_macro_f1",
    "compute_per_phoneme_f1",
    "compute_phoneme_f1",
    "enrich_with_f1",
]
