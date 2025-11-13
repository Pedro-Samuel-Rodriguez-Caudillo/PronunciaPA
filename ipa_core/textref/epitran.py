"""Proveedor TextRef basado en Epitran."""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Dict, Optional

from ipa_core.errors import NotReadyError
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import Token

try:  # Carga diferida: solo se necesita cuando se usa este proveedor.
    import epitran
except ImportError:  # pragma: no cover
    epitran = None  # type: ignore[assignment]


LangFactory = Callable[[str], object]


class EpitranTextRef(TextRefProvider):
    """Convierte texto a IPA usando modelos de Epitran."""

    _LANG_CODES: Dict[str, str] = {
        "es": "spa-Latn",
        "en": "eng-Latn",
        "fr": "fra-Latn",
        "pt": "por-Latn",
    }

    def __init__(
        self,
        *,
        default_lang: str = "es",
        factory: Optional[LangFactory] = None,
    ) -> None:
        self._default_lang = default_lang
        self._factory = factory or self._load_model

    def _load_model(self, code: str):
        if epitran is None:
            raise NotReadyError("Epitran no instalado. Ejecuta `pip install ipa-core[speech]`.")
        return epitran.Epitran(code)

    @lru_cache(maxsize=8)
    def _get_model(self, code: str):
        return self._factory(code)

    def _resolve_code(self, lang: Optional[str]) -> str:
        if not lang:
            lang = self._default_lang
        return self._LANG_CODES.get(lang, lang)

    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]:  # noqa: D401
        code = self._resolve_code(lang)
        model = self._get_model(code)
        tokens = self._transliterate(model, text)
        return [token for token in tokens if token.strip()]

    @staticmethod
    def _transliterate(model, text: str) -> list[str]:
        if hasattr(model, "trans_list"):
            try:
                return list(model.trans_list(text))
            except AttributeError:  # pragma: no cover - fallback dinámico
                pass
        transliterated = model.transliterate(text)  # pragma: no cover - fallback
        return [ch for ch in transliterated if not ch.isspace()]


__all__ = ["EpitranTextRef"]
