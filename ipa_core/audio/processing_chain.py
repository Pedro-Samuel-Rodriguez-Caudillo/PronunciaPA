"""Cadena de procesamiento de audio (Chain of Responsibility).

Define pasos atómicos e idempotentes para preparar audio antes de ASR:
1. EnsureWavStep  — normalizar formato a WAV PCM 16kHz mono
2. VADTrimStep    — recortar silencios inicio/final con energía
3. QualityCheckStep — validar calidad (SNR, duración, clipping)

Uso::

    chain = AudioProcessingChain.default(vad_enabled=True)
    ctx = AudioContext(audio=audio_input, lang="es")
    ctx = await chain.process(ctx)
    # ctx.audio contiene el audio procesado
    # ctx.quality_result contiene el resultado de calidad
    ctx.cleanup()  # elimina archivos temporales
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional

from ipa_core.types import AudioInput

logger = logging.getLogger(__name__)


@dataclass
class AudioContext:
    """Contexto mutable que fluye a través de la cadena de procesamiento."""

    audio: AudioInput
    lang: str = ""
    temp_files: List[str] = field(default_factory=list)
    vad_result: Optional[Any] = None
    quality_result: Optional[Any] = None
    steps_applied: List[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def was_step_applied(self, name: str) -> bool:
        return name in self.steps_applied

    def mark_step(self, name: str) -> None:
        if name not in self.steps_applied:
            self.steps_applied.append(name)

    def add_temp_file(self, path: str) -> None:
        if path not in self.temp_files:
            self.temp_files.append(path)

    def cleanup(self) -> None:
        """Eliminar todos los archivos temporales registrados."""
        for path in self.temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
                    logger.debug("Eliminado temp file: %s", path)
            except OSError as exc:
                logger.warning("No se pudo eliminar temp file %s: %s", path, exc)
        self.temp_files.clear()


class EnsureWavStep:
    """Paso 1: normalizar formato de audio a WAV PCM 16kHz mono."""

    name = "ensure_wav"

    async def process(self, ctx: AudioContext) -> AudioContext:
        if ctx.was_step_applied(self.name):
            return ctx
        try:
            from ipa_core.audio.files import ensure_wav
            new_path, is_temp = ensure_wav(
                ctx.audio["path"],
                target_sample_rate=16000,
                target_channels=1,
            )
            if is_temp:
                ctx.add_temp_file(new_path)
            new_audio = dict(ctx.audio)
            new_audio["path"] = new_path
            new_audio["sample_rate"] = 16000
            new_audio["channels"] = 1
            ctx.audio = new_audio  # type: ignore[assignment]
            ctx.meta["ensure_wav"] = {"converted": is_temp, "path": new_path}
        except Exception as exc:
            logger.warning("EnsureWavStep falló, continuando con audio original: %s", exc)
            ctx.meta["ensure_wav"] = {"error": str(exc)}
        ctx.mark_step(self.name)
        return ctx


class VADTrimStep:
    """Paso 2: recortar silencios inicio/final con detección de energía.

    Parameters
    ----------
    enabled : bool
        Si False, actúa como no-op (idempotencia garantizada).
    """

    name = "vad_trim"

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    async def process(self, ctx: AudioContext) -> AudioContext:
        if ctx.was_step_applied(self.name) or not self.enabled:
            ctx.mark_step(self.name)
            return ctx
        try:
            import wave
            import tempfile
            from ipa_core.audio.vad import analyze_vad

            vad = analyze_vad(ctx.audio["path"])
            ctx.vad_result = vad
            ctx.meta["vad"] = {
                "speech_ratio": vad.speech_ratio,
                "duration_ms": vad.duration_ms,
                "speech_segments": len(vad.speech_segments),
                "trim_suggestion": vad.trim_suggestion,
            }

            if vad.trim_suggestion:
                start_ms, end_ms = vad.trim_suggestion
                trimmed_path = self._trim_wav(ctx.audio["path"], start_ms, end_ms)
                if trimmed_path:
                    ctx.add_temp_file(trimmed_path)
                    new_audio = dict(ctx.audio)
                    new_audio["path"] = trimmed_path
                    ctx.audio = new_audio  # type: ignore[assignment]
                    ctx.meta["vad"]["trimmed"] = True
        except Exception as exc:
            logger.warning("VADTrimStep falló, continuando sin recorte: %s", exc)
            ctx.meta.setdefault("vad", {})["error"] = str(exc)
        ctx.mark_step(self.name)
        return ctx

    @staticmethod
    def _trim_wav(path: str, start_ms: int, end_ms: int) -> Optional[str]:
        """Recortar WAV entre start_ms y end_ms, retorna ruta temporal o None."""
        import wave
        import struct
        import tempfile

        try:
            with wave.open(path, "rb") as wf:
                sr = wf.getframerate()
                sw = wf.getsampwidth()
                nc = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())

            start_frame = int(start_ms * sr / 1000)
            end_frame = int(end_ms * sr / 1000)
            bytes_per_frame = sw * nc
            start_byte = start_frame * bytes_per_frame
            end_byte = end_frame * bytes_per_frame
            trimmed = frames[start_byte:end_byte]

            if not trimmed:
                return None

            tmp = tempfile.NamedTemporaryFile(
                prefix="pronunciapa_vad_", suffix=".wav", delete=False
            )
            with wave.open(tmp.name, "wb") as out_wf:
                out_wf.setnchannels(nc)
                out_wf.setsampwidth(sw)
                out_wf.setframerate(sr)
                out_wf.writeframes(trimmed)
            return tmp.name
        except Exception as exc:
            logger.warning("_trim_wav falló: %s", exc)
            return None


class QualityCheckStep:
    """Paso 3: evaluar calidad de audio (SNR, duración, clipping)."""

    name = "quality_check"

    async def process(self, ctx: AudioContext) -> AudioContext:
        if ctx.was_step_applied(self.name):
            return ctx
        try:
            from ipa_core.services.audio_quality import assess_audio_quality

            quality_res, warnings, _ = assess_audio_quality(ctx.audio["path"])
            ctx.quality_result = quality_res
            ctx.meta["quality"] = {
                "passed": quality_res.passed if quality_res else None,
                "warnings": warnings,
            }
            if quality_res:
                ctx.meta["audio_quality"] = quality_res.to_dict()
        except Exception as exc:
            logger.warning("QualityCheckStep falló: %s", exc)
            ctx.meta.setdefault("quality", {})["error"] = str(exc)
        ctx.mark_step(self.name)
        return ctx


class AudioProcessingChain:
    """Cadena configurable de pasos de procesamiento de audio."""

    def __init__(self, steps: List[Any]) -> None:
        self.steps = steps

    async def process(self, ctx: AudioContext) -> AudioContext:
        """Ejecutar todos los pasos en orden."""
        for step in self.steps:
            ctx = await step.process(ctx)
        return ctx

    @classmethod
    def default(cls, *, vad_enabled: bool = True) -> "AudioProcessingChain":
        """Cadena estándar: EnsureWav → VADTrim → QualityCheck."""
        return cls([
            EnsureWavStep(),
            VADTrimStep(enabled=vad_enabled),
            QualityCheckStep(),
        ])

    @classmethod
    def minimal(cls) -> "AudioProcessingChain":
        """Cadena mínima: solo EnsureWav (para tests sin deps externas)."""
        return cls([EnsureWavStep()])


__all__ = [
    "AudioContext",
    "EnsureWavStep",
    "VADTrimStep",
    "QualityCheckStep",
    "AudioProcessingChain",
]
