"""Shared helpers for LLM adapters and services."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import ValidationError


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError("Output schema must be a JSON object.")
    return data


def extract_json_object(raw: str) -> dict[str, Any]:
    """Extract the first JSON object found in raw text."""
    start = raw.find("{")
    if start == -1:
        raise ValidationError("LLM output does not contain JSON.")
    depth = 0
    end = None
    for idx, ch in enumerate(raw[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break
    if end is None:
        raise ValidationError("LLM output contains incomplete JSON.")
    payload = raw[start:end]
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"LLM output JSON invalid: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValidationError("LLM output JSON must be an object.")
    return obj


def validate_json_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate required keys and basic types from a JSON schema dict."""
    required = schema.get("required", [])
    for key in required:
        if key not in payload:
            raise ValidationError(f"LLM output missing required key: {key}")

    properties = schema.get("properties", {})
    for key, rule in properties.items():
        if key not in payload:
            continue
        expected = rule.get("type")
        if expected and not _matches_type(payload[key], expected):
            raise ValidationError(f"LLM output key '{key}' has invalid type.")


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "number":
        return isinstance(value, (int, float))
    if expected == "integer":
        return isinstance(value, int)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def build_fallback(schema: dict[str, Any], *, summary: Optional[str] = None) -> dict[str, Any]:
    """Generate a deterministic fallback payload based on schema."""
    payload: dict[str, Any] = {}
    properties = schema.get("properties", {})
    for key, rule in properties.items():
        expected = rule.get("type")
        if expected == "array":
            payload[key] = []
        elif expected == "object":
            payload[key] = {}
        elif expected == "string":
            payload[key] = summary or "Sin feedback disponible."
        elif expected == "number":
            payload[key] = 0.0
        elif expected == "integer":
            payload[key] = 0
        elif expected == "boolean":
            payload[key] = False
        else:
            payload[key] = None
    return payload
