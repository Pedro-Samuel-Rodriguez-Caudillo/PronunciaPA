"""TextRef para inglés basado en el CMU Pronouncing Dictionary.

Convierte texto en inglés a tokens IPA usando el CMU Dict (ARPAbet → IPA).
Requiere ``nltk`` con el corpus ``cmudict`` descargado::

    pip install nltk
    python -c "import nltk; nltk.download('cmudict')"

Para palabras fuera del diccionario (OOV) usa eSpeak como fallback
si está disponible; de lo contrario, retorna los grafemas.

Uso
---
    from ipa_core.textref.cmu_dict import CMUDictTextRef
    ref = CMUDictTextRef()
    await ref.setup()
    result = await ref.to_ipa("hello world", lang="en")
    # {"tokens": ["h", "ɛ", "l", "oʊ", "w", "ɝ", "l", "d"], ...}
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from ipa_core.types import Token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ARPAbet → IPA mapping
# Fuente: CMU Pronouncing Dictionary + convenciones IPA estándar GA (inglés
# americano general).  Los dígitos de acento (0/1/2) se eliminan antes de
# la búsqueda — el mapping trabaja siempre sobre la forma sin dígito.
# ---------------------------------------------------------------------------
_ARPABET_TO_IPA: Dict[str, str] = {
    # Vocales
    "AA": "ɑ",   # father
    "AE": "æ",   # cat
    "AH": "ʌ",   # cut (forma tónica); AH0 → ə se maneja abajo
    "AO": "ɔ",   # law
    "AW": "aʊ",  # how
    "AY": "aɪ",  # buy
    "EH": "ɛ",   # bed
    "ER": "ɝ",   # bird (tónico)
    "EY": "eɪ",  # say
    "IH": "ɪ",   # bit
    "IY": "i",   # beet
    "OW": "oʊ",  # go
    "OY": "ɔɪ",  # boy
    "UH": "ʊ",   # book
    "UW": "u",   # boot
    # Consonantes
    "B":  "b",
    "CH": "tʃ",
    "D":  "d",
    "DH": "ð",
    "F":  "f",
    "G":  "ɡ",
    "HH": "h",
    "JH": "dʒ",
    "K":  "k",
    "L":  "l",
    "M":  "m",
    "N":  "n",
    "NG": "ŋ",
    "P":  "p",
    "R":  "ɹ",
    "S":  "s",
    "SH": "ʃ",
    "T":  "t",
    "TH": "θ",
    "V":  "v",
    "W":  "w",
    "Y":  "j",
    "Z":  "z",
    "ZH": "ʒ",
}

# Schwa para vocales átonas (stress = 0)
_SCHWA_PHONES = {"AH0": "ə", "ER0": "ɚ"}


def _arpabet_to_ipa_token(phone: str) -> str:
    """Convertir un fonema ARPAbet (con o sin dígito de stress) a IPA.

    Elimina el dígito de stress (0/1/2) al final si está presente,
    pero antes comprueba si hay un mapeo especial para esa forma exacta
    (ej. AH0 → ə vs AH → ʌ).
    """
    # Schwa especiales: AH0 → ə, ER0 → ɚ
    if phone in _SCHWA_PHONES:
        return _SCHWA_PHONES[phone]
    # Eliminar dígito de stress y buscar en mapping general
    base = re.sub(r"\d$", "", phone)
    return _ARPABET_TO_IPA.get(base, phone.lower())


def _normalize_word(word: str) -> str:
    """Normalizar palabra para búsqueda en CMU Dict."""
    return re.sub(r"[^a-z'-]", "", word.lower())


class CMUDictTextRef:
    """TextRef para inglés usando el CMU Pronouncing Dictionary.

    Parámetros
    ----------
    oov_fallback : str
        Estrategia para palabras fuera de vocabulario:
        - ``"espeak"``   — usar eSpeak-NG como fallback (default)
        - ``"grapheme"`` — retornar grafemas individuales
        - ``"skip"``     — omitir la palabra de la transcripción
    default_lang : str
        Idioma por defecto. Solo ``"en"`` está soportado; para otros
        idiomas retorna resultado vacío y avisa.
    """

    output_type = "ipa"

    def __init__(
        self,
        *,
        oov_fallback: str = "espeak",
        default_lang: str = "en",
    ) -> None:
        self._oov_fallback = oov_fallback
        self._default_lang = default_lang
        self._cmudict: Optional[Dict[str, List[List[str]]]] = None
        self._espeak: Any = None
        self._ready = False

    async def setup(self) -> None:
        """Cargar CMU Dict y preparar fallback."""
        try:
            import nltk
            try:
                from nltk.corpus import cmudict as _cmu
                self._cmudict = _cmu.dict()
            except LookupError:
                logger.info("CMU Dict no encontrado, descargando...")
                nltk.download("cmudict", quiet=True)
                from nltk.corpus import cmudict as _cmu
                self._cmudict = _cmu.dict()
            logger.info("CMU Dict cargado: %d entradas", len(self._cmudict))
        except ImportError:
            logger.warning(
                "nltk no instalado. CMUDictTextRef sin diccionario. "
                "Instala con: pip install nltk && python -c \"import nltk; nltk.download('cmudict')\""
            )
            self._cmudict = {}

        if self._oov_fallback == "espeak":
            try:
                from ipa_core.textref.espeak import EspeakTextRef
                self._espeak = EspeakTextRef(default_lang="en")
                await self._espeak.setup()
            except Exception as exc:
                logger.warning("eSpeak fallback no disponible: %s", exc)
                self._espeak = None

        self._ready = True

    async def teardown(self) -> None:
        if self._espeak is not None:
            await self._espeak.teardown()
        self._ready = False

    async def to_ipa(
        self,
        text: str,
        *,
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convertir texto en inglés a tokens IPA.

        Parámetros
        ----------
        text : str
            Texto en inglés (puede ser varias palabras).
        lang : str, optional
            Si no es inglés (``"en"``), registra advertencia y delega al fallback.

        Retorna
        -------
        dict con ``{"tokens": [...], "meta": {...}}``
        """
        effective_lang = lang or self._default_lang

        # CMU Dict es solo para inglés
        if effective_lang not in ("en", "en-us", "en-gb", "en-au"):
            logger.warning(
                "CMUDictTextRef solo soporta inglés; lang='%s' recibido.", effective_lang
            )
            if self._espeak is not None:
                return await self._espeak.to_ipa(text, lang=lang)
            return {"tokens": list(text), "meta": {"method": "grapheme_fallback"}}

        if not self._ready:
            from ipa_core.errors import NotReadyError
            raise NotReadyError("CMUDictTextRef no inicializado. Llama setup() primero.")

        words = text.strip().split()
        all_tokens: List[Token] = []
        oov_words: List[str] = []
        meta_words: List[Dict[str, Any]] = []

        for raw_word in words:
            normalized = _normalize_word(raw_word)
            if not normalized:
                continue

            if self._cmudict and normalized in self._cmudict:
                # Usar primera pronunciación del diccionario
                phones = self._cmudict[normalized][0]
                tokens = [_arpabet_to_ipa_token(p) for p in phones]
                all_tokens.extend(tokens)
                meta_words.append({"word": raw_word, "source": "cmudict", "tokens": tokens})
            else:
                oov_words.append(raw_word)
                fallback_tokens = await self._resolve_oov(raw_word, lang=effective_lang)
                all_tokens.extend(fallback_tokens)
                meta_words.append({"word": raw_word, "source": self._oov_fallback, "tokens": fallback_tokens})

        return {
            "tokens": all_tokens,
            "meta": {
                "method": "cmudict",
                "oov_words": oov_words,
                "oov_count": len(oov_words),
                "words": meta_words,
            },
        }

    async def _resolve_oov(self, word: str, *, lang: str) -> List[Token]:
        """Resolver palabra fuera de vocabulario según la estrategia configurada."""
        if self._oov_fallback == "espeak" and self._espeak is not None:
            try:
                result = await self._espeak.to_ipa(word, lang=lang)
                return result.get("tokens", [])
            except Exception as exc:
                logger.warning("eSpeak OOV fallback falló para '%s': %s", word, exc)

        if self._oov_fallback == "skip":
            return []

        # grapheme fallback
        return list(word.lower())


__all__ = ["CMUDictTextRef"]
