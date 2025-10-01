"""Kernel orchestration for the IPA core pipeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None

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

    def run(self, input_dir: str | Path, dry_run: bool = False) -> dict[str, Any]:
        """Execute the (stub) pipeline.

        Returns a dictionary with diagnostic information so callers can
        inspect which plugins were activated. The actual phonetic processing
        will be implemented in future iterations.
        """

        input_path = Path(input_dir)
        if not input_path.exists():
            logger.warning(
                "El directorio de entrada %s no existe; se continúa con lista vacía",
                input_path,
            )
            files: list[str] = []
        else:
            files = sorted(p.name for p in input_path.iterdir() if p.is_file())

        result = {
            "input_dir": str(input_path),
            "files": files,
            "plugins": self.config.to_mapping(),
            "dry_run": dry_run,
        }

        if dry_run:
            logger.info("Ejecución en modo dry-run; no se procesa audio")
            return result

        logger.info(
            "Kernel stub ejecutado con %d archivo(s) utilizando plugins %s",
            len(files),
            result["plugins"],
        )
        return result


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
