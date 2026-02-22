"""Suprasegmentales opcionales en el nivel fonético.

Los suprasegmentales son rasgos prosódicos que se superponen sobre los
segmentos fonémicos: acento, tono, duración, nasalización, aspiración.
En IPA se representan con diacríticos o símbolos especiales.

Este módulo proporciona:
1. Detección de marcas suprasegmentales en una transcripción IPA.
2. Separación de segmentos y suprasegmentales.
3. Normalización configurable (conservar o eliminar suprasegmentales
   según el modo de evaluación).

Suprasegmentales soportados
----------------------------
Símbolo | Nombre            | Categoría
--------|-------------------|----------
ˈ       | Acento primario   | stress
ˌ       | Acento secundario | stress
ː       | Duración larga    | length
ˑ       | Duración semilarga| length
.       | Límite silábico   | boundary
|       | Límite menor      | boundary
‖       | Límite mayor      | boundary
↗       | Tono ascendente   | tone
↘       | Tono descendente  | tone
̃       | Nasalización (diacrít.) | manner
ʰ       | Aspiración        | manner
ʼ       | Eyección          | manner
ʷ       | Labialización     | manner

Modos de tratamiento
---------------------
- ``"strict"``  — preservar todos los suprasegmentales en comparación.
- ``"phonemic"`` — eliminar todos los suprasegmentales (comparar sólo
  segmentos fonémicos abstractos).  Modo por defecto.
- ``"prosodic"`` — conservar acento y tono, eliminar duración/límites.

Uso
---
::

    from ipa_core.phonology.suprasegmentals import strip_suprasegmentals
    clean = strip_suprasegmentals("ˈpa.ta.ˌtas")
    # → "patatas"

    from ipa_core.phonology.suprasegmentals import extract_suprasegmentals
    segs, supra = extract_suprasegmentals("ˈkaˑsa")
    # segs → ["k", "a", "s", "a"]
    # supra → [{"type": "stress", "symbol": "ˈ", "before_index": 0}, ...]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from ipa_core.types import Token


# ---------------------------------------------------------------------------
# Catálogo de símbolos suprasegmentales
# ---------------------------------------------------------------------------

SuprasegmentalCategory = Literal["stress", "length", "boundary", "tone", "manner"]

@dataclass(frozen=True)
class SuprasegmentalMark:
    """Descripción de una marca suprasegmental."""
    symbol: str
    name: str
    category: SuprasegmentalCategory


SUPRASEGMENTALS: list[SuprasegmentalMark] = [
    # Acento
    SuprasegmentalMark("ˈ", "primary_stress", "stress"),
    SuprasegmentalMark("ˌ", "secondary_stress", "stress"),
    # Longitud
    SuprasegmentalMark("ː", "long", "length"),
    SuprasegmentalMark("ˑ", "half_long", "length"),
    # Límites
    SuprasegmentalMark(".", "syllable_boundary", "boundary"),
    SuprasegmentalMark("|", "minor_boundary", "boundary"),
    SuprasegmentalMark("‖", "major_boundary", "boundary"),
    # Tono (flechas tonales)
    SuprasegmentalMark("↗", "rising_tone", "tone"),
    SuprasegmentalMark("↘", "falling_tone", "tone"),
    SuprasegmentalMark("↑", "extra_high_tone", "tone"),
    SuprasegmentalMark("↓", "extra_low_tone", "tone"),
    # Diacríticos de manera (frecuentemente suprasegmentales en contexto)
    SuprasegmentalMark("ʰ", "aspirated", "manner"),
    SuprasegmentalMark("ʼ", "ejective", "manner"),
    SuprasegmentalMark("ʷ", "labialized", "manner"),
    SuprasegmentalMark("ʲ", "palatalized", "manner"),
    SuprasegmentalMark("ˠ", "velarized", "manner"),
    SuprasegmentalMark("ˤ", "pharyngealized", "manner"),
    SuprasegmentalMark("\u0303", "nasalized", "manner"),   # combining tilde ̃
    SuprasegmentalMark("\u02B0", "aspirated_h", "manner"), # ʰ (alt encoding)
    SuprasegmentalMark("ⁿ", "prenasalized", "manner"),
]

_SUPRA_SYMBOLS: frozenset[str] = frozenset(m.symbol for m in SUPRASEGMENTALS)
_SUPRA_BY_SYMBOL: dict[str, SuprasegmentalMark] = {m.symbol: m for m in SUPRASEGMENTALS}

# Categorías a preservar por modo
_MODE_KEEP: dict[str, frozenset[SuprasegmentalCategory]] = {
    "strict": frozenset({"stress", "length", "boundary", "tone", "manner"}),
    "prosodic": frozenset({"stress", "tone"}),
    "phonemic": frozenset(),  # eliminar todo
}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def strip_suprasegmentals(
    ipa: str,
    *,
    mode: str = "phonemic",
) -> str:
    """Eliminar (o conservar) marcas suprasegmentales de una cadena IPA.

    Parámetros
    ----------
    ipa : str
        Cadena IPA con posibles suprasegmentales.
    mode : str
        Modo de normalización:
        - ``"phonemic"``  — eliminar todo (defecto).
        - ``"prosodic"``  — conservar acento y tono.
        - ``"strict"``    — conservar todo.

    Retorna
    -------
    str
        Cadena IPA normalizada.
    """
    keep_cats = _MODE_KEEP.get(mode, frozenset())
    result = []
    for char in ipa:
        mark = _SUPRA_BY_SYMBOL.get(char)
        if mark is None:
            result.append(char)
        elif mark.category in keep_cats:
            result.append(char)
        # else: eliminar
    return "".join(result)


@dataclass
class ExtractedSuprasegmental:
    """Una marca suprasegmental extraída con su posición en la secuencia."""
    symbol: str
    name: str
    category: SuprasegmentalCategory
    before_index: int  # índice del segmento anterior a esta marca (-1 = inicio)


def extract_suprasegmentals(
    ipa: str,
) -> tuple[list[Token], list[ExtractedSuprasegmental]]:
    """Separar segmentos fonémicos de marcas suprasegmentales.

    Parámetros
    ----------
    ipa : str
        Cadena IPA a analizar.

    Retorna
    -------
    tuple[list[Token], list[ExtractedSuprasegmental]]
        - lista de segmentos fonémicos (sin suprasegmentales).
        - lista de marcas encontradas con su posición relativa.
    """
    segments: list[Token] = []
    marks: list[ExtractedSuprasegmental] = []
    seg_idx = -1

    for char in ipa:
        mark = _SUPRA_BY_SYMBOL.get(char)
        if mark is not None:
            marks.append(ExtractedSuprasegmental(
                symbol=mark.symbol,
                name=mark.name,
                category=mark.category,
                before_index=seg_idx,
            ))
        else:
            segments.append(char)
            seg_idx += 1

    return segments, marks


def has_suprasegmentals(ipa: str) -> bool:
    """Verificar si la cadena IPA contiene marcas suprasegmentales."""
    return any(c in _SUPRA_SYMBOLS for c in ipa)


def filter_tokens_by_mode(
    tokens: Sequence[Token],
    *,
    mode: str = "phonemic",
) -> list[Token]:
    """Filtrar tokens IPA según el modo (eliminar suprasegmentales si aplica).

    A diferencia de ``strip_suprasegmentals``, trabaja sobre una lista
    de tokens ya tokenizados.

    Parámetros
    ----------
    tokens : Sequence[Token]
        Lista de tokens IPA (cada token puede ser un símbolo o diacrítico).
    mode : str
        Modo de evaluación.

    Retorna
    -------
    list[Token]
        Tokens filtrados.
    """
    keep_cats = _MODE_KEEP.get(mode, frozenset())
    result = []
    for t in tokens:
        mark = _SUPRA_BY_SYMBOL.get(t)
        if mark is None:
            result.append(t)
        elif mark.category in keep_cats:
            result.append(t)
    return result


__all__ = [
    "SUPRASEGMENTALS",
    "SuprasegmentalMark",
    "SuprasegmentalCategory",
    "ExtractedSuprasegmental",
    "strip_suprasegmentals",
    "extract_suprasegmentals",
    "has_suprasegmentals",
    "filter_tokens_by_mode",
]
