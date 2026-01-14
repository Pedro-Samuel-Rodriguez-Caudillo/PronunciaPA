"""Loaders and validators for pack manifests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from ipa_core.packs.schema import LanguagePack, ModelPack, PackResource

DEFAULT_PACKS_DIR = Path(__file__).resolve().parents[2] / "data" / "packs"
_MANIFEST_NAMES = ("pack.yaml", "pack.yml", "pack.json")


def resolve_manifest_path(
    path_or_id: str | Path,
    *,
    base_dir: Path | None = None,
) -> Path:
    base_dir = base_dir or DEFAULT_PACKS_DIR
    candidate = Path(path_or_id)

    if candidate.is_dir():
        return _find_manifest_in_dir(candidate)
    if candidate.is_file():
        return candidate

    if not candidate.is_absolute():
        relative = base_dir / candidate
        if relative.is_file():
            return relative
        if relative.is_dir():
            return _find_manifest_in_dir(relative)

    if candidate.suffix in (".yaml", ".yml", ".json"):
        raise FileNotFoundError(f"Manifest not found: {candidate}")

    pack_dir = base_dir / str(path_or_id)
    if pack_dir.is_dir():
        return _find_manifest_in_dir(pack_dir)

    raise FileNotFoundError(f"Pack manifest not found for: {path_or_id}")


def load_language_pack(
    path_or_id: str | Path,
    *,
    base_dir: Path | None = None,
    validate_files: bool = True,
) -> LanguagePack:
    manifest_path = resolve_manifest_path(path_or_id, base_dir=base_dir)
    data = _load_manifest(manifest_path)
    pack = LanguagePack(**data)
    if validate_files:
        _validate_language_pack_files(pack, manifest_path.parent)
    return pack


def load_model_pack(
    path_or_id: str | Path,
    *,
    base_dir: Path | None = None,
    validate_files: bool = True,
) -> ModelPack:
    manifest_path = resolve_manifest_path(path_or_id, base_dir=base_dir)
    data = _load_manifest(manifest_path)
    pack = ModelPack(**data)
    if validate_files:
        _validate_model_pack_files(pack, manifest_path.parent)
    return pack


def _find_manifest_in_dir(directory: Path) -> Path:
    for name in _MANIFEST_NAMES:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"No manifest found in directory: {directory}")


def _load_manifest(path: Path) -> dict[str, Any]:
    if path.suffix in (".yaml", ".yml"):
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    if path.suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    raise ValueError(f"Unsupported manifest format: {path.suffix}")


def _validate_language_pack_files(pack: LanguagePack, base_dir: Path) -> None:
    required = _collect_language_resources(pack)
    _validate_resources(required, base_dir)


def _validate_model_pack_files(pack: ModelPack, base_dir: Path) -> None:
    required = _collect_model_resources(pack)
    _validate_resources(required, base_dir)


def _validate_resources(
    items: Iterable[tuple[str, PackResource]],
    base_dir: Path,
) -> None:
    missing: list[str] = []
    for label, resource in items:
        if not resource.required:
            continue
        path = resource.resolve_path(base_dir)
        if not path.exists():
            missing.append(f"{label}: {path}")
    if missing:
        joined = "\n".join(f"- {item}" for item in missing)
        raise FileNotFoundError(f"Missing pack resources:\n{joined}")


def _collect_language_resources(pack: LanguagePack) -> list[tuple[str, PackResource]]:
    items: list[tuple[str, PackResource]] = [
        ("inventory", pack.inventory),
        ("lexicon", pack.lexicon),
    ]
    for index, rule in enumerate(pack.rules):
        items.append((f"rules[{index}]", rule))
    for key, mapping in pack.mappings.items():
        items.append((f"mappings.{key}", mapping))
    if pack.scoring_profile:
        items.append(("scoring_profile", pack.scoring_profile))
    if pack.templates:
        items.append(("templates", pack.templates))
    return items


def _collect_model_resources(pack: ModelPack) -> list[tuple[str, PackResource]]:
    items: list[tuple[str, PackResource]] = [
        (f"files[{index}]", resource)
        for index, resource in enumerate(pack.files)
    ]
    if pack.tokenizer:
        items.append(("tokenizer", pack.tokenizer))
    if pack.prompt:
        items.append(("prompt", pack.prompt))
    if pack.output_schema:
        items.append(("output_schema", pack.output_schema))
    return items


__all__ = [
    "DEFAULT_PACKS_DIR",
    "load_language_pack",
    "load_model_pack",
    "resolve_manifest_path",
]
