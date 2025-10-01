"""Utilities for discovering and loading IPA Core plugins.

This module provides a tiny abstraction over :mod:`importlib.metadata`
entry points so that the rest of the codebase can reason about plugins
in terms of logical groups (``asr_backend``, ``textref`` ...).
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Iterable

__all__ = [
    "PLUGIN_GROUPS",
    "PluginGroup",
    "load_plugin",
    "list_plugins",
]


@dataclass(frozen=True)
class PluginGroup:
    """Represents a logical group of plugins.

    Attributes
    ----------
    name:
        Human-friendly identifier used from the CLI (``asr``/``textref`` ...).
    entrypoint_group:
        Name of the entry-point group registered in ``pyproject.toml``.
    description:
        Short explanation used when rendering help messages.
    """

    name: str
    entrypoint_group: str
    description: str


PLUGIN_GROUPS: dict[str, PluginGroup] = {
    "asr": PluginGroup(
        name="asr",
        entrypoint_group="ipa_core.backends.asr",
        description="Backends de reconocimiento de voz a IPA",
    ),
    "textref": PluginGroup(
        name="textref",
        entrypoint_group="ipa_core.plugins.textref",
        description="Conversores de texto a IPA (referencia)",
    ),
    "comparator": PluginGroup(
        name="comparator",
        entrypoint_group="ipa_core.plugins.compare",
        description="Comparadores de secuencias IPA",
    ),
    "preprocessor": PluginGroup(
        name="preprocessor",
        entrypoint_group="ipa_core.plugins.preprocess",
        description="Preprocesadores de audio/texto previos al pipeline",
    ),
}


def _iter_entry_points(group: str) -> Iterable[metadata.EntryPoint]:
    """Iterate over entry points for ``group``.

    A thin wrapper around :func:`importlib.metadata.entry_points` so the
    behaviour can be stubbed easily during testing.
    """

    return metadata.entry_points().select(group=group)


def load_plugin(group: str, name: str):
    """Load a plugin identified by ``group`` and ``name``.

    Parameters
    ----------
    group:
        Entry-point group name (``ipa_core.backends.asr`` ...).
    name:
        Plugin name inside the group.

    Returns
    -------
    Any
        The object exposed by the entry point (usually a class).

    Raises
    ------
    ValueError
        If the plugin cannot be found within the requested group.
    """

    for ep in _iter_entry_points(group):
        if ep.name == name:
            return ep.load()
    raise ValueError(f"Plugin no encontrado: {group}::{name}")


def list_plugins(group: str) -> list[str]:
    """Return the available plugin names for ``group`` sorted alphabetically."""

    return sorted(ep.name for ep in _iter_entry_points(group))
