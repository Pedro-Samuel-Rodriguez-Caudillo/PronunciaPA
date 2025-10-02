"""Kernel orchestration for the IPA core pipeline."""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None

from ipa_core.compare.base import CompareResult, PhonemeStats
from ipa_core.plugins import PLUGIN_GROUPS, load_plugin

__all__ = ["Kernel", "KernelConfig"]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class KernelConfig:
    """Configuration data class for plugin selection.

    Parameters
    ----------
    asr_backend:
        Name of the ASR backend plugin (``ipa_core.backends.asr`` group).
    textref:
        Name of the text-to-IPA plugin (``ipa_core.plugins.textref`` group).
    comparator:
        Name of the comparator plugin (``ipa_core.plugins.compare`` group).
    preprocessor:
        Optional preprocessor plugin name (``ipa_core.plugins.preprocess`` group).
    """

    asr_backend: str = "null"
    textref: str = "noop"
    comparator: str = "noop"
    preprocessor: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "KernelConfig":
        """Create an instance from a dictionary-like object.

        The expected structure is either a flat mapping with the fields of
        :class:`KernelConfig` or a mapping containing a ``plugins`` section.
        Any missing values are filled with the dataclass defaults.
        """

        if "plugins" in data:
            plugins_cfg = data.get("plugins") or {}
            if not isinstance(plugins_cfg, Mapping):
                raise ValueError("La sección 'plugins' debe ser un mapeo")
        else:
            plugins_cfg = data

        kwargs: dict[str, Any] = {}
        for field in ("asr_backend", "textref", "comparator", "preprocessor"):
            if field in plugins_cfg and plugins_cfg[field] is not None:
                kwargs[field] = plugins_cfg[field]

        return cls(**kwargs)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "KernelConfig":
        """Load configuration from a YAML file."""

        cfg_path = Path(path)
        raw = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""
        payload = _load_yaml(raw) if raw else {}
        if payload is None:
            payload = {}
        if not isinstance(payload, Mapping):
            raise ValueError("El archivo de configuración debe contener un mapeo")
        return cls.from_mapping(payload)

    def to_mapping(self) -> dict[str, Any]:
        """Return a serialisable representation of the configuration."""

        return {
            "asr_backend": self.asr_backend,
            "textref": self.textref,
            "comparator": self.comparator,
            "preprocessor": self.preprocessor,
        }


@dataclass(slots=True)
class _Sample:
    index: int
    audio_original: str
    audio_path: Path
    text: str
    lang: str | None


class Kernel:
    """Instantiate and orchestrate the registered plugins."""

    def __init__(self, cfg: KernelConfig):
        self.config = cfg
        self.asr = self._instantiate("asr", cfg.asr_backend)
        self.textref = self._instantiate("textref", cfg.textref)
        self.comparator = self._instantiate("comparator", cfg.comparator)
        self.preprocessor = (
            self._instantiate("preprocessor", cfg.preprocessor)
            if cfg.preprocessor
            else None
        )

    @staticmethod
    def _resolve_group(group_key: str) -> str:
        try:
            return PLUGIN_GROUPS[group_key].entrypoint_group
        except KeyError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"Grupo de plugins desconocido: {group_key}") from exc

    def _instantiate(self, group_key: str, plugin_name: str | None):
        if not plugin_name:
            return None
        group = self._resolve_group(group_key)
        plugin_cls = load_plugin(group, plugin_name)
        return plugin_cls()

    def run(self, metadata_path: str | Path) -> dict[str, Any]:
        """Execute the IPA pipeline over the provided metadata file."""

        if self.asr is None or self.textref is None or self.comparator is None:
            raise RuntimeError(
                "Se requieren plugins configurados para ASR, TextRef y Comparator"
            )

        dataset = _load_metadata(metadata_path)
        logger.info("Procesando %d registros", len(dataset))

        details: list[dict[str, Any]] = []
        processed = 0
        total_tokens = 0
        total_errors = 0
        per_class_acc: dict[str, PhonemeStats] = {}

        for sample in dataset:
            detail: dict[str, Any] = {
                "index": sample.index,
                "audio_path": sample.audio_original,
                "text": sample.text,
                "lang": sample.lang,
            }

            try:
                ref_ipa = self.textref.text_to_ipa(sample.text, sample.lang)
                hyp_ipa = self.asr.transcribe_ipa(str(sample.audio_path))
                compare_result = self.comparator.compare(ref_ipa, hyp_ipa)
            except Exception as exc:  # pragma: no cover - defensive branch
                logger.exception(
                    "Error procesando registro %s (%s)",
                    sample.index,
                    sample.audio_original,
                )
                detail["error"] = str(exc)
                details.append(detail)
                continue

            processed += 1
            total_tokens += compare_result.total_ref_tokens
            total_errors += (
                compare_result.substitutions
                + compare_result.insertions
                + compare_result.deletions
            )
            _merge_per_class(per_class_acc, compare_result)

            detail.update(
                {
                    "ref_ipa": ref_ipa,
                    "hyp_ipa": hyp_ipa,
                    "per": compare_result.per,
                    "matches": compare_result.matches,
                    "substitutions": compare_result.substitutions,
                    "insertions": compare_result.insertions,
                    "deletions": compare_result.deletions,
                    "total_ref_tokens": compare_result.total_ref_tokens,
                    "ops": _serialise_ops(compare_result.ops),
                }
            )
            details.append(detail)

        per_global = 0.0 if total_tokens == 0 else total_errors / total_tokens

        return {
            "config": self.config.to_mapping(),
            "metadata": {
                "path": str(Path(metadata_path).resolve()),
                "total_items": len(dataset),
            },
            "summary": {
                "procesados": processed,
                "con_error": len(dataset) - processed,
                "total_ref_tokens": total_tokens,
                "total_errores": total_errors,
            },
            "per_global": per_global,
            "per_por_clase": _serialise_per_class(per_class_acc),
            "detalles": details,
        }


