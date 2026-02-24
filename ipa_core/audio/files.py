"""Helpers para normalizar archivos de audio a WAV PCM."""
from __future__ import annotations

import logging
import os
import struct
import tempfile
import wave
from pathlib import Path
from typing import Tuple

from ipa_core.errors import FileNotFound, UnsupportedFormat

logger = logging.getLogger(__name__)


def _scan_wav_chunks(raw: bytes) -> dict:
    """Escanea un buffer RIFF/WAV y retorna offsets y tamaños de chunks clave.

    Funciona con WAV no estándar que incluyen sub-chunks extra (LIST/INFO,
    JUNK, bext, etc.) antes del chunk ``data``, lo que rompe ``wave.open()``
    y confunde a ffmpeg.

    Returns:
        Dict con claves ``"fmt"``, ``"data"`` — cada valor es
        ``{"offset": int, "size": int}`` apuntando al contenido del chunk
        (byte posterior al header de 8 bytes), o ``None`` si no se encontró.
    """
    result: dict = {"fmt": None, "data": None}
    if len(raw) < 12 or raw[0:4] != b"RIFF" or raw[8:12] != b"WAVE":
        return result
    pos = 12
    while pos + 8 <= len(raw):
        chunk_id = raw[pos : pos + 4]
        chunk_size = struct.unpack_from("<I", raw, pos + 4)[0]
        content_offset = pos + 8
        key = chunk_id.decode("latin-1", errors="replace").rstrip("\x00")
        if key in ("fmt ", "data"):
            result[key.strip()] = {"offset": content_offset, "size": chunk_size, "header_offset": pos}
            if result["fmt"] and result["data"]:
                break
        # Los chunks RIFF se alinean a 2 bytes
        pos += 8 + chunk_size + (chunk_size % 2)
    return result


def _fix_wav_data_chunk(path: str) -> None:
    """Reescribe los campos ChunkSize y Subchunk2Size del header WAV.

    El paquete ``record`` de Flutter (especialmente en Windows) genera archivos
    WAV con el tamaño del chunk de datos incorrecto cuando la grabación
    es corta o finaliza de forma abrupta.  Esto hace que ``wave.getnframes()``
    devuelva valores enormes y que algunas librerías de ASR no lean audio alguno.

    A diferencia de la versión anterior, este helper **escanea** la posición
    real del chunk ``data`` en lugar de asumir el offset fijo 40 (header
    estándar de 44 bytes).  Así no corrompe WAVs con sub-chunks extra.
    """
    file_size = os.path.getsize(path)
    if file_size < 44:
        return  # demasiado pequeño para ser un WAV válido

    with open(path, "r+b") as f:
        raw = f.read()

    if raw[0:4] != b"RIFF" or raw[8:12] != b"WAVE":
        return  # no es un WAV estándar

    chunks = _scan_wav_chunks(raw)
    data_info = chunks.get("data")
    if data_info is None:
        return  # no se encontró chunk data — dejar que el fallback lo maneje

    data_header_offset = data_info["header_offset"]
    actual_data_size = file_size - data_info["offset"]
    stored_data_size = data_info["size"]

    expected_riff = file_size - 8
    stored_riff = struct.unpack_from("<I", raw, 4)[0]

    needs_fix = (stored_riff != expected_riff) or (stored_data_size != actual_data_size)
    if needs_fix:
        with open(path, "r+b") as f:
            f.seek(4)
            f.write(struct.pack("<I", expected_riff))
            f.seek(data_header_offset + 4)
            f.write(struct.pack("<I", actual_data_size))


try:  # Carga perezosa para evitar dependencia obligatoria en tests unitarios.
    from pydub import AudioSegment
except ImportError:  # pragma: no cover - ejecutado solo cuando falta la dependencia.
    AudioSegment = None  # type: ignore[assignment]


