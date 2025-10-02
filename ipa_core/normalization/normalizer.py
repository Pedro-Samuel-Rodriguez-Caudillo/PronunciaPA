"""Normalizador configurable para cadenas IPA."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence
import json
import unicodedata

try:  # pragma: no cover - dependencia opcional
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - entorno mínimo
    yaml = None


@dataclass(frozen=True)
class NormalizationConfig:
    """Configuración inmutable para :class:`IPANormalizer`."""

    replacements: tuple[tuple[str, str], ...] = ()
    disallowed_characters: frozenset[str] = frozenset()
    allowed_characters: frozenset[str] | None = None
    collapse_whitespace: bool = True

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> "NormalizationConfig":
        replacements = _as_str_pairs(mapping.get("replacements"))
        # Ordenamos por longitud descendente para evitar sustituciones parciales.
        replacements = tuple(sorted(replacements, key=lambda item: len(item[0]), reverse=True))

        disallowed = frozenset(_as_str_sequence(mapping.get("disallowed_characters")))
        allowed_values = mapping.get("allowed_characters")
        allowed: frozenset[str] | None
        if allowed_values is None:
            allowed = None
        else:
            allowed = frozenset(_as_str_sequence(allowed_values))

        collapse_whitespace = bool(mapping.get("collapse_whitespace", True))

        return cls(
            replacements=replacements,
            disallowed_characters=disallowed,
            allowed_characters=allowed,
            collapse_whitespace=collapse_whitespace,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "NormalizationConfig":
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de configuración: {path}")
        raw = file_path.read_text(encoding="utf-8")
        data = _load_mapping(raw)
        if not isinstance(data, Mapping):
            raise ValueError("La configuración de normalización debe ser un mapeo")
        return cls.from_mapping(data)


class IPANormalizer:
    """Aplica normalizaciones configurables a transcripciones IPA."""

    def __init__(self, config: NormalizationConfig | None = None):
        self._config = config or NormalizationConfig()

    @classmethod
    def from_config_file(cls, path: str | Path) -> "IPANormalizer":
        return cls(NormalizationConfig.from_file(path))

    def normalize(self, text: str) -> str:
        """Normaliza una cadena IPA aplicando reglas predefinidas."""

        normalised = unicodedata.normalize("NFC", text)
        normalised = self._apply_replacements(normalised)
        normalised = self._filter_characters(normalised)
        if self._config.collapse_whitespace:
            normalised = " ".join(normalised.split())
        return unicodedata.normalize("NFC", normalised)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _apply_replacements(self, text: str) -> str:
        for source, target in self._config.replacements:
            text = text.replace(source, target)
        return text

    def _filter_characters(self, text: str) -> str:
        disallowed = self._config.disallowed_characters
        allowed = self._config.allowed_characters
        if not disallowed and allowed is None:
            return text

        result_chars: list[str] = []
        for char in text:
            if char.isspace():
                result_chars.append(char)
                continue
            if char in disallowed:
                continue
            if allowed is not None and char not in allowed:
                continue
            result_chars.append(char)
        return "".join(result_chars)


# ----------------------------------------------------------------------
# Utilidades de parsing
# ----------------------------------------------------------------------

def _load_mapping(raw: str) -> Mapping[str, object]:
    if yaml is not None:  # pragma: no branch - ruta principal
        data = yaml.safe_load(raw)
        if data is None:
            return {}
        if isinstance(data, Mapping):
            return data
        raise ValueError("La configuración YAML debe ser un mapeo de nivel superior")

    # Fallback: intentamos interpretar el archivo como JSON válido.
    data = json.loads(raw or "{}")
    if isinstance(data, Mapping):
        return data
    raise ValueError("La configuración de normalización debe ser un mapeo")


def _as_str_pairs(value: object | None) -> Sequence[tuple[str, str]]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        pairs: list[tuple[str, str]] = []
        for key, val in value.items():
            if not isinstance(key, str) or not isinstance(val, str):
                raise TypeError("Las sustituciones deben ser cadenas")
            pairs.append((key, val))
        return tuple(pairs)
    raise TypeError("'replacements' debe ser un mapeo de cadenas")


def _as_str_sequence(value: object | None) -> Iterable[str]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        items: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("Los valores deben ser cadenas")
            items.append(item)
        return tuple(items)
    raise TypeError("Se esperaba una secuencia de cadenas")