def _coerce_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"", "null", "none", "~"}:
        return None
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _load_yaml(raw: str) -> Mapping[str, Any] | None:
    if yaml is not None:
        return yaml.safe_load(raw)

    result: dict[str, Any] = {}
    stack: list[dict[str, Any]] = [result]
    indents = [0]
    last_keys = [None]

    lines = raw.splitlines()
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError("Indentación inválida en YAML (se esperaban múltiplos de 2 espacios)")

        while indent < indents[-1]:
            stack.pop()
            indents.pop()
            last_keys.pop()

        if indent > indents[-1]:
            if indent != indents[-1] + 2:
                raise ValueError("Incremento de indentación inválido en YAML simplificado")
            parent = stack[-1]
            pending_key = last_keys[-1]
            if pending_key is None:
                raise ValueError("No hay clave padre para anidar el bloque")
            new_dict: dict[str, Any] = {}
            parent[pending_key] = new_dict
            stack.append(new_dict)
            indents.append(indent)
            last_keys.append(None)

        current = stack[-1]
        key, _, remainder = line.strip().partition(":")
        key = key.strip()
        remainder = remainder.strip()

        if not remainder:
            current[key] = None
            last_keys[-1] = key
            continue

        current[key] = _coerce_scalar(remainder)
        last_keys[-1] = key

    return result


def _load_metadata(path: str | Path) -> list[_Sample]:
    metadata_path = Path(path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de metadata: {path}")

    with metadata_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("El archivo de metadata debe tener encabezados")

        required = {"audio_path", "text"}
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(
                "Faltan columnas obligatorias en metadata: " + ", ".join(sorted(missing))
            )

        rows: list[_Sample] = []
        base_dir = metadata_path.parent
        for idx, row in enumerate(reader, start=1):
            audio_raw = (row.get("audio_path") or "").strip()
            text = (row.get("text") or "").strip()
            lang_raw = (row.get("lang") or "").strip() or None

            if not audio_raw:
                raise ValueError(f"Fila {idx}: 'audio_path' no puede estar vacío")
            if not text:
                raise ValueError(f"Fila {idx}: 'text' no puede estar vacío")

            rows.append(
                _Sample(
                    index=idx,
                    audio_original=audio_raw,
                    audio_path=(base_dir / audio_raw).resolve(),
                    text=text,
                    lang=lang_raw,
                )
            )

    return rows


def _merge_per_class(
    accumulator: dict[str, PhonemeStats], compare_result: CompareResult
) -> None:
    for key, stats in compare_result.per_class.items():
        current = accumulator.setdefault(key, PhonemeStats())
        current.matches += stats.matches
        current.substitutions += stats.substitutions
        current.insertions += stats.insertions
        current.deletions += stats.deletions


def _serialise_ops(ops: Iterable[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {
            "op": op,
            "ref": ref,
            "hyp": hyp,
        }
        for op, ref, hyp in ops
    ]


def _serialise_per_class(per_class: Mapping[str, PhonemeStats]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for key in sorted(per_class):
        stats = per_class[key]
        result[key] = {
            "matches": stats.matches,
            "substitutions": stats.substitutions,
            "insertions": stats.insertions,
            "deletions": stats.deletions,
            "errors": stats.errors,
        }
    return result
