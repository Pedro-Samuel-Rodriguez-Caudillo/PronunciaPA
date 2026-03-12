"""Allosaurus plugin wrapper.

This package exposes the entry point used by plugin discovery, while delegating
all ASR logic to the core backend implementation.
"""
from __future__ import annotations

from typing import Any, Optional

from ipa_core.backends.allosaurus_backend import AllosaurusBackend


class AllosaurusASR(AllosaurusBackend):
    """Entry-point compatible wrapper around the core Allosaurus backend."""

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        params = params or {}
        super().__init__(
            model_name=str(params.get("model_name", "uni2005")),
            lang=params.get("lang"),
            device=str(params.get("device", "cpu")),
            emit_timestamps=bool(params.get("emit_timestamps", False)),
        )


__all__ = ["AllosaurusASR"]
