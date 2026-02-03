"""Proveedor TextRef basado en Epitran."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from ipa_core.errors import NotReadyError
from ipa_core.plugins.base import BasePlugin
from ipa_core.textref.tokenize import tokenize_ipa
from ipa_core.types import TextRefResult

if TYPE_CHECKING:
    from ipa_core.textref.cache import TextRefCache


try:  # Carga diferida: solo se necesita cuando se usa este proveedor.
    import epitran
except Exception:  # pragma: no cover
    epitran = None  # type: ignore[assignment]


LangFactory = Callable[[str], object]


class EpitranTextRef(BasePlugin):
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
        cache: Optional["TextRefCache"] = None,
    ) -> None:
        self._default_lang = default_lang
        self._factory = factory or self._load_model
        self._cache = cache

    def _load_model(self, code: str) -> Any:
        if epitran is None:
            raise NotReadyError("Epitran no instalado. Ejecuta `pip install ipa-core[speech]`.")
        return epitran.Epitran(code)

    @lru_cache(maxsize=8)
    def _get_model(self, code: str) -> Any:
        return self._factory(code)

    def _resolve_code(self, lang: Optional[str]) -> str:
        if not lang:
            lang = self._default_lang
        return self._LANG_CODES.get(lang, lang)

    async def to_ipa(self, text: str, *, lang: Optional[str] = None, **kw: Any) -> TextRefResult:  # noqa: D401
        """Convertir texto de forma asíncrona."""
        cleaned = text.strip()
        if not cleaned:
            return {"tokens": [], "meta": {"empty": True}}
        
        resolved_lang = lang or self._default_lang
        
        # Usar cache si está disponible
        if self._cache is not None:
            return await self._cache.get_or_compute(
                cleaned, resolved_lang, "epitran",
                lambda: self._compute_ipa(cleaned, resolved_lang)
            )
        
        return await self._compute_ipa(cleaned, resolved_lang)
    
    async def _compute_ipa(self, text: str, lang: str) -> TextRefResult:
        """Ejecutar Epitran para obtener transcripción IPA."""
        code = self._resolve_code(lang)
        model = self._get_model(code)
        tokens = self._transliterate(model, text)
        if isinstance(tokens, str):
            clean_tokens = tokenize_ipa(tokens)
        else:
            clean_tokens = [token for token in tokens if token.strip()]
        return {"tokens": clean_tokens, "meta": {"method": "epitran", "code": code}}

    @staticmethod
    def _transliterate(model: Any, text: str) -> list[str] | str:
        if hasattr(model, "trans_list"):
            try:
                return list(model.trans_list(text))
            except AttributeError:  # pragma: no cover - fallback dinámico
                pass
        transliterated = model.transliterate(text)  # pragma: no cover - fallback
        return transliterated


__all__ = ["EpitranTextRef"]

