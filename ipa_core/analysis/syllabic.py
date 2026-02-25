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
    """Derivar sonoridad a partir de los rasgos SPE de panphon.

    Retorna ``None`` si panphon no reconoce el fonema.
    """
    if not _PANPHON_OK or _FT is None:
        return None
    fts = _FT.word_fts(phone)
    if not fts:
        return None
    seg = fts[0]
    syl = seg["syl"]
    son = seg["son"]
    cont = seg["cont"]
    nas = seg["nas"]
    cons = seg["cons"]

    # 6: vocales [+syllabic]
    if syl == 1:
        return 6
    # 5: glides [+sonorant, +continuant, −consonantal]
    if son == 1 and cont == 1 and cons == -1:
        return 5
    # 4: líquidas [+sonorant, +consonantal, −nasal]
    if son == 1 and cons == 1 and nas != 1:
        return 4
    # 3: nasales [+sonorant, +nasal]
    if son == 1 and nas == 1:
        return 3
    # 2: fricativas [−sonorant, +continuant]
    if son != 1 and cont == 1:
        return 2
    # 1: oclusivas [−sonorant, −continuant]
    if son != 1 and cont != 1:
        return 1
    return None


@lru_cache(maxsize=512)
def _sonority(token: Token) -> int:
    """Obtener nivel de sonoridad: overrides → panphon → 0."""
    if token in _SONORITY_OVERRIDES:
        return _SONORITY_OVERRIDES[token]
    derived = _derive_sonority_panphon(token)
    if derived is not None:
        return derived
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
    """Segmentar una secuencia de tokens IPA en sílabas.

    Aplica el Principio de Sonoridad Secuencial (SSP) con Maximal Onset
    para distribuir consonantes entre coda del sílaba previa y onset de
    la siguiente.

    Parámetros
    ----------
    tokens : Sequence[Token]
        Lista de símbolos IPA a segmentar.
    timestamps : Sequence[(float, float)], optional
        Lista de (t_start, t_end) por token, del mismo largo que tokens.
        Si se proporciona, cada sílaba incluirá sus tiempos.

    Retorna
    -------
    list[Syllable]
        Sílabas en orden.  Si no hay vocales, retorna una sílaba con
        todos los tokens en onset (consonante-sílaba).
    """
    tokens_list = list(tokens)
    ts = list(timestamps) if timestamps else None
    if ts is not None and len(ts) != len(tokens_list):
        ts = None  # timestamps desalineados → ignorar

    # Encontrar posiciones de vocales (núcleos)
    nuclei_positions = [i for i, t in enumerate(tokens_list) if _is_vowel(t)]

    if not nuclei_positions:
        # Sin vocales: toda la secuencia es un onset (p.ej. "str" en inglés)
        syll = Syllable(onset=tokens_list, nucleus="")
        if ts:
            syll.t_start = ts[0][0]
            syll.t_end = ts[-1][1]
        return [syll] if tokens_list else []

    syllables: list[Syllable] = []
    prev_nucleus_end = 0

    for idx, nucleus_pos in enumerate(nuclei_positions):
        # Límite derecho de la sílaba actual:
        # la siguiente vocal o el final del token stream
        next_nucleus_pos = (
            nuclei_positions[idx + 1] if idx + 1 < len(nuclei_positions) else len(tokens_list)
        )

        # Tokens disponibles entre el núcleo actual y el siguiente núcleo
        inter = tokens_list[nucleus_pos + 1 : next_nucleus_pos]

        # Maximal Onset: cuántas consonantes del inter pueden ir como onset
        # del siguiente sílaba (sin romper SSP)?
        maximal_onset = 0
        if idx + 1 < len(nuclei_positions):
            for j in range(len(inter)):
                candidate_onset = inter[j:]
                # El onset debe tener sonoridad creciente hacia el núcleo
                if _valid_onset(candidate_onset):
                    maximal_onset = len(candidate_onset)
                    break

        coda = inter[: len(inter) - maximal_onset]
        onset = tokens_list[prev_nucleus_end : nucleus_pos]

        syll = Syllable(
            onset=list(onset),
            nucleus=tokens_list[nucleus_pos],
            coda=list(coda),
        )

        # Calcular timestamps de la sílaba
        if ts is not None:
            syll_indices = list(range(prev_nucleus_end, nucleus_pos + 1 + len(coda)))
            if syll_indices:
                syll.t_start = ts[syll_indices[0]][0]
                syll.t_end = ts[syll_indices[-1]][1]

        syllables.append(syll)
        prev_nucleus_end = nucleus_pos + 1 + len(coda)

    return syllables


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
    """Determinar la posición silábica de un token dentro de la secuencia.

    Retorna un diccionario con:
    - ``syllable_index`` : int — índice de la sílaba (0-based)
    - ``position`` : str — "onset", "nucleus", o "coda"
    - ``syllable_position`` : str — "initial", "medial", o "final" en la palabra
    """
    syllables = syllabify(tokens)
    offset = 0
    for syll_idx, syll in enumerate(syllables):
        syll_tokens = syll.tokens
        end = offset + len(syll_tokens)
        if offset <= token_index < end:
            local_idx = token_index - offset
            if local_idx < len(syll.onset):
                role = "onset"
            elif local_idx == len(syll.onset):
                role = "nucleus"
            else:
                role = "coda"
            n_sylls = len(syllables)
            if n_sylls == 1:
                word_pos = "monosyllabic"
            elif syll_idx == 0:
                word_pos = "initial"
            elif syll_idx == n_sylls - 1:
                word_pos = "final"
            else:
                word_pos = "medial"
            return {
                "syllable_index": syll_idx,
                "position": role,
                "syllable_position": word_pos,
            }
        offset = end
    return {"syllable_index": -1, "position": "unknown", "syllable_position": "unknown"}


__all__ = [
    "Syllable",
    "syllabify",
    "get_syllable_count",
    "get_syllabic_position",
    "_sonority",
    "_is_vowel",
]
