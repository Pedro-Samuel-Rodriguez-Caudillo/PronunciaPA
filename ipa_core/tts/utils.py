"""Shared helpers for TTS adapters."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional


def ensure_output_path(output_path: Optional[str], *, suffix: str) -> Path:
    """Return an output path, creating a temp file when needed."""
    if output_path:
        return Path(output_path)
    tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_tts_", suffix=suffix, delete=False)
    return Path(tmp.name)


def read_audio_meta(path: Path, *, default_rate: int, default_channels: int) -> tuple[int, int]:
    """Best-effort audio metadata for WAV/AIFF outputs."""
    suffix = path.suffix.lower()
    if suffix == ".wav":
        try:
            import wave
            with wave.open(str(path), "rb") as handle:
                return handle.getframerate(), handle.getnchannels()
        except Exception:
            return default_rate, default_channels
    if suffix in (".aiff", ".aif", ".aifc"):
        try:
            import aifc
            with aifc.open(str(path), "rb") as handle:
                return handle.getframerate(), handle.getnchannels()
        except Exception:
            return default_rate, default_channels
    return default_rate, default_channels
