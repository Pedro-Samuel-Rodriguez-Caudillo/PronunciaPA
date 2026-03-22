"""Análisis silábico basado en timestamps del ASR.

Usa los timestamps producidos por Allosaurus (o cualquier backend que
devuelva ``time_stamps`` en su ``ASRResult``) para segmentar la
transcripción IPA en sílabas.

Estructura silábica
-------------------
Una sílaba tiene estructura CV(C):
  - Onset (ataques): consonantes antes del núcleo.
  - Núcleo: vocal (o consonante silábica).
  - Coda: consonantes después del núcleo.

El algoritmo aplica la *Sonority Sequencing Principle* (SSP):
  - Obstruyentes < nasales < líquidas < glides < vocales
  - Los tokens se agrupan maximizando el onset (Maximal Onset Principle).

Integración con Allosaurus
--------------------------
Cuando ``emit_timestamps=True``, Allosaurus devuelve una lista de pares
``(t_start, t_end)`` sincronizada con la lista de tokens.  ``syllabify()``
puede recibir esos timestamps para enriquecer cada sílaba con tiempos.

Uso
---
::

    from ipa_core.analysis.syllabic import syllabify, Syllable
    tokens = ["p", "a", "l", "a", "β", "r", "a"]
    sylls = syllabify(tokens)
    # → [Syllable(onset=["p"], nucleus="a", coda=[]),
    #    Syllable(onset=["l"], nucleus="a", coda=[]),
    #    Syllable(onset=["β", "r"], nucleus="a", coda=[])]
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Sequence

from ipa_core.types import Token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Jerarquía de sonoridad (Sonority Hierarchy) — derivada de panphon
# ---------------------------------------------------------------------------
# Valor más alto = más sonoro.  Vocales = 6 (pico silábico).
#
# ANTES: diccionario estático con ~80 fonemas hardcodeados.
#        Fonemas nuevos (hindi, árabe…) requerían entradas manuales.
# AHORA: se derivan automáticamente de los rasgos SPE de panphon (~6 000
#        segmentos IPA) usando la escala clásica de sonoridad:
#
#   6 — vocales          [+syllabic]
#   5 — glides           [+sonorant, +continuant, −consonantal]
#   4 — líquidas         [+sonorant, +consonantal, −nasal]
#   3 — nasales          [+sonorant, +nasal]
#   2 — fricativas       [−sonorant, +continuant]
#   1 — oclusivas        [−sonorant, −continuant]
#
# Un pequeño diccionario de sobreescrituras (_SONORITY_OVERRIDES) cubre
# casos límite: laringales (panphon las marca [+sonorant] pero para el
# SSP se comportan como fricativas/oclusivas) y africadas multi-carácter
# que panphon puede no parsear como unidad.
# ---------------------------------------------------------------------------

os.environ.setdefault("PYTHONUTF8", "1")

try:
    import panphon as _panphon

    _FT = _panphon.FeatureTable()
    _PANPHON_OK = True
    logger.debug("panphon disponible para sonoridad (%s segmentos)", len(_FT.segments))
except Exception as _exc:  # pragma: no cover
    _FT = None
    _PANPHON_OK = False
    logger.warning("panphon no disponible — sonoridad limitada a overrides: %s", _exc)

# Sobreescrituras manuales para fonemas cuya clasificación SPE
# de panphon no se mapea bien al SSP, o que panphon no reconoce como
# segmentos únicos (africadas tokenizadas sin tie-bar).
_SONORITY_OVERRIDES: dict[str, int] = {
    # Laringales: panphon → [+sonorant] pero el SSP las trata como fric./ocl.
    "h": 2, "ɦ": 2, "ʔ": 1,
    # Africadas comunes (tokens multi-char que panphon puede no parsear)
    "tʃ": 2, "dʒ": 2, "ts": 2, "dz": 2,
    "t͡ʃ": 2, "d͡ʒ": 2, "t͡s": 2, "d͡z": 2,
    "pf": 2,  # alemán
    # ASCII 'g' (U+0067) — panphon espera IPA ɡ (U+0261)
    "g": 1,
}


def _derive_sonority_panphon(phone: str) -> int | None:
    """Derivar sonoridad a partir de los rasgos SPE de panphon."""
    if not _PANPHON_OK or _FT is None:
        return None
    fts = _FT.word_fts(phone)
    if not fts:
        return None
    
    seg = fts[0]
    return _map_features_to_sonority(seg)


def _map_features_to_sonority(seg: dict[str, int]) -> int | None:
    """Mapea rasgos de panphon a la escala de sonoridad SSP."""
    if seg["syl"] == 1:
        return 6
    if seg["son"] == 1:
        return _sonorant_sonority(seg)
    return 2 if seg["cont"] == 1 else 1


def _sonorant_sonority(seg: dict[str, int]) -> int | None:
    """SSP para sonorantes: glides (5), líquidas (4), nasales (3)."""
    if seg["nas"] == 1:
        return 3
    if seg["cons"] == -1:
        return 5
    if seg["cons"] == 1:
        return 4
    return None


@lru_cache(maxsize=512)
def _sonority(token: Token) -> int:
    """Obtener nivel de sonoridad: overrides → panphon → fallbacks → 0."""
    if token in _SONORITY_OVERRIDES:
        return _SONORITY_OVERRIDES[token]
    
    derived = _derive_sonority_panphon(token)
    if derived is not None:
        return derived
        
    return _manual_sonority_fallback(token)


def _manual_sonority_fallback(phone: str) -> int:
    """Heurística manual para símbolos comunes si panphon no está disponible."""
    p = phone.lower()
    if p in ("a", "e", "i", "o", "u", "y", "w", "ɑ", "ɛ", "ɪ", "ɔ", "ʊ", "ʌ", "ə"):
        return 6
    if p in ("l", "r", "ɾ", "ʀ", "ɹ", "ɭ", "ʎ", "ʟ"):
        return 4
    return _manual_low_sonority_fallback(p)


def _manual_low_sonority_fallback(p: str) -> int:
    if p in ("m", "n", "ŋ", "ɲ", "ɳ", "ɱ"):
        return 3
    if p in ("s", "z", "ʃ", "ʒ", "f", "v", "x", "θ", "ð", "χ", "ʁ", "ç", "ʝ"):
        return 2
    if p in ("p", "b", "t", "d", "k", "ɡ", "g", "q", "ʔ"):
        return 1
    return 0


def _is_vowel(token: Token) -> bool:
    return _sonority(token) == 6


@dataclass
class Syllable:
    """Representación de una sílaba IPA con estructura onset-núcleo-coda.

    Campos
    ------
    onset : list[Token]
        Consonantes del ataque (previas al núcleo).
    nucleus : Token
        Vocal o consonante silábica (núcleo).
    coda : list[Token]
        Consonantes de la coda (posteriores al núcleo).
    t_start : float | None
        Timestamp de inicio (si se proporcionaron timestamps del ASR).
    t_end : float | None
        Timestamp de fin.
    """

    onset: list[Token] = field(default_factory=list)
    nucleus: Token = ""
    coda: list[Token] = field(default_factory=list)
    t_start: Optional[float] = None
    t_end: Optional[float] = None

    @property
    def tokens(self) -> list[Token]:
        """Todos los tokens de la sílaba en orden."""
        return self.onset + [self.nucleus] + self.coda

    @property
    def ipa(self) -> str:
        """Transcripción IPA de la sílaba."""
        return "".join(self.tokens)

    def __repr__(self) -> str:
        ts = f" [{self.t_start:.2f}-{self.t_end:.2f}]" if self.t_start is not None else ""
        return f"Syllable({self.ipa!r}{ts})"


def syllabify(
    tokens: Sequence[Token],
    *,
    timestamps: Optional[Sequence[tuple[float, float]]] = None,
) -> list[Syllable]:
    """Segmentar una secuencia de tokens IPA en sílabas."""
    tokens_list = list(tokens)
    ts = _validate_timestamps(tokens_list, timestamps)
    
    nuclei_positions = [i for i, t in enumerate(tokens_list) if _is_vowel(t)]

    if not nuclei_positions:
        return _handle_no_nuclei(tokens_list, ts)

    return _build_syllables(tokens_list, nuclei_positions, ts)


def _validate_timestamps(tokens: list[Token], ts: Optional[Sequence[tuple[float, float]]]) -> Optional[list[tuple[float, float]]]:
    if ts is None:
        return None
    if len(ts) != len(tokens):
        return None
    return list(ts)


def _handle_no_nuclei(tokens: list[Token], ts: Optional[list[tuple[float, float]]]) -> list[Syllable]:
    if not tokens:
        return []
    syll = Syllable(onset=tokens, nucleus="")
    if ts:
        syll.t_start = ts[0][0]
        syll.t_end = ts[-1][1]
    return [syll]


def _build_syllables(tokens: list[Token], nuclei: list[int], ts: Optional[list[tuple[float, float]]]) -> list[Syllable]:
    syllables: list[Syllable] = []
    prev_nucleus_end = 0

    for idx, nucleus_pos in enumerate(nuclei):
        next_pos = nuclei[idx + 1] if idx + 1 < len(nuclei) else len(tokens)
        inter = tokens[nucleus_pos + 1 : next_pos]
        
        maximal_onset = _calculate_maximal_onset(idx, nuclei, inter)
        
        coda = inter[: len(inter) - maximal_onset]
        onset = tokens[prev_nucleus_end : nucleus_pos]

        syll = Syllable(onset=list(onset), nucleus=tokens[nucleus_pos], coda=list(coda))
        _attach_timestamps(syll, prev_nucleus_end, nucleus_pos, coda, ts)
        
        syllables.append(syll)
        prev_nucleus_end = nucleus_pos + 1 + len(coda)

    return syllables


def _calculate_maximal_onset(idx: int, nuclei: list[int], inter: list[Token]) -> int:
    if idx + 1 >= len(nuclei):
        return 0
    for j in range(len(inter)):
        if _valid_onset(inter[j:]):
            return len(inter) - j
    return 0


def _attach_timestamps(syll: Syllable, start: int, nucleus_pos: int, coda: list[Token], ts: Optional[list[tuple[float, float]]]) -> None:
    if ts is None:
        return
    syll_indices = list(range(start, nucleus_pos + 1 + len(coda)))
    if syll_indices:
        syll.t_start = ts[syll_indices[0]][0]
        syll.t_end = ts[syll_indices[-1]][1]


def _valid_onset(tokens: list[Token]) -> bool:
    """Verificar si una secuencia puede constituir un onset válido (SSP)."""
    if not tokens:
        return True
    # El onset debe tener sonoridad no-decreciente hacia el núcleo
    for i in range(len(tokens) - 1):
        if _sonority(tokens[i]) > _sonority(tokens[i + 1]):
            return False
    return True


def get_syllable_count(tokens: Sequence[Token]) -> int:
    """Contar el número de sílabas en una secuencia de tokens."""
    return len(syllabify(tokens))


def get_syllabic_position(
    tokens: Sequence[Token],
    token_index: int,
) -> dict[str, object]:
    """Determinar la posición silábica de un token dentro de la secuencia."""
    syllables = syllabify(tokens)
    offset = 0
    for syll_idx, syll in enumerate(syllables):
        end = offset + len(syll.tokens)
        if offset <= token_index < end:
            return _build_syllabic_position_res(syll, syll_idx, len(syllables), token_index - offset)
        offset = end
    return {"syllable_index": -1, "position": "unknown", "syllable_position": "unknown"}


def _build_syllabic_position_res(syll: Syllable, idx: int, total: int, local_idx: int) -> dict[str, object]:
    return {
        "syllable_index": idx,
        "position": _determine_role(syll, local_idx),
        "syllable_position": _determine_word_position(idx, total),
    }


def _determine_role(syll: Syllable, local_idx: int) -> str:
    if local_idx < len(syll.onset):
        return "onset"
    if local_idx == len(syll.onset):
        return "nucleus"
    return "coda"


def _determine_word_position(idx: int, total: int) -> str:
    if total == 1:
        return "monosyllabic"
    if idx == 0:
        return "initial"
    if idx == total - 1:
        return "final"
    return "medial"


__all__ = [
    "Syllable",
    "syllabify",
    "get_syllable_count",
    "get_syllabic_position",
    "_sonority",
    "_is_vowel",
]
