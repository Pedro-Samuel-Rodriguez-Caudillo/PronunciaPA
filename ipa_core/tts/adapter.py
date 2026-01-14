"""TTS adapter with Piper primary and system fallback."""
from __future__ import annotations

from typing import Any, Optional

from ipa_core.errors import NotReadyError
from ipa_core.plugins.base import BasePlugin
from ipa_core.tts.piper import PiperTTS
from ipa_core.tts.system import SystemTTS
from ipa_core.types import TTSResult


class TTSAdapter(BasePlugin):
    """Selects Piper when available, then falls back to system TTS."""

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._prefer = str(params.get("prefer", "piper")).lower()
        self._piper = PiperTTS(params.get("piper"))
        self._system = SystemTTS(params.get("system"))
        self._piper_ready = None
        self._system_ready = None

    async def setup(self) -> None:
        self._piper_ready = await _safe_setup(self._piper)
        self._system_ready = await _safe_setup(self._system)

    async def teardown(self) -> None:
        await self._system.teardown()
        await self._piper.teardown()

    async def synthesize(self, text: str, *, lang: str, voice: Optional[str] = None, output_path: Optional[str] = None, **kw) -> TTSResult:
        if self._prefer == "system":
            return await _synthesize_with_fallback(
                primary=self._system,
                primary_ready=self._system_ready,
                fallback=self._piper,
                fallback_ready=self._piper_ready,
                text=text,
                lang=lang,
                voice=voice,
                output_path=output_path,
            )
        return await _synthesize_with_fallback(
            primary=self._piper,
            primary_ready=self._piper_ready,
            fallback=self._system,
            fallback_ready=self._system_ready,
            text=text,
            lang=lang,
            voice=voice,
            output_path=output_path,
        )


async def _safe_setup(plugin: BasePlugin) -> bool:
    try:
        await plugin.setup()
        return True
    except NotReadyError:
        return False


async def _synthesize_with_fallback(
    *,
    primary: BasePlugin,
    primary_ready: Optional[bool],
    fallback: BasePlugin,
    fallback_ready: Optional[bool],
    text: str,
    lang: str,
    voice: Optional[str],
    output_path: Optional[str],
) -> TTSResult:
    if primary_ready is False:
        return await _call_plugin(fallback, fallback_ready, text, lang, voice, output_path)
    try:
        return await _call_plugin(primary, primary_ready, text, lang, voice, output_path)
    except NotReadyError:
        return await _call_plugin(fallback, fallback_ready, text, lang, voice, output_path)


async def _call_plugin(
    plugin: BasePlugin,
    ready_flag: Optional[bool],
    text: str,
    lang: str,
    voice: Optional[str],
    output_path: Optional[str],
) -> TTSResult:
    if ready_flag is False:
        raise NotReadyError("No available TTS backend.")
    synth = getattr(plugin, "synthesize", None)
    if synth is None:
        raise NotReadyError("TTS backend does not implement synthesize.")
    return await synth(text, lang=lang, voice=voice, output_path=output_path)


__all__ = ["TTSAdapter"]
