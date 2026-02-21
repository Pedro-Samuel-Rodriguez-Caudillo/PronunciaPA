"""Cadena de procesamiento de audio (Chain of Responsibility).

Define pasos atómicos e idempotentes para preparar audio antes de ASR:
1. EnsureWavStep    — normalizar formato a WAV PCM 16kHz mono
2. VADTrimStep      — recortar silencios inicio/final con energía
3. AGCStep          — normalizar amplitud (Automatic Gain Control)
4. QualityCheckStep — validar calidad (SNR, duración, clipping)

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
            ctx.meta["ensure_wav"] = {"error": str(exc), "error_type": type(exc).__name__}
        ctx.mark_step(self.name)
        return ctx


class VADTrimStep:
    """Paso 2: recortar silencios inicio/final con VAD.

    Parameters
    ----------
    enabled : bool
        Si False, actúa como no-op (idempotencia garantizada).
    backend : str
        Backend VAD a usar: ``"auto"`` (Silero si disponible, sino energía),
        ``"silero"`` (forzar Silero VAD neural), ``"energy"`` (VAD de energía
        clásico, sin dependencias externas).
    """

    name = "vad_trim"

    def __init__(self, *, enabled: bool = True, backend: str = "auto") -> None:
        self.enabled = enabled
        self.backend = backend

    async def process(self, ctx: AudioContext) -> AudioContext:
        if ctx.was_step_applied(self.name) or not self.enabled:
            ctx.mark_step(self.name)
            return ctx
        try:
            import wave
            import tempfile
            from ipa_core.audio.vad import analyze_vad_best

            vad = analyze_vad_best(ctx.audio["path"], backend=self.backend)
            ctx.vad_result = vad
            ctx.meta["vad"] = {
                "speech_ratio": vad.speech_ratio,
                "duration_ms": vad.duration_ms,
                "speech_segments": len(vad.speech_segments),
                "trim_suggestion": vad.trim_suggestion,
            }

            if vad.trim_suggestion:
                # SOLO recortar el final del audio (nunca el inicio).
                #
                # Razones para NO recortar el inicio:
                # 1. El VAD de energía puede no detectar plosivas sordas iniciales
                #    (/p/, /t/, /k/) porque tienen poca energía; Allosaurus también
                #    necesita algunos frames de contexto previo para inicializar su
                #    estado oculto (sin ellos "prueba" → "rueba").
                # 2. Conservar el silencio original al principio es inocuo y
                #    garantiza que nunca se pierda el onset de la primera consonante.
                _start_ms, end_ms = vad.trim_suggestion
                trimmed_path = self._trim_wav(ctx.audio["path"], 0, end_ms)
                if trimmed_path:
                    ctx.add_temp_file(trimmed_path)
                    new_audio = dict(ctx.audio)
                    new_audio["path"] = trimmed_path
                    ctx.audio = new_audio  # type: ignore[assignment]
                    ctx.meta["vad"]["trimmed"] = True
                    ctx.meta["vad"]["path"] = trimmed_path  # exposed for cleanup
        except Exception as exc:
            logger.warning("VADTrimStep falló, continuando sin recorte: %s", exc)
            ctx.meta.setdefault("vad", {})["error"] = str(exc)
        ctx.mark_step(self.name)
        return ctx

    @staticmethod
    def _trim_wav(path: str, start_ms: int, end_ms: int) -> Optional[str]:
        """Recortar WAV entre start_ms y end_ms, retorna ruta temporal o None."""
        import struct
        import tempfile
        import wave

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


class AGCStep:
    """Paso 3: normalización de amplitud (Automatic Gain Control).

    Escala el audio para que su RMS alcance un nivel objetivo (-20 dBFS por
    defecto). Mejora el reconocimiento en audios muy silenciosos o muy fuertes.

    Parameters
    ----------
    enabled : bool
        Si False, actúa como no-op.
    target_dbfs : float
        Nivel objetivo en dBFS. Default: -20.0 (adecuado para ASR).
    max_gain_db : float
        Ganancia máxima a aplicar para evitar amplificar ruido puro.
    """

    name = "agc"

    def __init__(
        self,
        *,
        enabled: bool = True,
        target_dbfs: float = -20.0,
        max_gain_db: float = 20.0,
    ) -> None:
        self.enabled = enabled
        self.target_dbfs = target_dbfs
        self.max_gain_db = max_gain_db

    async def process(self, ctx: AudioContext) -> AudioContext:
        if ctx.was_step_applied(self.name) or not self.enabled:
            ctx.mark_step(self.name)
            return ctx
        try:
            new_path = self._apply_agc(ctx.audio["path"])
            if new_path:
                ctx.add_temp_file(new_path)
                new_audio = dict(ctx.audio)
                new_audio["path"] = new_path
                ctx.audio = new_audio  # type: ignore[assignment]
                ctx.meta["agc"] = {"applied": True, "target_dbfs": self.target_dbfs}
            else:
                ctx.meta["agc"] = {"applied": False}
        except Exception as exc:
            logger.warning("AGCStep falló, continuando con audio original: %s", exc)
            ctx.meta["agc"] = {"error": str(exc)}
        ctx.mark_step(self.name)
        return ctx

    def _apply_agc(self, path: str) -> Optional[str]:
        """Aplicar ganancia al WAV y retornar ruta temporal, o None si no se aplica."""
        import math
        import struct
        import tempfile
        import wave

        with wave.open(path, "rb") as wf:
            sr = wf.getframerate()
            sw = wf.getsampwidth()
            nc = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())

        if sw != 2:
            return None  # Solo soporta 16-bit PCM

        fmt = f"<{len(frames) // 2}h"
        samples = list(struct.unpack(fmt, frames))

        if not samples:
            return None

        max_val = 32767
        sum_sq = sum(s * s for s in samples)
        rms = (sum_sq / len(samples)) ** 0.5

        if rms < 1.0:
            return None  # Audio silencioso, no amplificar

        current_dbfs = 20.0 * math.log10(rms / max_val)
        gain_db = self.target_dbfs - current_dbfs

        if abs(gain_db) < 0.5:
            return None  # Ya en rango aceptable

        gain_db = max(-self.max_gain_db, min(self.max_gain_db, gain_db))
        gain_linear = 10.0 ** (gain_db / 20.0)

        scaled = [max(-max_val, min(max_val, int(s * gain_linear))) for s in samples]

        # Cerrar el archivo temporal antes de abrirlo con wave.open (requerido en Windows)
        with tempfile.NamedTemporaryFile(
            prefix="pronunciapa_agc_", suffix=".wav", delete=False
        ) as tmp:
            tmp_name = tmp.name
        packed = struct.pack(f"<{len(scaled)}h", *scaled)
        with wave.open(tmp_name, "wb") as out_wf:
            out_wf.setnchannels(nc)
            out_wf.setsampwidth(sw)
            out_wf.setframerate(sr)
            out_wf.writeframes(packed)
        return tmp_name


class QualityCheckStep:
    """Paso 4: evaluar calidad de audio (SNR, duración, clipping)."""

    name = "quality_check"

    async def process(self, ctx: AudioContext) -> AudioContext:
        if ctx.was_step_applied(self.name):
            return ctx
        try:
            from ipa_core.services.audio_quality import assess_audio_quality

            speech_segments = None
            if ctx.vad_result is not None:
                speech_segments = ctx.vad_result.speech_segments

            quality_res, warnings, _ = assess_audio_quality(
                ctx.audio["path"],
                speech_segments=speech_segments,
            )
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
        logger.debug(
            "[AudioChain] START  audio=%s sr=%s ch=%s",
            ctx.audio.get("path"),
            ctx.audio.get("sample_rate"),
            ctx.audio.get("channels"),
        )
        for step in self.steps:
            path_before = ctx.audio.get("path")
            ctx = await step.process(ctx)
            path_after = ctx.audio.get("path")
            if path_after != path_before:
                logger.debug(
                    "[AudioChain] %-14s  %s  →  %s",
                    step.name,
                    path_before,
                    path_after,
                )
            else:
                logger.debug(
                    "[AudioChain] %-14s  (unchanged) %s",
                    step.name,
                    path_after,
                )
        logger.debug(
            "[AudioChain] DONE   audio=%s  steps=%s",
            ctx.audio.get("path"),
            ctx.steps_applied,
        )
        return ctx

    @classmethod
    def default(
        cls,
        *,
        vad_enabled: bool = True,
        agc_enabled: bool = True,
        vad_backend: str = "auto",
    ) -> "AudioProcessingChain":
        """Cadena estándar: EnsureWav → AGC → VADTrim → QualityCheck.

        AGC corre antes de VAD para que la normalización de amplitud permita
        al VAD detectar consonantes sordas (/p/, /t/, clusters /pɾ/, /tr/)
        que en grabaciones lejanas caen por debajo del umbral de energía.

        Parameters
        ----------
        vad_enabled : bool
            Activar/desactivar el paso VAD.
        agc_enabled : bool
            Activar/desactivar el paso AGC.
        vad_backend : str
            Backend VAD: ``"auto"`` (Silero si disponible, sino energía),
            ``"silero"``, o ``"energy"``.
        """
        return cls([
            EnsureWavStep(),
            AGCStep(enabled=agc_enabled),
            VADTrimStep(enabled=vad_enabled, backend=vad_backend),
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
    "AGCStep",
    "QualityCheckStep",
    "AudioProcessingChain",
]
