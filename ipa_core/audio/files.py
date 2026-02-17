"""Helpers para normalizar archivos de audio a WAV PCM."""
from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path
from typing import Tuple

from ipa_core.errors import FileNotFound, UnsupportedFormat

try:  # Carga perezosa para evitar dependencia obligatoria en tests unitarios.
    from pydub import AudioSegment
except ImportError:  # pragma: no cover - ejecutado solo cuando falta la dependencia.
    AudioSegment = None  # type: ignore[assignment]


def ensure_wav(
    path: str,
    *,
    target_sample_rate: int = 16000,
    target_channels: int = 1,
) -> Tuple[str, bool]:
    """Garantiza que `path` apunte a un WAV PCM compatible con Allosaurus.

    Retorna la ruta final y un flag indicando si es temporal.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFound(f"Audio no encontrado: {path}")
    ext = p.suffix.lower()
    if ext == ".wav":
        try:
            with wave.open(str(p), "rb") as w:
                sr = w.getframerate()
                ch = w.getnchannels()
        except (wave.Error, EOFError) as exc:
            raise UnsupportedFormat(f"Formato no soportado o WAV inválido: {path}") from exc

        if sr == target_sample_rate and ch == target_channels:
            return path, False

        if AudioSegment is None:
            raise UnsupportedFormat("pydub/ffmpeg necesarios para resamplear WAV")

        audio = AudioSegment.from_file(path)
        audio = audio.set_frame_rate(target_sample_rate).set_channels(target_channels).set_sample_width(2)
        tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_", suffix=".wav", delete=False)
        audio.export(tmp.name, format="wav")
        return tmp.name, True

    if ext not in {".mp3", ".ogg", ".m4a", ".webm", ".opus", ".flac"}:
        raise UnsupportedFormat(f"Formato de audio no soportado: {ext}")

    if AudioSegment is None:
        raise UnsupportedFormat("pydub/ffmpeg necesarios para convertir audio a WAV")

    audio = AudioSegment.from_file(path)
    audio = audio.set_frame_rate(target_sample_rate).set_channels(target_channels).set_sample_width(2)
    tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_", suffix=".wav", delete=False)
    audio.export(tmp.name, format="wav")
    return tmp.name, True


def persist_bytes(data: bytes, *, suffix: str) -> str:
    """Guarda bytes arbitrarios respetando el sufijo indicado."""
    tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_", suffix=suffix, delete=False)
    with open(tmp.name, "wb") as fh:
        fh.write(data)
    return tmp.name


def write_bytes_to_wav(data: bytes) -> str:
    """Atajo para guardar bytes WAV."""
    return persist_bytes(data, suffix=".wav")


def cleanup_temp(path: str) -> None:
    """Elimina archivos temporales silenciosamente."""
    try:
        os.unlink(path)
    except OSError:
        pass
