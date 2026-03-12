"""Resolución centralizada del binario ffmpeg para el proyecto."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHED_FFMPEG_BINARY: Optional[str] = None


def find_ffmpeg_binary() -> Optional[str]:
    """Encuentra el binario ffmpeg desde entorno, PATH o imageio-ffmpeg."""
    global _CACHED_FFMPEG_BINARY
    if _CACHED_FFMPEG_BINARY:
        return _CACHED_FFMPEG_BINARY

    candidates: list[Optional[str]] = [
        os.environ.get("PRONUNCIAPA_FFMPEG_BIN"),
        shutil.which("ffmpeg"),
    ]

    try:
        import imageio_ffmpeg  # type: ignore

        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass

    if os.name == "nt":
        candidates.extend(
            [
                r"C:\ffmpeg\ffmpeg.exe",
                r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
            ]
        )

    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).is_file():
            _CACHED_FFMPEG_BINARY = str(Path(candidate))
            return _CACHED_FFMPEG_BINARY

    return None


def ensure_ffmpeg_in_path() -> Optional[str]:
    """Asegura que el directorio del binario ffmpeg esté presente en PATH."""
    binary = find_ffmpeg_binary()
    if not binary:
        return None

    ffmpeg_dir = str(Path(binary).parent)
    current_path = os.environ.get("PATH", "")
    path_entries = current_path.split(os.pathsep) if current_path else []
    if ffmpeg_dir not in path_entries:
        os.environ["PATH"] = os.pathsep.join([ffmpeg_dir, *path_entries]) if current_path else ffmpeg_dir
    return binary


def configure_pydub() -> Optional[str]:
    """Configura pydub para usar el ffmpeg resuelto sin warnings espurios."""
    binary = ensure_ffmpeg_in_path()
    if not binary:
        return None

    try:
        from pydub import AudioSegment  # type: ignore

        AudioSegment.converter = binary
    except Exception as exc:  # pragma: no cover - defensivo
        logger.debug("No se pudo configurar pydub con ffmpeg: %s", exc)
    return binary
