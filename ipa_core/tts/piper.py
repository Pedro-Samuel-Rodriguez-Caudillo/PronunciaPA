"""Piper TTS adapter."""
from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.tts.utils import ensure_output_path, read_audio_meta
from ipa_core.types import AudioInput, TTSResult


class PiperTTS(BasePlugin):
    """Local TTS adapter backed by the Piper CLI."""

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._binary = (
            params.get("binary")
            or os.getenv("PRONUNCIAPA_PIPER_BIN")
            or "piper"
        )
        self._model_path = params.get("model_path")
        self._config_path = params.get("config_path")
        self._sample_rate = int(params.get("sample_rate", 16000))
        self._channels = int(params.get("channels", 1))
        self._speaker = params.get("speaker")
        self._extra_args = list(params.get("extra_args", []))
        self._options = dict(params.get("options", {}))

    async def setup(self) -> None:
        if not _binary_exists(self._binary):
            raise NotReadyError(
                "Piper binary not found. Install it or set PRONUNCIAPA_PIPER_BIN."
            )
        if not self._model_path:
            raise NotReadyError("Piper model_path is required.")
        model_path = Path(self._model_path)
        if not model_path.exists():
            raise NotReadyError(f"Piper model not found: {model_path}")
        if self._config_path:
            config_path = Path(self._config_path)
            if not config_path.exists():
                raise NotReadyError(f"Piper config not found: {config_path}")

    async def synthesize(
        self,
        text: str,
        *,
        lang: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        **kw,
    ) -> TTSResult:
        cleaned = text.strip()
        if not cleaned:
            raise ValidationError("TTS text must be non-empty.")
        if not _binary_exists(self._binary):
            raise NotReadyError(
                "Piper binary not found. Install it or set PRONUNCIAPA_PIPER_BIN."
            )
        if not self._model_path:
            raise NotReadyError("Piper model_path is required.")
        if self._config_path and not Path(self._config_path).exists():
            raise NotReadyError(f"Piper config not found: {self._config_path}")

        out_path = ensure_output_path(output_path, suffix=".wav")
        cmd = [self._binary, "--model", str(self._model_path), "--output_file", str(out_path)]
        if self._config_path:
            cmd.extend(["--config", str(self._config_path)])

        speaker = self._speaker if self._speaker is not None else voice
        if speaker is not None:
            cmd.extend(["--speaker", str(speaker)])

        for key in ("length_scale", "noise_scale", "noise_w", "sentence_silence"):
            if key in self._options:
                cmd.extend([f"--{key}", str(self._options[key])])

        if self._extra_args:
            cmd.extend(str(arg) for arg in self._extra_args)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate(cleaned.encode("utf-8"))
        except FileNotFoundError as exc:
            raise NotReadyError(f"Failed to execute Piper: {self._binary}") from exc
        except Exception as exc:
            raise ValidationError(f"Piper invocation failed: {exc}") from exc

        if proc.returncode != 0:
            detail = stderr.decode(errors="ignore").strip()
            raise ValidationError(f"Piper failed with code {proc.returncode}: {detail}")

        if not out_path.exists():
            raise ValidationError("Piper did not produce an output file.")

        sample_rate, channels = read_audio_meta(
            out_path,
            default_rate=self._sample_rate,
            default_channels=self._channels,
        )
        audio: AudioInput = {
            "path": str(out_path),
            "sample_rate": sample_rate,
            "channels": channels,
        }
        return {
            "audio": audio,
            "meta": {
                "backend": "piper",
                "model_path": str(self._model_path),
                "lang": lang,
                "speaker": speaker,
            },
        }


def _binary_exists(binary: str) -> bool:
    if shutil.which(binary):
        return True
    return Path(binary).exists()


__all__ = ["PiperTTS"]
