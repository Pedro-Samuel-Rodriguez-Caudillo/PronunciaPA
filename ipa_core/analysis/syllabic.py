"""Análisis silábico de secuencias IPA, opcionalmente guiado por timestamps.

Estrategia de segmentación
--------------------------
1. **Con timestamps** (Allosaurus ``emit_timestamps=True``):
   Detecta pausas inter-fonema > ``gap_threshold`` segundos como fronteras de
   sílaba.  El resultado se refina con estructura CV para distinguir onset /
   núcleo / coda.

2. **Sin timestamps** (solo IPA):
   Aplica el algoritmo de máximo ataque (*maximal onset principle*): cada
   consonante que puede ser onset se asocia a la sílaba siguiente.  Los
   núcleos son siempre las vocales IPA.

Limitaciones
------------
- No modela estructura métrica ni estrés suprasegmental.
- Grupos consonánticos complejos (p.ej. ``str``) se asignan como onset completo
  sin validar fonotaxis del idioma concreto.
- Diseñado para análisis fonético simple; no reemplaza un analizador morfológico.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


# ---------------------------------------------------------------------------
# Vocales IPA reconocidas como núcleos silábicos
# ---------------------------------------------------------------------------

# Vocales cardinales y sus equivalentes fonéticos más comunes
_IPA_VOWELS: frozenset[str] = frozenset(
    "aeiouæœɑɒɔɛɜɝɞɪɨɯʉʊʌʏɐɘɵɤɶ"
    # Vocales con diacríticos comunes (nasalizadas, largas, etc.) se detectan
    # por su carácter base: se comprueba si el primer carácter del token es vocal.
)

# Consonantes que nunca van en coda (solo onset) — simplificación universal
_ONSET_ONLY: frozenset[str] = frozenset()  # Depende del idioma; vacío por ahora


def _is_vowel(phone: str) -> bool:
    """Devuelve True si el fonema IPA es un núcleo silábico (vocal)."""
    if not phone:
        return False
    # Comprobar el carácter base (ignora diacríticos de longitud/tono)
    base = phone[0]
    return base in _IPA_VOWELS


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class SyllablePosition:
    """Posición de un fonema dentro de su sílaba."""
    onset: bool = False
    nucleus: bool = False
    coda: bool = False

    def label(self) -> str:
        if self.nucleus:
            return "nucleus"
        if self.onset:
            return "onset"
        return "coda"


@dataclass
class PhonemeInfo:
    """Información de un fonema en el contexto silábico."""
    phone: str
    syllable_index: int
    position_in_syllable: int        # 0-based dentro de la sílaba
    position: SyllablePosition = field(default_factory=SyllablePosition)
    start: Optional[float] = None    # segundos (de timestamp)
    end: Optional[float] = None      # segundos (de timestamp)

    @property
    def onset(self) -> bool:
        return self.position.onset

    @property
    def nucleus(self) -> bool:
        return self.position.nucleus

    @property
    def coda(self) -> bool:
        return self.position.coda


@dataclass
class Syllable:
    """Representa una sílaba con sus fonemas constituyentes."""
    index: int
    phonemes: list[PhonemeInfo] = field(default_factory=list)
    start: Optional[float] = None    # inicio de la primera fonema
    end: Optional[float] = None      # fin del último fonema

    @property
    def onset_phones(self) -> list[str]:
        return [p.phone for p in self.phonemes if p.onset]

    @property
    def nucleus_phones(self) -> list[str]:
        return [p.phone for p in self.phonemes if p.nucleus]

    @property
    def coda_phones(self) -> list[str]:
        return [p.phone for p in self.phonemes if p.coda]

    @property
    def ipa(self) -> str:
        return "".join(p.phone for p in self.phonemes)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "ipa": self.ipa,
            "onset": self.onset_phones,
            "nucleus": self.nucleus_phones,
            "coda": self.coda_phones,
            "start": self.start,
            "end": self.end,
        }


# ---------------------------------------------------------------------------
# Analizador principal
# ---------------------------------------------------------------------------

class SyllabicAnalyzer:
    """Agrupa secuencias de fonemas IPA en sílabas.

    Parámetros
    ----------
    gap_threshold : float
        Silencio mínimo entre fonemas (segundos) para insertar una frontera
        silábica cuando se usan timestamps.  Valor por defecto: 0.06 s (60 ms).
    """

    def __init__(self, gap_threshold: float = 0.06) -> None:
        self.gap_threshold = gap_threshold

    def analyze(
        self,
        tokens: Sequence[str],
        timestamps: Optional[Sequence[tuple[float, float]]] = None,
    ) -> list[Syllable]:
        """Analizar una secuencia IPA y devolver sus sílabas.

        Parámetros
        ----------
        tokens :
            Lista de fonemas IPA (p.ej. producida por Allosaurus).
        timestamps :
            Lista opcional de (inicio, fin) en segundos por fonema.
            Si se proporciona, debe tener la misma longitud que ``tokens``.

        Retorna
        -------
        list[Syllable]
            Sílabas en orden, cada una con phonemes etiquetados como
            onset / nucleus / coda.
        """
        tokens_list = list(tokens)
        if not tokens_list:
            return []

        # --- Detectar fronteras silábicas ---
        if timestamps and len(timestamps) == len(tokens_list):
            boundaries = self._boundaries_from_timestamps(tokens_list, list(timestamps))
        else:
            boundaries = self._boundaries_from_cv(tokens_list)

        # --- Agrupar tokens en sílabas ---
        raw_syllables = self._group_by_boundaries(tokens_list, boundaries, timestamps)

        # --- Asignar posiciones onset/nucleus/coda dentro de cada sílaba ---
        for syl in raw_syllables:
            self._assign_positions(syl)

        return raw_syllables

    # ------------------------------------------------------------------
    # Detección de fronteras
    # ------------------------------------------------------------------

    def _boundaries_from_timestamps(
        self,
        tokens: list[str],
        timestamps: list[tuple[float, float]],
    ) -> list[bool]:
        """Marca True en la posición i si hay una frontera ANTES del token i."""
        n = len(tokens)
        boundaries = [False] * n
        boundaries[0] = True  # primera sílaba siempre inicia aquí

        for i in range(1, n):
            prev_end = timestamps[i - 1][1]
            curr_start = timestamps[i][0]
            gap = curr_start - prev_end
            if gap >= self.gap_threshold:
                boundaries[i] = True
            elif _is_vowel(tokens[i]) and not _is_vowel(tokens[i - 1]):
                # Transición consonante → vocal sin pausa: heurística de onset
                # Aplicar solo si el token previo no es ya un núcleo
                # (para evitar separar diptongos)
                pass  # Dejar que _boundaries_from_cv complemente

        # Refinar con regla CV sobre lo que quedó dentro de cada grupo
        cv_hints = self._boundaries_from_cv(tokens)
        for i in range(1, n):
            if cv_hints[i]:
                boundaries[i] = True

        return boundaries

    def _boundaries_from_cv(self, tokens: list[str]) -> list[bool]:
        """Aplica máximo ataque: frontera antes de cada vocal salvo la primera."""
        n = len(tokens)
        if n == 0:
            return []

        # Posición de cada vocal
        vowel_positions = [i for i, t in enumerate(tokens) if _is_vowel(t)]
        if not vowel_positions:
            # Sin vocales: toda la secuencia es una sola "sílaba" consonántica
            return [True] + [False] * (n - 1)

        boundaries = [False] * n
        boundaries[0] = True

        for v_idx in vowel_positions:
            if v_idx == 0:
                continue
            # Retroceder hasta el inicio de la consonante más a la izquierda
            # que puede ser onset de esta vocal (máximo ataque)
            onset_start = v_idx
            # Buscar el limite: la vocal anterior o el inicio del array
            prev_nucleus = max(
                (p for p in vowel_positions if p < v_idx),
                default=-1,
            )
            # El onset puede comenzar después de la vocal anterior
            # (o desde el inicio si no hay vocal anterior)
            min_onset = prev_nucleus + 1
            j = v_idx - 1
            while j >= min_onset and not _is_vowel(tokens[j]):
                onset_start = j
                j -= 1
            if onset_start > 0:
                boundaries[onset_start] = True

        return boundaries

    # ------------------------------------------------------------------
    # Agrupación
    # ------------------------------------------------------------------

    def _group_by_boundaries(
        self,
        tokens: list[str],
        boundaries: list[bool],
        timestamps: Optional[Sequence[tuple[float, float]]],
    ) -> list[Syllable]:
        syllables: list[Syllable] = []
        current_phonemes: list[PhonemeInfo] = []
        syl_idx = 0

        for i, token in enumerate(tokens):
            ts = timestamps[i] if timestamps and len(timestamps) > i else None
            if boundaries[i] and current_phonemes:
                # Cerrar sílaba anterior
                syl = self._build_syllable(syl_idx, current_phonemes)
                syllables.append(syl)
                syl_idx += 1
                current_phonemes = []

            pinfo = PhonemeInfo(
                phone=token,
                syllable_index=syl_idx,
                position_in_syllable=len(current_phonemes),
                start=ts[0] if ts else None,
                end=ts[1] if ts else None,
            )
            current_phonemes.append(pinfo)

        if current_phonemes:
            syl = self._build_syllable(syl_idx, current_phonemes)
            syllables.append(syl)

        return syllables

    def _build_syllable(self, idx: int, phonemes: list[PhonemeInfo]) -> Syllable:
        start = phonemes[0].start
        end = phonemes[-1].end
        return Syllable(index=idx, phonemes=list(phonemes), start=start, end=end)

    # ------------------------------------------------------------------
    # Asignación de posiciones (onset / nucleus / coda)
    # ------------------------------------------------------------------

    def _assign_positions(self, syl: Syllable) -> None:
        """Etiquetar cada fonema de la sílaba como onset, nucleus o coda."""
        phones = syl.phonemes
        if not phones:
            return

        # Encontrar el primer núcleo (vocal)
        nucleus_idx = next(
            (i for i, p in enumerate(phones) if _is_vowel(p.phone)),
            None,
        )

        if nucleus_idx is None:
            # Sin vocal: todos son coda (sílaba consonántica, p.ej. /s/ en inglés)
            for p in phones:
                p.position.coda = True
            return

        for i, p in enumerate(phones):
            if i < nucleus_idx:
                p.position.onset = True
            elif i == nucleus_idx:
                p.position.nucleus = True
            else:
                # Comprobar si hay otra vocal (diptongo/núcleo complejo)
                if _is_vowel(p.phone):
                    p.position.nucleus = True
                else:
                    p.position.coda = True


# ---------------------------------------------------------------------------
# Función de conveniencia
# ---------------------------------------------------------------------------

def analyze_syllables(
    tokens: Sequence[str],
    timestamps: Optional[Sequence[tuple[float, float]]] = None,
    *,
    gap_threshold: float = 0.06,
) -> list[Syllable]:
    """Analizar una secuencia IPA y devolver sus sílabas.

    Función de conveniencia sobre :class:`SyllabicAnalyzer`.

    Parámetros
    ----------
    tokens :
        Fonemas IPA (p.ej. ``["e", "s", "p", "a", "ɲ", "a"]``).
    timestamps :
        Timestamps por fonema ``[(start, end), ...]`` opcionales.
    gap_threshold :
        Pausa mínima (s) para frontera silábica cuando hay timestamps.

    Retorna
    -------
    list[Syllable]
        Sílabas en orden con posiciones etiquetadas.
    """
    return SyllabicAnalyzer(gap_threshold=gap_threshold).analyze(tokens, timestamps)


def syllables_to_dict(syllables: list[Syllable]) -> list[dict]:
    """Serializar sílabas a una lista de dicts JSON-serializables."""
    return [s.to_dict() for s in syllables]


__all__ = [
    "PhonemeInfo",
    "Syllable",
    "SyllabicAnalyzer",
    "SyllablePosition",
    "analyze_syllables",
    "syllables_to_dict",
]
