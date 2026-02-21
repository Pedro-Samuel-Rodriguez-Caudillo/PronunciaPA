"""Generador de pares mínimos para ejercicios de pronunciación.

Un par mínimo es un par de palabras que difieren en exactamente un fonema.
Ejemplo: /pata/ vs /bata/ — contraste /p/ ↔ /b/.

Uso
---
>>> from ipa_core.packs.minimal_pairs import MinimalPairGenerator
>>> gen = MinimalPairGenerator.from_lexicon(lexicon, language="es-mx")
>>> pairs = gen.find_pairs_for_phoneme("r")
>>> curated = gen.get_curated_pairs(language="es-mx")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipos de datos
# ---------------------------------------------------------------------------

@dataclass
class MinimalPair:
    """Par mínimo: dos palabras que contrastan en un único fonema."""

    word1: str
    """Primera palabra del contraste."""

    ipa1: str
    """Transcripción IPA de word1."""

    word2: str
    """Segunda palabra del contraste."""

    ipa2: str
    """Transcripción IPA de word2."""

    phoneme1: str
    """Fonema de word1 en la posición de contraste."""

    phoneme2: str
    """Fonema de word2 en la posición de contraste."""

    position: int
    """Índice (0-based) del fonema en contraste."""

    difficulty: int = 1
    """Nivel de dificultad: 1 (fácil) a 3 (difícil)."""

    language: str = "es"
    """Código de idioma (BCP-47)."""

    tags: list[str] = field(default_factory=list)
    """Etiquetas: 'onset', 'coda', 'nucleus', 'voicing', 'place', etc."""

    def contrast_label(self) -> str:
        """Etiqueta legible del contraste, p.ej. '/p/ vs /b/'."""
        return f"/{self.phoneme1}/ vs /{self.phoneme2}/"

    def as_dict(self) -> dict:
        return {
            "word1": self.word1,
            "ipa1": self.ipa1,
            "word2": self.word2,
            "ipa2": self.ipa2,
            "phoneme1": self.phoneme1,
            "phoneme2": self.phoneme2,
            "position": self.position,
            "difficulty": self.difficulty,
            "language": self.language,
            "tags": self.tags,
            "contrast_label": self.contrast_label(),
        }


# ---------------------------------------------------------------------------
# Pares curados por idioma (hardcoded, alta calidad pedagógica)
# ---------------------------------------------------------------------------

#: Pares curados para español mexicano.
_CURATED_ES_MX: list[MinimalPair] = [
    # ── Vibrantes: /r/ (múltiple) vs /ɾ/ (simple) ──────────────────
    # Este es EL contraste más difícil del español para hablantes de inglés.
    MinimalPair("pero", "p e ɾ o", "perro", "p e r o", "ɾ", "r", 2,
                difficulty=3, language="es-mx", tags=["rhotic", "place"]),
    MinimalPair("caro", "k a ɾ o", "carro", "k a r o", "ɾ", "r", 2,
                difficulty=3, language="es-mx", tags=["rhotic", "coda"]),
    MinimalPair("moro", "m o ɾ o", "morro", "m o r o", "ɾ", "r", 2,
                difficulty=3, language="es-mx", tags=["rhotic"]),
    MinimalPair("cero", "s e ɾ o", "cerro", "s e r o", "ɾ", "r", 2,
                difficulty=3, language="es-mx", tags=["rhotic"]),
    MinimalPair("para", "p a ɾ a", "parra", "p a r a", "ɾ", "r", 2,
                difficulty=3, language="es-mx", tags=["rhotic"]),

    # ── Nasales: /n/ vs /ɲ/ (ñ) ─────────────────────────────────────
    MinimalPair("año", "a ɲ o", "ano", "a n o", "ɲ", "n", 1,
                difficulty=2, language="es-mx", tags=["nasal", "place"]),
    MinimalPair("soña", "s o ɲ a", "sona", "s o n a", "ɲ", "n", 1,
                difficulty=2, language="es-mx", tags=["nasal", "place"]),
    MinimalPair("ñoño", "ɲ o ɲ o", "nono", "n o n o", "ɲ", "n", 0,
                difficulty=2, language="es-mx", tags=["nasal", "place"]),

    # ── Oclusivas sordas/sonoras: /p/ vs /b/ ────────────────────────
    MinimalPair("pata", "p a t a", "bata", "b a t a", "p", "b", 0,
                difficulty=1, language="es-mx", tags=["stop", "voicing", "onset"]),
    MinimalPair("poca", "p o k a", "boca", "b o k a", "p", "b", 0,
                difficulty=1, language="es-mx", tags=["stop", "voicing"]),

    # ── Oclusivas: /t/ vs /d/ ────────────────────────────────────────
    MinimalPair("tío", "t i o", "dio", "d i o", "t", "d", 0,
                difficulty=1, language="es-mx", tags=["stop", "voicing"]),
    MinimalPair("toma", "t o m a", "doma", "d o m a", "t", "d", 0,
                difficulty=1, language="es-mx", tags=["stop", "voicing"]),

    # ── Oclusivas velares: /k/ vs /g/ ────────────────────────────────
    MinimalPair("cama", "k a m a", "gama", "g a m a", "k", "g", 0,
                difficulty=1, language="es-mx", tags=["stop", "voicing", "velar"]),
    MinimalPair("cota", "k o t a", "gota", "g o t a", "k", "g", 0,
                difficulty=1, language="es-mx", tags=["stop", "voicing", "velar"]),

    # ── Fricativas: /s/ vs /x/ (j/g) ────────────────────────────────
    MinimalPair("saja", "s a x a", "jaja", "x a x a", "s", "x", 0,
                difficulty=2, language="es-mx", tags=["fricative", "place"]),
    MinimalPair("cosa", "k o s a", "coja", "k o x a", "s", "x", 2,
                difficulty=2, language="es-mx", tags=["fricative", "place"]),

    # ── Africada: /tʃ/ vs /ʃ/ ───────────────────────────────────────
    MinimalPair("chico", "tʃ i k o", "shico", "ʃ i k o", "tʃ", "ʃ", 0,
                difficulty=2, language="es-mx", tags=["affricate", "fricative"]),

    # ── Vocales: /e/ vs /i/ ──────────────────────────────────────────
    MinimalPair("pesa", "p e s a", "pisa", "p i s a", "e", "i", 1,
                difficulty=1, language="es-mx", tags=["vowel", "height"]),
    MinimalPair("seta", "s e t a", "sita", "s i t a", "e", "i", 1,
                difficulty=1, language="es-mx", tags=["vowel", "height"]),

    # ── Vocales: /o/ vs /u/ ──────────────────────────────────────────
    MinimalPair("toro", "t o ɾ o", "turo", "t u ɾ o", "o", "u", 1,
                difficulty=1, language="es-mx", tags=["vowel", "height"]),
    MinimalPair("boca", "b o k a", "buca", "b u k a", "o", "u", 1,
                difficulty=1, language="es-mx", tags=["vowel", "height"]),

    # ── Vocales: /a/ vs /e/ ──────────────────────────────────────────
    MinimalPair("casa", "k a s a", "queso", "k e s o", "a", "e", 1,
                difficulty=1, language="es-mx", tags=["vowel"]),

    # ── Lateral: /l/ vs /r/ ──────────────────────────────────────────
    MinimalPair("loca", "l o k a", "roca", "r o k a", "l", "r", 0,
                difficulty=2, language="es-mx", tags=["lateral", "rhotic"]),
    MinimalPair("polo", "p o l o", "poro", "p o ɾ o", "l", "ɾ", 2,
                difficulty=2, language="es-mx", tags=["lateral", "rhotic"]),

    # ── Nasal: /m/ vs /n/ ────────────────────────────────────────────
    MinimalPair("mapa", "m a p a", "napa", "n a p a", "m", "n", 0,
                difficulty=1, language="es-mx", tags=["nasal", "place"]),
    MinimalPair("cama", "k a m a", "cana", "k a n a", "m", "n", 2,
                difficulty=1, language="es-mx", tags=["nasal", "place"]),
]

#: Pares curados para inglés americano.
_CURATED_EN_US: list[MinimalPair] = [
    # ── /θ/ vs /s/ (this vs sis) ────────────────────────────────────
    MinimalPair("think", "θ ɪ ŋ k", "sink", "s ɪ ŋ k", "θ", "s", 0,
                difficulty=2, language="en-us", tags=["fricative", "dental"]),
    MinimalPair("math", "m æ θ", "mass", "m æ s", "θ", "s", 2,
                difficulty=2, language="en-us", tags=["fricative", "dental", "coda"]),

    # ── /ð/ vs /d/ ───────────────────────────────────────────────────
    MinimalPair("then", "ð ɛ n", "den", "d ɛ n", "ð", "d", 0,
                difficulty=2, language="en-us", tags=["fricative", "dental", "voicing"]),

    # ── /æ/ vs /ɛ/ ───────────────────────────────────────────────────
    MinimalPair("bad", "b æ d", "bed", "b ɛ d", "æ", "ɛ", 1,
                difficulty=2, language="en-us", tags=["vowel", "height"]),
    MinimalPair("bag", "b æ ɡ", "beg", "b ɛ ɡ", "æ", "ɛ", 1,
                difficulty=2, language="en-us", tags=["vowel", "height"]),

    # ── /ɪ/ vs /iː/ ──────────────────────────────────────────────────
    MinimalPair("ship", "ʃ ɪ p", "sheep", "ʃ iː p", "ɪ", "iː", 1,
                difficulty=2, language="en-us", tags=["vowel", "length"]),
    MinimalPair("bit", "b ɪ t", "beat", "b iː t", "ɪ", "iː", 1,
                difficulty=2, language="en-us", tags=["vowel", "length"]),

    # ── /p/ vs /b/ ───────────────────────────────────────────────────
    MinimalPair("pat", "p æ t", "bat", "b æ t", "p", "b", 0,
                difficulty=1, language="en-us", tags=["stop", "voicing"]),

    # ── /v/ vs /b/ ───────────────────────────────────────────────────
    MinimalPair("vat", "v æ t", "bat", "b æ t", "v", "b", 0,
                difficulty=2, language="en-us", tags=["fricative", "stop", "voicing"]),
]

#: Registro por idioma.
_CURATED: dict[str, list[MinimalPair]] = {
    "es-mx": _CURATED_ES_MX,
    "es": _CURATED_ES_MX,
    "en-us": _CURATED_EN_US,
    "en": _CURATED_EN_US,
}


# ---------------------------------------------------------------------------
# Generador dinámico desde léxico
# ---------------------------------------------------------------------------

class MinimalPairGenerator:
    """Genera pares mínimos a partir de un léxico IPA.

    Parámetros
    ----------
    lexicon : dict[str, list[str]]
        Diccionario ``{palabra: [lista_de_fonemas]}``.
        Los fonemas deben estar ya tokenizados (un símbolo IPA por elemento).
    language : str
        Código de idioma (p.ej. ``"es-mx"``).
    """

    def __init__(
        self,
        lexicon: dict[str, list[str]],
        *,
        language: str = "es",
        max_pairs: int = 500,
    ) -> None:
        self._lexicon = lexicon
        self.language = language
        self.max_pairs = max_pairs
        self._pair_cache: dict[str, list[MinimalPair]] | None = None

    @classmethod
    def from_lexicon_strings(
        cls,
        lexicon: dict[str, str],
        *,
        language: str = "es",
        max_pairs: int = 500,
    ) -> "MinimalPairGenerator":
        """Construir desde léxico con IPA como string (fonemas separados por espacios).

        Ejemplo::

            lexicon = {"hola": "o l a", "mola": "m o l a"}
            gen = MinimalPairGenerator.from_lexicon_strings(lexicon)
        """
        tokenized = {
            word: tokens.split()
            for word, tokens in lexicon.items()
        }
        return cls(tokenized, language=language, max_pairs=max_pairs)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def find_pairs_for_phoneme(self, phoneme: str) -> list[MinimalPair]:
        """Retorna todos los pares mínimos en los que participa ``phoneme``.

        Solo incluye pares donde *una* de las dos palabras contiene
        el fonema dado en la posición de contraste.
        """
        all_pairs = self._build_all_pairs()
        return [
            p for p in all_pairs
            if p.phoneme1 == phoneme or p.phoneme2 == phoneme
        ]

    def find_pairs_for_contrast(
        self,
        phoneme1: str,
        phoneme2: str,
    ) -> list[MinimalPair]:
        """Retorna pares que contrastan exactamente ``phoneme1`` vs ``phoneme2``."""
        all_pairs = self._build_all_pairs()
        return [
            p for p in all_pairs
            if (p.phoneme1 == phoneme1 and p.phoneme2 == phoneme2)
            or (p.phoneme1 == phoneme2 and p.phoneme2 == phoneme1)
        ]

    def find_pairs_by_tag(self, tag: str) -> list[MinimalPair]:
        """Retorna pares curados con la etiqueta dada."""
        curated = self.get_curated_pairs()
        return [p for p in curated if tag in p.tags]

    def find_pairs_by_difficulty(self, difficulty: int) -> list[MinimalPair]:
        """Retorna pares curados con el nivel de dificultad dado."""
        curated = self.get_curated_pairs()
        return [p for p in curated if p.difficulty == difficulty]

    def get_curated_pairs(self, language: str | None = None) -> list[MinimalPair]:
        """Retorna la lista curada de pares para el idioma.

        Si el idioma no tiene lista curada, retorna lista vacía.
        """
        lang = language or self.language
        return _CURATED.get(lang, [])

    def iter_pairs(self) -> Iterator[MinimalPair]:
        """Itera sobre todos los pares generados desde el léxico."""
        yield from self._build_all_pairs()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _build_all_pairs(self) -> list[MinimalPair]:
        """Construir todos los pares mínimos desde el léxico (con cache)."""
        if self._pair_cache is not None:
            return self._pair_cache

        pairs: list[MinimalPair] = []
        words = list(self._lexicon.items())

        for i, (w1, t1) in enumerate(words):
            if len(pairs) >= self.max_pairs:
                break
            for w2, t2 in words[i + 1:]:
                if len(pairs) >= self.max_pairs:
                    break
                pair = _check_minimal_pair(w1, t1, w2, t2, language=self.language)
                if pair is not None:
                    pairs.append(pair)

        self._pair_cache = pairs
        logger.debug(
            "MinimalPairGenerator: %d pares generados desde léxico (%d palabras)",
            len(pairs), len(words),
        )
        return pairs


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def _check_minimal_pair(
    word1: str,
    tokens1: list[str],
    word2: str,
    tokens2: list[str],
    *,
    language: str = "es",
) -> Optional[MinimalPair]:
    """Si word1 y word2 difieren en exactamente un fonema, retorna el par.

    Requiere la misma longitud (número de fonemas).
    """
    if len(tokens1) != len(tokens2):
        return None
    diffs = [
        (i, t1, t2)
        for i, (t1, t2) in enumerate(zip(tokens1, tokens2))
        if t1 != t2
    ]
    if len(diffs) != 1:
        return None

    pos, ph1, ph2 = diffs[0]
    return MinimalPair(
        word1=word1,
        ipa1=" ".join(tokens1),
        word2=word2,
        ipa2=" ".join(tokens2),
        phoneme1=ph1,
        phoneme2=ph2,
        position=pos,
        language=language,
    )


def get_curated_pairs(language: str = "es-mx") -> list[MinimalPair]:
    """Acceso directo a los pares mínimos curados para un idioma.

    Ejemplo::

        pairs = get_curated_pairs("es-mx")
        for pair in pairs:
            print(pair.contrast_label(), pair.word1, "vs", pair.word2)
    """
    return _CURATED.get(language, _CURATED.get(language.split("-")[0], []))


__all__ = [
    "MinimalPair",
    "MinimalPairGenerator",
    "get_curated_pairs",
]
