"""System TTS adapter with backend detection."""
from __future__ import annotations

import asyncio
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.tts.utils import ensure_output_path, read_audio_meta
from ipa_core.types import AudioInput, TTSResult


class SystemTTS(BasePlugin):
    """Local TTS adapter using system backends."""

    _VOICE_MAP = {
        "en": "en",
        "es": "es",
        "fr": "fr",
        "pt": "pt",
    }

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._backend = (
            params.get("backend")
            or os.getenv("PRONUNCIAPA_TTS_SYSTEM_BACKEND")
            or os.getenv("PRONUNCIAPA_TTS_BACKEND")
        )
        if self._backend:
            self._backend = str(self._backend).lower()
        self._espeak_bin = (
            params.get("espeak_bin")
            or os.getenv("PRONUNCIAPA_TTS_ESPEAK_BIN")
            or os.getenv("PRONUNCIAPA_ESPEAK_BIN")
        )
        self._powershell_bin = params.get("powershell_bin")
        self._default_voice = params.get("voice")
        self._sample_rate = int(params.get("sample_rate", 16000))
        self._channels = int(params.get("channels", 1))

    async def setup(self) -> None:
        backend = self._backend or self._detect_backend()
        if backend == "espeak":
            self._detect_espeak_binary()
            return
        if backend == "say":
            if not shutil.which("say"):
                raise NotReadyError("macOS 'say' command not available.")
            return
        if backend == "sapi":
            self._detect_powershell()
            return
        raise NotReadyError(f"Unsupported system TTS backend: {backend}")

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

        voice = voice or self._default_voice
        backend = self._backend or self._detect_backend()
        if backend == "espeak":
            return await self._synthesize_espeak(cleaned, lang=lang, voice=voice, output_path=output_path)
        if backend == "say":
            return await self._synthesize_say(cleaned, voice=voice, output_path=output_path)
        if backend == "sapi":
            return await self._synthesize_sapi(cleaned, voice=voice, output_path=output_path)
        raise NotReadyError(f"Unsupported system TTS backend: {backend}")

    def _detect_backend(self) -> str:
        if self._backend:
            return self._backend

        if self._has_espeak():
            return "espeak"

        system = platform.system()
        if system == "Windows":
            self._detect_powershell()
            return "sapi"
        if system == "Darwin":
            if shutil.which("say"):
                return "say"
        raise NotReadyError("No system TTS backend detected.")

    def _has_espeak(self) -> bool:
        try:
            self._detect_espeak_binary()
            return True
        except NotReadyError:
            return False

    def _detect_espeak_binary(self) -> str:
        if self._espeak_bin:
            if _binary_exists(self._espeak_bin):
                return self._espeak_bin
            raise NotReadyError(f"eSpeak binary not found: {self._espeak_bin}")

        for candidate in ("espeak-ng", "espeak"):
            if _binary_exists(candidate):
                self._espeak_bin = candidate
                return candidate

        windows_candidates = [
            r"C:\Program Files\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files\eSpeak NG\espeak.exe",
            r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files (x86)\eSpeak NG\espeak.exe",
        ]
        for path in windows_candidates:
            if Path(path).exists():
                self._espeak_bin = path
                return path
        raise NotReadyError("No eSpeak binary detected.")

    def _detect_powershell(self) -> str:
        if self._powershell_bin:
            if _binary_exists(self._powershell_bin):
                return self._powershell_bin
            raise NotReadyError(f"PowerShell binary not found: {self._powershell_bin}")

        for candidate in ("pwsh", "powershell"):
            if shutil.which(candidate):
                self._powershell_bin = candidate
                return candidate
        raise NotReadyError("PowerShell not available for SAPI TTS.")

    def _resolve_espeak_voice(self, lang: str, voice: Optional[str]) -> str:
        if voice:
            return voice
        lang = (lang or "").split("-")[0]
        return self._VOICE_MAP.get(lang, lang or "en")

    async def _synthesize_espeak(
        self,
        text: str,
        *,
        lang: str,
        voice: Optional[str],
        output_path: Optional[str],
    ) -> TTSResult:
        binary = self._detect_espeak_binary()
        out_path = ensure_output_path(output_path, suffix=".wav")
        voice_name = self._resolve_espeak_voice(lang, voice)
        cmd = [binary, "-v", voice_name, "-w", str(out_path), text]
        await _run_command(cmd, "espeak")
        return _build_result(
            out_path,
            backend="espeak",
            sample_rate=self._sample_rate,
            channels=self._channels,
            meta={"lang": lang, "voice": voice_name},
        )

    async def _synthesize_say(
        self,
        text: str,
        *,
        voice: Optional[str],
        output_path: Optional[str],
    ) -> TTSResult:
        if not shutil.which("say"):
            raise NotReadyError("macOS 'say' command not available.")
        out_path = ensure_output_path(output_path, suffix=".aiff")
        cmd = ["say", "-o", str(out_path)]
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text)
        await _run_command(cmd, "say")
        return _build_result(
            out_path,
            backend="say",
            sample_rate=self._sample_rate,
            channels=self._channels,
            meta={"voice": voice},
        )

    async def _synthesize_sapi(
        self,
        text: str,
        *,
        voice: Optional[str],
        output_path: Optional[str],
    ) -> TTSResult:
        powershell = self._detect_powershell()
        out_path = ensure_output_path(output_path, suffix=".wav")
        script = _build_sapi_script(text, out_path, voice=voice)
        cmd = [powershell, "-NoProfile", "-NonInteractive", "-Command", script]
        await _run_command(cmd, "sapi")
        return _build_result(
            out_path,
            backend="sapi",
            sample_rate=self._sample_rate,
            channels=self._channels,
            meta={"voice": voice},
        )


