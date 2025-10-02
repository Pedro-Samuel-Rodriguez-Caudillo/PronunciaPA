"""Backend ASR basado en Whisper con salida IPA."""

from __future__ import annotations

import audioop
import wave
from array import array
from pathlib import Path
from typing import Callable, Dict, Optional

from ipa_core.backends.base import ASRBackend

PipelineFactory = Callable[..., Callable[..., Dict[str, str]]]


class WhisperIPABackend(ASRBackend):
    """Convierte audio a IPA utilizando un modelo Whisper afinado."""

    name = "whisper-ipa"
    target_sample_rate = 16_000

    def __init__(
        self,
        model_name: str = "neurlang/ipa-whisper-base",
        *,
        device: int | str | None = None,
        pipeline_factory: PipelineFactory | None = None,
        generate_kwargs: Optional[dict] = None,
        chunk_length_s: float = 30.0,
    ) -> None:
        """Inicializa el backend cargando el pipeline de Transformers."""

        if pipeline_factory is None:
            from transformers import pipeline as hf_pipeline  # type: ignore

            pipeline_factory = hf_pipeline

        self.model_name = model_name
        self.device = device
        self.generate_kwargs = generate_kwargs or {"task": "transcribe"}
        self.chunk_length_s = chunk_length_s
        self._pipeline_factory = pipeline_factory
        self._pipeline = self._create_pipeline()

    # ------------------------------------------------------------------
    # Audio helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_wave(path: Path) -> tuple[bytes, int, int]:
        with wave.open(str(path), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            channels = wav_file.getnchannels()
            frames = wav_file.readframes(wav_file.getnframes())

        if channels > 1:
            frames = audioop.tomono(frames, sample_width, 0.5, 0.5)

        return frames, sample_rate, sample_width

    @classmethod
    def _resample_bytes(cls, frames: bytes, sample_width: int, orig_sr: int) -> tuple[bytes, int]:
        if orig_sr == cls.target_sample_rate:
            return frames, sample_width

        resampled, _ = audioop.ratecv(
            frames,
            sample_width,
            1,
            orig_sr,
            cls.target_sample_rate,
            None,
        )
        return resampled, sample_width

    @staticmethod
    def _bytes_to_float(frames: bytes, sample_width: int) -> list[float]:
        if sample_width not in (1, 2, 4):
            frames = audioop.lin2lin(frames, sample_width, 2)
            sample_width = 2

        if sample_width == 1:
            fmt = "b"
            scale = float(2**7)
        elif sample_width == 2:
            fmt = "h"
            scale = float(2**15)
        else:
            fmt = "i"
            scale = float(2**31)

        samples = array(fmt)
        samples.frombytes(frames)
        return [sample / scale for sample in samples]

    @staticmethod
    def _normalize(samples: list[float]) -> list[float]:
        peak = max((abs(value) for value in samples), default=0.0)
        if peak == 0.0:
            return samples
        return [value / peak for value in samples]

    # ------------------------------------------------------------------
    # Pipeline helpers
    # ------------------------------------------------------------------
    def _create_pipeline(self):
        kwargs: dict = {
            "model": self.model_name,
            "chunk_length_s": self.chunk_length_s,
            "return_timestamps": False,
        }
        if self.device is not None:
            kwargs["device"] = self.device

        pipe = self._pipeline_factory("automatic-speech-recognition", **kwargs)

        model_wrapper = getattr(pipe, "model", None)
        if model_wrapper is not None and hasattr(model_wrapper.config, "forced_decoder_ids"):
            model_wrapper.config.forced_decoder_ids = None
        if model_wrapper is not None and hasattr(model_wrapper.config, "suppress_tokens"):
            model_wrapper.config.suppress_tokens = []

        return pipe

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def transcribe_ipa(self, audio_path: str) -> str:
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"No se encontró el archivo de audio: {audio_path}")

        frames, sr, sample_width = self._load_wave(audio_file)
        frames, sample_width = self._resample_bytes(frames, sample_width, sr)
        samples = self._bytes_to_float(frames, sample_width)
        samples = self._normalize(samples)

        call_kwargs = {"sampling_rate": self.target_sample_rate}
        if self.generate_kwargs:
            call_kwargs["generate_kwargs"] = self.generate_kwargs

        result = self._pipeline(samples, **call_kwargs)
        if not isinstance(result, dict) or "text" not in result:
            raise RuntimeError("El pipeline Whisper devolvió una respuesta inesperada")

        text = result["text"].strip()
        if not text:
            raise RuntimeError("El backend Whisper-IPA devolvió una transcripción vacía")
        return text