def _convert_with_ffmpeg(
    input_path: str,
    output_path: str,
    target_sample_rate: int,
    target_channels: int,
) -> bool:
    """Convierte cualquier audio a WAV PCM 16-bit usando ffmpeg.

    Usa exactamente los mismos parámetros que el proyecto de referencia pruebaASR
    para garantizar máxima compatibilidad con Allosaurus:
        -ar {sample_rate} -ac {channels} -sample_fmt s16

    Retorna True si la conversión fue exitosa.
    """
    import subprocess
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ar", str(target_sample_rate),
                "-ac", str(target_channels),
                "-sample_fmt", "s16",
                output_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.debug("ffmpeg stderr: %s", result.stderr[-500:] if result.stderr else "")
        return result.returncode == 0
    except FileNotFoundError:
        logger.debug("ffmpeg no encontrado en PATH")
        return False


def ensure_wav(
    path: str,
    *,
    target_sample_rate: int = 16000,
    target_channels: int = 1,
) -> Tuple[str, bool]:
    """Garantiza que ``path`` apunte a un WAV PCM 16-bit compatible con Allosaurus.

    Siempre convierte con ffmpeg (igual que pruebaASR) para evitar el bug de
    Flutter/record que escribe el data chunk size incorrecto en el header WAV:
    si se devolviera el archivo original, Allosaurus leería solo los frames
    indicados en el header, cortando el inicio del audio.

    Estrategia:
    1. **ffmpeg** (primera opción): convierte con ``-sample_fmt s16``.
       Lee hasta EOF real ignorando el tamaño del header.
    2. pydub (fallback si ffmpeg no está en PATH).

    Retorna ``(ruta_final, es_temporal)``.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFound(f"Audio no encontrado: {path}")

    ext = p.suffix.lower()

    # No hay fast-path para WAV: Flutter/record frecuentemente escribe el campo
    # data chunk size incorrecto (0 o valor obsoleto). Si devolviéramos el archivo
    # tal cual, Allosaurus leería internamente con wave.open() y solo procesaría
    # los frames indicados en el header — causando que se recorte el inicio del audio.
    # ffmpeg también respeta el tamaño del chunk; corregir el header antes asegura
    # que lee todo el audio real hasta EOF.
    if ext not in {".wav", ".mp3", ".ogg", ".m4a", ".webm", ".opus", ".flac"}:
        raise UnsupportedFormat(f"Formato de audio no soportado: {ext}")

    # Para WAV: corregir header in-place antes de pasar a ffmpeg.
    # Flutter/record escribe ChunkSize/Subchunk2Size stale cuando la grabación
    # finaliza de forma abrupta o sin flush explícito.
    if ext == ".wav":
        _fix_wav_data_chunk(str(p))

    # ── ffmpeg (camino principal, igual que pruebaASR) ──────────────────────
    tmp = tempfile.NamedTemporaryFile(
        prefix="pronunciapa_", suffix=".wav", delete=False
    )
    tmp.close()

    if _convert_with_ffmpeg(path, tmp.name, target_sample_rate, target_channels):
        logger.debug("ensure_wav: convertido con ffmpeg → %s", tmp.name)
        return tmp.name, True

    # Limpiar temporal fallido
    try:
        os.unlink(tmp.name)
    except OSError:
        pass

    # ── pydub (fallback si ffmpeg no disponible) ────────────────────────────
    if AudioSegment is None:
        raise UnsupportedFormat(
            "ffmpeg no encontrado y pydub no instalado. "
            "Instala ffmpeg (recomendado) o pydub: pip install pydub"
        )

    try:
        audio = AudioSegment.from_file(path)
    except Exception as pydub_exc:
        raise UnsupportedFormat(
            f"Formato de audio no decodificable: {path}"
        ) from pydub_exc

    audio = (
        audio.set_frame_rate(target_sample_rate)
        .set_channels(target_channels)
        .set_sample_width(2)
    )
    tmp2 = tempfile.NamedTemporaryFile(prefix="pronunciapa_", suffix=".wav", delete=False)
    tmp2.close()
    audio.export(tmp2.name, format="wav")
    logger.debug("ensure_wav: convertido con pydub → %s", tmp2.name)
    return tmp2.name, True


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
