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

def _rebuild_clean_wav(src_path: str, dst_path: str) -> None:
    """Extrae PCM raw de un WAV no estándar y escribe un WAV limpio de 44 bytes.

    Funciona aunque ``wave.open()`` y ffmpeg fallen por sub-chunks extra
    (LIST/INFO/JUNK/bext) antes del chunk ``data``.

    Raises:
        ValueError: Si no se encuentran los chunks ``fmt`` y ``data``.
    """
    with open(src_path, "rb") as f:
        raw = f.read()

    chunks = _scan_wav_chunks(raw)
    fmt_info = chunks.get("fmt")
    data_info = chunks.get("data")

    if fmt_info is None or data_info is None:
        raise ValueError(
            f"No se encontraron chunks fmt/data en '{src_path}' "
            f"(chunks encontrados: {list(k for k, v in chunks.items() if v)})"
        )

    fmt_bytes = raw[fmt_info["offset"] : fmt_info["offset"] + fmt_info["size"]]
    pcm_bytes = raw[data_info["offset"] : data_info["offset"] + data_info["size"]]

    if len(fmt_bytes) < 16:
        raise ValueError(f"Chunk fmt demasiado pequeño: {len(fmt_bytes)} bytes")

    channels = struct.unpack_from("<H", fmt_bytes, 2)[0]
    sample_rate = struct.unpack_from("<I", fmt_bytes, 4)[0]
    bits_per_sample = struct.unpack_from("<H", fmt_bytes, 14)[0]
    sample_width = bits_per_sample // 8

    with wave.open(dst_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


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
        # Corregir header antes de cualquier operación: el paquete record de
        # Flutter a veces genera ChunkSize/Subchunk2Size incorrectos.
        _fix_wav_data_chunk(str(p))
        # Verificar que wave.open() puede leer el fichero.  Algunos WAV grabados
        # en Windows incluyen sub-chunks extra (LIST/INFO) entre «fmt » y «data»;
        # Python's chunk.py no puede hacer seek sobre Chunk anidados y lanza
        # RuntimeError.  En ese caso forzamos reescritura limpia vía pydub.
        wav_readable = False
        try:
            with wave.open(str(p), "rb") as w:
                sr = w.getframerate()
                ch = w.getnchannels()
            wav_readable = True
        except (wave.Error, EOFError, RuntimeError):
            pass  # fall through to pydub rewrite

        if wav_readable and sr == target_sample_rate and ch == target_channels:
            return path, False

        if not wav_readable:
            # WAV no legible por wave (sub-chunks extra: LIST/INFO/JUNK/bext…).
            # Primero intentamos extracción pura en Python (sin ffmpeg): escaneamos
            # los chunks RIFF manualmente, extraemos el PCM raw y escribimos un WAV
            # limpio de 44 bytes.  Solo si eso falla recurrimos a pydub/ffmpeg.
            tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_clean_", suffix=".wav", delete=False)
            tmp.close()
            try:
                _rebuild_clean_wav(str(p), tmp.name)
                rebuilt_ok = True
            except Exception as rebuild_exc:
                logger.warning("_rebuild_clean_wav falló (%s), recurriendo a pydub", rebuild_exc)
                rebuilt_ok = False
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass

            if rebuilt_ok:
                # Verificar si el WAV reconstruido ya tiene el SR/CH deseados
                try:
                    with wave.open(tmp.name, "rb") as wc:
                        rebuilt_sr = wc.getframerate()
                        rebuilt_ch = wc.getnchannels()
                    if rebuilt_sr == target_sample_rate and rebuilt_ch == target_channels:
                        return tmp.name, True
                    # Necesita resampling — usar pydub si disponible
                    if AudioSegment is not None:
                        try:
                            audio = AudioSegment.from_file(tmp.name, format="wav")
                        except Exception as pydub_exc:
                            raise UnsupportedFormat(
                                f"WAV reconstruido no decodificable por pydub: {path}"
                            ) from pydub_exc
                        audio = (
                            audio.set_frame_rate(target_sample_rate)
                            .set_channels(target_channels)
                            .set_sample_width(2)
                        )
                        tmp2 = tempfile.NamedTemporaryFile(prefix="pronunciapa_", suffix=".wav", delete=False)
                        tmp2.close()
                        audio.export(tmp2.name, format="wav")
                        try:
                            os.unlink(tmp.name)
                        except OSError:
                            pass
                        return tmp2.name, True
                    # Sin pydub: devolver el WAV limpio tal cual (allosaurus resamplea)
                    return tmp.name, True
                except Exception as wave_exc:
                    logger.warning("wave.open falló en WAV reconstruido (%s)", wave_exc)

            # Último recurso: pydub/ffmpeg
            if AudioSegment is None:
                raise UnsupportedFormat("pydub/ffmpeg necesarios para convertir WAV con chunks extra")
            try:
                audio = AudioSegment.from_file(str(p), format="wav")
            except Exception as pydub_exc:
                raise UnsupportedFormat(
                    f"Formato no soportado o WAV inválido (pydub no puede decodificar): {path}"
                ) from pydub_exc
            audio = audio.set_frame_rate(target_sample_rate).set_channels(target_channels).set_sample_width(2)
            tmp3 = tempfile.NamedTemporaryFile(prefix="pronunciapa_", suffix=".wav", delete=False)
            tmp3.close()
            audio.export(tmp3.name, format="wav")
            return tmp3.name, True

        if AudioSegment is None:
            raise UnsupportedFormat("pydub/ffmpeg necesarios para resamplear WAV")

        try:
            audio = AudioSegment.from_file(path)
        except Exception as pydub_exc:
            raise UnsupportedFormat(
                f"Formato WAV no decodificable por pydub: {path}"
            ) from pydub_exc
        audio = audio.set_frame_rate(target_sample_rate).set_channels(target_channels).set_sample_width(2)
        tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_", suffix=".wav", delete=False)
        audio.export(tmp.name, format="wav")
        return tmp.name, True

    if ext not in {".mp3", ".ogg", ".m4a", ".webm", ".opus", ".flac"}:
        raise UnsupportedFormat(f"Formato de audio no soportado: {ext}")

    if AudioSegment is None:
        raise UnsupportedFormat("pydub/ffmpeg necesarios para convertir audio a WAV")

    try:
        audio = AudioSegment.from_file(path)
    except Exception as pydub_exc:
        raise UnsupportedFormat(
            f"Formato de audio no decodificable por pydub: {path}"
        ) from pydub_exc
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
