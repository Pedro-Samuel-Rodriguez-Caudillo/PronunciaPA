"""Helpers to apply runtime overrides to AppConfig."""
from __future__ import annotations

from typing import Optional

from ipa_core.config.schema import AppConfig


def _copy_model(model, update: dict):
    if hasattr(model, "model_copy"):
        return model.model_copy(update=update)
    return model.copy(update=update)


def apply_overrides(
    cfg: AppConfig,
    *,
    model_pack: Optional[str] = None,
    llm_name: Optional[str] = None,
) -> AppConfig:
    updates: dict = {}
    if model_pack:
        updates["model_pack"] = model_pack
    if llm_name:
        llm_cfg = _copy_model(cfg.llm, {"name": llm_name})
        updates["llm"] = llm_cfg
    if updates:
        return _copy_model(cfg, updates)
    return cfg


__all__ = ["apply_overrides"]
