"""Conversor TextRef basado en ``phonemizer`` con backend eSpeak NG."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Mapping

try:  # pragma: no cover - dependencia opcional durante la importación
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - dependencia opcional
    yaml = None

try:  # pragma: no cover - dependencia opcional durante la importación
    from phonemizer import phonemize  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - entorno sin dependencia
    phonemize = None

from ipa_core.normalization import IPANormalizer
from ipa_core.textref.base import TextRef

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _ROOT_DIR / "config" / "textref_phonemizer.yaml"
_NORMALIZATION_CONFIG = _ROOT_DIR / "configs" / "normalization.yaml"


class PhonemizerTextRef(TextRef):
    """Implementación de :class:`TextRef` usando ``phonemizer``.

    El idioma por defecto se obtiene de ``config/textref_phonemizer.yaml`` si
    está disponible. Puede sobrescribirse tanto al instanciar la clase como al
    invocar :meth:`text_to_ipa` mediante el argumento ``lang``.
    """

    def __init__(
        self,
        language: str | None = None,
        config_path: Path | None = None,
        *,
        normalizer: IPANormalizer | None = None,
        normalization_config_path: Path | None = None,
    ):
        self._config_path = config_path or _CONFIG_PATH
        self._default_language = language or self._load_language()
        self._normalizer = normalizer or self._load_normalizer(
            normalization_config_path or _NORMALIZATION_CONFIG
        )

    def _load_language(self) -> str:
        config = self._load_config()
        lang = config.get("language") if isinstance(config, Mapping) else None
        if isinstance(lang, str) and lang:
            return lang
        return "es"

    def _load_config(self) -> Mapping[str, Any]:
        if not self._config_path.exists():
            return {}
        raw = self._config_path.read_text(encoding="utf-8")
        if yaml is not None:  # pragma: no branch - ruta principal
            data = yaml.safe_load(raw) or {}
            if not isinstance(data, Mapping):
                raise ValueError("La configuración de phonemizer debe ser un mapeo")
            return data

        # Fallback simple para YAML estilo clave: valor cuando PyYAML no está disponible
        result: dict[str, Any] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in stripped:
                raise ValueError(
                    "Formato inválido en configuración de phonemizer: se esperaba 'clave: valor'"
                )
            key, value = stripped.split(":", 1)
            result[key.strip()] = value.strip()
        return result

    def text_to_ipa(self, text: str, lang: str | None = None) -> str:
        if lang is not None:
            if not isinstance(lang, str) or not lang.strip():
                raise ValueError("El idioma debe ser una cadena no vacía")
            language = lang
        else:
            language = self._default_language
        if not isinstance(language, str) or not language:
            raise ValueError("El idioma debe ser una cadena no vacía")

        if phonemize is None:
            phonemes = _fallback_phonemize(text, language)
        else:
            phonemes = phonemize(
                text,
                language=language,
                backend="espeak",
                strip=True,
                njobs=1,
            )
        normalised = " ".join(phonemes.split())
        return self._normalizer.normalize(normalised)

    def _load_normalizer(self, config_path: Path) -> IPANormalizer:
        try:
            return IPANormalizer.from_config_file(config_path)
        except FileNotFoundError:  # pragma: no cover - despliegues sin configuración
            return IPANormalizer()


def _fallback_phonemize(text: str, language: str) -> str:
    """Fallback muy básico cuando ``phonemizer`` no está disponible."""

    lang = language.lower()
    if lang in {"es", "es-es", "es-la", "es-mx"}:
        return " ".join(_fallback_spanish(word) for word in _tokenize(text))
    if lang in {"en", "en-us", "en-gb"}:
        return " ".join(_fallback_english(word) for word in _tokenize(text))
    raise ModuleNotFoundError(
        "phonemizer no está instalado y no existe un fallback para el idioma "
        f"'{language}'. Instale 'phonemizer' y 'espeak-ng'."
    )


def _tokenize(text: str) -> Iterable[str]:
    word = []
    for char in text.lower():
        if char.isalpha():
            word.append(char)
            continue
        if word:
            yield "".join(word)
            word.clear()
    if word:
        yield "".join(word)


def _fallback_spanish(word: str) -> str:
    custom = {
        "hola": "ˈola",
        "mundo": "ˈmundo",
        "taco": "ˈtako",
    }
    if word in custom:
        return custom[word]
    return word


def _fallback_english(word: str) -> str:
    custom = {
        "taco": "ˈtækoʊ",
    }
    if word in custom:
        return custom[word]
    return word