async def _run_command(cmd: list[str], backend: str) -> None:
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Running TTS command: {cmd}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError as exc:
        logger.error(f"TTS binary not found: {cmd[0]}")
        raise NotReadyError(f"Failed to execute {backend} backend: binary not found.") from exc
    except OSError as exc:
        logger.error(f"TTS OS error: {exc}")
        raise ValidationError(f"{backend} invocation failed (OS error): {exc}") from exc
    except Exception as exc:
        logger.error(f"TTS unexpected error: {type(exc).__name__}: {exc}")
        raise ValidationError(f"{backend} invocation failed: {type(exc).__name__}: {exc}") from exc

    if proc.returncode != 0:
        detail = stderr.decode(errors="ignore").strip()
        stdout_detail = stdout.decode(errors="ignore").strip()
        logger.error(f"TTS command failed with code {proc.returncode}: stderr={detail}, stdout={stdout_detail}")
        raise ValidationError(f"{backend} failed with code {proc.returncode}: {detail or stdout_detail or 'no output'}")


def _build_result(
    out_path: Path,
    *,
    backend: str,
    sample_rate: int,
    channels: int,
    meta: Optional[dict[str, Any]] = None,
) -> TTSResult:
    if not out_path.exists():
        raise ValidationError("TTS backend did not produce an output file.")
    rate, ch = read_audio_meta(out_path, default_rate=sample_rate, default_channels=channels)
    audio: AudioInput = {
        "path": str(out_path),
        "sample_rate": rate,
        "channels": ch,
    }
    payload = {"backend": backend}
    if meta:
        payload.update({k: v for k, v in meta.items() if v is not None})
    return {
        "audio": audio,
        "meta": payload,
    }


def _build_sapi_script(text: str, out_path: Path, *, voice: Optional[str]) -> str:
    safe_path = str(out_path).replace("'", "''")
    voice_clause = ""
    if voice:
        safe_voice = voice.replace("'", "''")
        voice_clause = f"$synth.SelectVoice('{safe_voice}')"
    safe_text = text.replace("\r", "")
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "Add-Type -AssemblyName System.Speech",
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer",
            voice_clause,
            f"$synth.SetOutputToWaveFile('{safe_path}')",
            "$synth.Speak(@'",
            safe_text,
            "'@)",
            "$synth.Dispose()",
        ]
    )


def _binary_exists(binary: str) -> bool:
    if shutil.which(binary):
        return True
    return Path(binary).exists()


__all__ = ["SystemTTS"]
