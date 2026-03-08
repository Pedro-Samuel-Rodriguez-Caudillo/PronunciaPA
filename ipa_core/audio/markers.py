"""Helpers para marcar audio ya normalizado internamente."""
from __future__ import annotations

from typing import Any, Mapping


PREPROCESSED_AUDIO_FLAG = "_pronunciapa_preprocessed"
_LEGACY_PREPROCESSED_AUDIO_FLAG = "_skip_ensure_wav"


def mark_audio_preprocessed(audio: Mapping[str, Any]) -> dict[str, Any]:
    """Retorna una copia del audio marcada como ya normalizada a WAV."""
    payload = dict(audio)
    payload[PREPROCESSED_AUDIO_FLAG] = True
    payload.pop(_LEGACY_PREPROCESSED_AUDIO_FLAG, None)
    return payload


def is_audio_preprocessed(audio: Mapping[str, Any]) -> bool:
    """Indica si el audio ya fue normalizado y no requiere ensure_wav."""
    return bool(
        audio.get(PREPROCESSED_AUDIO_FLAG)
        or audio.get(_LEGACY_PREPROCESSED_AUDIO_FLAG)
    )


def strip_audio_markers(audio: Mapping[str, Any]) -> dict[str, Any]:
    """Elimina flags internos antes de exponer el payload hacia afuera."""
    payload = dict(audio)
    payload.pop(PREPROCESSED_AUDIO_FLAG, None)
    payload.pop(_LEGACY_PREPROCESSED_AUDIO_FLAG, None)
    return payload


__all__ = [
    "PREPROCESSED_AUDIO_FLAG",
    "is_audio_preprocessed",
    "mark_audio_preprocessed",
    "strip_audio_markers",
]