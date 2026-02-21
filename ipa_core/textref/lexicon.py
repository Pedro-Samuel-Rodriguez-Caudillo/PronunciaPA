"""Backend TextRef basado en léxico del LanguagePack + fallback a eSpeak.

Estrategia de búsqueda
----------------------
1. Normalizar el texto (minúsculas, sin puntuación).
2. Para cada palabra, buscar en el léxico precargado del pack (``Dict[str, str]``).
3. Si la palabra no está en el léxico (OOV), delegar a eSpeak como fallback.
4. Combinar los tokens de todas las palabras en el resultado final.

Ventajas
--------
- Funciona 100% offline para el vocabulario curado del pack.
- Pronunciaciones del léxico son consistentes (revisadas por expertos / G2P validado).
- El fallback a eSpeak garantiza cobertura total del idioma.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional, TYPE_CHECKING

from ipa_core.plugins.base import BasePlugin
from ipa_core.textref.tokenize import tokenize_ipa
from ipa_core.types import TextRefResult

if TYPE_CHECKING:
    from ipa_core.textref.cache import TextRefCache
    from ipa_core.textref.espeak import EspeakTextRef


# ---------------------------------------------------------------------------
# Utilidades de normalización de texto
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s'-]", re.UNICODE)


def _normalize_word(word: str) -> str:
    """Normalizar una palabra para la búsqueda en el léxico.

    Aplica: NFD → minúsculas → elimina puntuación → strip.
    Se conservan apóstrofes y guiones por su valor fonético.
    """
    nfd = unicodedata.normalize("NFD", word)
    lower = nfd.lower()
    clean = _PUNCT_RE.sub("", lower).strip()
    return clean


def _split_words(text: str) -> list[str]:
    """Dividir texto en palabras, conservando orden."""
    return text.split()


# ---------------------------------------------------------------------------
# Backend principal
# ---------------------------------------------------------------------------

class LexiconTextRef(BasePlugin):
    """Proveedor TextRef que primero busca en el léxico del pack.

    Parámetros
    ----------
    lexicon:
        Diccionario ``{palabra: transcripción_IPA}`` precargado del pack.
        Las claves deben estar ya normalizadas (minúsculas, sin puntuación).
    espeak_fallback:
        Instancia de :class:`~ipa_core.textref.espeak.EspeakTextRef` para
        cubrir las palabras que no están en el léxico.  Si es ``None``, las
        palabras OOV se omiten del resultado (no recomendado en producción).
    default_lang:
        Código de idioma por defecto.
    cache:
        Caché compartida opcional.
    """

    def __init__(
        self,
        *,
        lexicon: Optional[dict[str, str]] = None,
        espeak_fallback: Optional["EspeakTextRef"] = None,
        default_lang: str = "es",
        cache: Optional["TextRefCache"] = None,
    ) -> None:
        self._lexicon: dict[str, str] = lexicon or {}
        self._espeak = espeak_fallback
        self._default_lang = default_lang
        self._cache = cache

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    async def setup(self) -> None:
        if self._espeak is not None:
            await self._espeak.setup()

    async def teardown(self) -> None:
        if self._espeak is not None:
            await self._espeak.teardown()

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    async def to_ipa(
        self,
        text: str,
        *,
        lang: Optional[str] = None,
        **kw: Any,
    ) -> TextRefResult:
        """Convertir texto a IPA consultando el léxico y eSpeak como fallback."""
        cleaned = text.strip()
        if not cleaned:
            return {"tokens": [], "meta": {"empty": True}}

        resolved_lang = lang or self._default_lang

        if self._cache is not None:
            return await self._cache.get_or_compute(
                cleaned,
                resolved_lang,
                "lexicon",
                lambda: self._compute_ipa(cleaned, resolved_lang),
            )

        return await self._compute_ipa(cleaned, resolved_lang)

    # ------------------------------------------------------------------
    # Implementación interna
    # ------------------------------------------------------------------

    async def _compute_ipa(self, text: str, lang: str) -> TextRefResult:
        """Resolver IPA palabra por palabra."""
        words = _split_words(text)
        all_tokens: list[str] = []
        sources: list[str] = []  # para trazabilidad

        oov_words: list[tuple[int, str]] = []  # (índice, palabra_original)
        word_tokens: dict[int, list[str]] = {}

        # Primera pasada: buscar en léxico
        for idx, word in enumerate(words):
            key = _normalize_word(word)
            if key in self._lexicon:
                ipa_str = self._lexicon[key]
                tokens = tokenize_ipa(ipa_str)
                word_tokens[idx] = tokens
                sources.append("lexicon")
            else:
                oov_words.append((idx, word))

        # Segunda pasada: batch fallback a eSpeak para OOV
        if oov_words:
            if self._espeak is not None:
                # Enviar todas las palabras OOV en una sola llamada para eficiencia
                oov_text = " ".join(w for _, w in oov_words)
                try:
                    result = await self._espeak.to_ipa(oov_text, lang=lang)
                    oov_tokens = result.get("tokens", [])
                    # Distribuir tokens entre palabras OOV de forma proporcional
                    # (eSpeak no devuelve límites de palabra, así que asignamos en bloque)
                    for idx, _ in oov_words:
                        word_tokens[idx] = []
                    # Asignar todos los tokens OOV al primer slot OOV como bloque
                    if oov_words:
                        word_tokens[oov_words[0][0]] = oov_tokens
                    for _, _ in oov_words[1:]:
                        pass  # slots vacíos (tokens ya incluidos en bloque)
                    sources.extend(["espeak_fallback"] * len(oov_words))
                except Exception:  # noqa: BLE001
                    # eSpeak no disponible: marcar como vacíos
                    for idx, _ in oov_words:
                        word_tokens[idx] = []
                    sources.extend(["oov_skipped"] * len(oov_words))
            else:
                # Sin fallback: palabras OOV → sin tokens
                for idx, _ in oov_words:
                    word_tokens[idx] = []
                sources.extend(["oov_skipped"] * len(oov_words))

        # Construir secuencia final respetando orden de palabras
        for idx in range(len(words)):
            all_tokens.extend(word_tokens.get(idx, []))

        return {
            "tokens": all_tokens,
            "meta": {
                "method": "lexicon",
                "lang": lang,
                "total_words": len(words),
                "lexicon_hits": len(words) - len(oov_words),
                "oov_count": len(oov_words),
                "sources": sources,
                "has_espeak_fallback": self._espeak is not None,
            },
        }

    # ------------------------------------------------------------------
    # Helpers para inspección
    # ------------------------------------------------------------------

    def lookup(self, word: str) -> Optional[str]:
        """Buscar una palabra en el léxico (retorna IPA o None)."""
        return self._lexicon.get(_normalize_word(word))

    def contains(self, word: str) -> bool:
        """Verificar si una palabra está en el léxico."""
        return _normalize_word(word) in self._lexicon

    @property
    def lexicon_size(self) -> int:
        """Número de entradas en el léxico."""
        return len(self._lexicon)

    @classmethod
    def from_pack_dict(
        cls,
        pack_lexicon: dict[str, str],
        *,
        espeak_fallback: Optional["EspeakTextRef"] = None,
        default_lang: str = "es",
        cache: Optional["TextRefCache"] = None,
    ) -> "LexiconTextRef":
        """Construir desde el dict léxico del LanguagePack.

        Normaliza las claves del dict antes de almacenarlas.
        """
        normalized = {_normalize_word(k): v for k, v in pack_lexicon.items()}
        return cls(
            lexicon=normalized,
            espeak_fallback=espeak_fallback,
            default_lang=default_lang,
            cache=cache,
        )


__all__ = ["LexiconTextRef", "normalize_word"]


def normalize_word(word: str) -> str:
    """Alias público de :func:`_normalize_word`."""
    return _normalize_word(word)
