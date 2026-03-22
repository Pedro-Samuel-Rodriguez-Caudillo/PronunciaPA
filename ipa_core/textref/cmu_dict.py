"""TextRef para inglés basado en el CMU Pronouncing Dictionary.

Convierte texto en inglés a tokens IPA usando el CMU Dict (ARPAbet → IPA).
Requiere ``nltk`` con el corpus ``cmudict`` descargado::

    pip install nltk
    python -c "import nltk; nltk.download('cmudict')"

Para palabras fuera del diccionario (OOV) usa eSpeak como fallback
si está disponible; de lo contrario, retorna los grafemas.

Cache
-----
Los resultados se cachean por (texto, lang) en un LRU interno de 5 000
entradas para evitar búsquedas repetidas en el diccionario.

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

from ipa_core.textref.cache import TextRefCache
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

# Nombre canónico del proveedor para el cache (debe ser único)
_PROVIDER_NAME = "cmudict"


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
    cache_size : int
        Número máximo de entradas en el cache LRU. Default: 5000.
    """

    output_type = "ipa"

    def __init__(
        self,
        *,
        oov_fallback: str = "espeak",
        default_lang: str = "en",
        cache_size: int = 5000,
    ) -> None:
        self._oov_fallback = oov_fallback
        self._default_lang = default_lang
        self._cmudict: Optional[Dict[str, List[List[str]]]] = None
        self._espeak: Any = None
        self._ready = False
        self._cache: TextRefCache = TextRefCache(max_size=cache_size)

    async def setup(self) -> None:
        """Cargar CMU Dict y preparar fallback."""
        await self._setup_cmudict()
        await self._setup_oov_fallback()
        self._ready = True

    async def _setup_cmudict(self) -> None:
        try:
            import nltk
            self._cmudict = self._try_load_nltk_cmudict(nltk)
        except ImportError:
            logger.warning("nltk no instalado. CMUDictTextRef sin diccionario.")
            self._cmudict = {}

    def _try_load_nltk_cmudict(self, nltk) -> Dict[str, List[List[str]]]:
        try:
            from nltk.corpus import cmudict as _cmu
            return _cmu.dict()
        except LookupError:
            logger.info("CMU Dict no encontrado, descargando...")
            nltk.download("cmudict", quiet=True)
            from nltk.corpus import cmudict as _cmu
            return _cmu.dict()

    async def _setup_oov_fallback(self) -> None:
        if self._oov_fallback != "espeak":
            return
        try:
            from ipa_core.textref.espeak import EspeakTextRef
            self._espeak = EspeakTextRef(default_lang="en")
            await self._espeak.setup()
        except Exception as exc:
            logger.warning("eSpeak fallback no disponible: %s", exc)
            self._espeak = None

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
        """Convertir texto en inglés a tokens IPA (con cache LRU)."""
        if not self._ready:
            from ipa_core.errors import NotReadyError
            raise NotReadyError("CMUDictTextRef no inicializado.")

        effective_lang = (lang or self._default_lang).lower()

        return await self._cache.get_or_compute(
            text,
            effective_lang,
            _PROVIDER_NAME,
            lambda: self._compute_ipa(text, effective_lang),
        )

    async def _compute_ipa(
        self,
        text: str,
        effective_lang: str,
    ) -> Dict[str, Any]:
        """Computar la transcripción IPA (llamada solo cuando no está en cache)."""
        if not self._is_english(effective_lang):
            return await self._handle_non_english(text, effective_lang)

        all_tokens: List[Token] = []
        oov_words: List[str] = []
        meta_words: List[Dict[str, Any]] = []

        for raw_word in text.strip().split():
            tokens, source = await self._process_word(raw_word, effective_lang, oov_words)
            if tokens is not None:
                all_tokens.extend(tokens)
                meta_words.append({"word": raw_word, "source": source, "tokens": tokens})

        return self._build_compute_response(all_tokens, oov_words, meta_words, effective_lang)

    def _is_english(self, lang: str) -> bool:
        return lang in ("en", "en-us", "en-gb", "en-au", "en-ca", "en-nz", "en-in")

    async def _handle_non_english(self, text: str, lang: str) -> Dict[str, Any]:
        logger.warning("CMUDictTextRef solo soporta inglés; lang='%s'", lang)
        if self._espeak is not None:
            return await self._espeak.to_ipa(text, lang=lang)
        return {"tokens": list(text), "meta": {"method": "grapheme_fallback"}}

    async def _process_word(self, raw_word: str, lang: str, oov_list: List[str]) -> tuple[Optional[List[Token]], str]:
        normalized = _normalize_word(raw_word)
        if not normalized:
            return None, "empty"

        if self._cmudict and normalized in self._cmudict:
            phones = self._cmudict[normalized][0]
            return [_arpabet_to_ipa_token(p) for p in phones], "cmudict"
        
        oov_list.append(raw_word)
        tokens = await self._resolve_oov(raw_word, lang=lang)
        return tokens, self._oov_fallback

    def _build_compute_response(self, tokens: List[Token], oov: List[str], meta: List[dict], lang: str) -> Dict[str, Any]:
        res = {
            "tokens": tokens,
            "meta": {
                "method": "cmudict", "dialect": lang,
                "oov_words": oov, "oov_count": len(oov),
                "words": meta,
            },
        }
        if lang in ("en-gb", "en-au", "en-ca", "en-nz", "en-in"):
            res["meta"]["dialect_note"] = (
                f"Pronunciaciones de palabras conocidas en GA. "
                f"Palabras OOV usan eSpeak voz '{lang}'."
            )
        return res

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

    def cache_stats(self) -> dict:
        """Retornar estadísticas del cache LRU (para diagnóstico)."""
        return self._cache.get_stats().to_dict()


__all__ = ["CMUDictTextRef"]
