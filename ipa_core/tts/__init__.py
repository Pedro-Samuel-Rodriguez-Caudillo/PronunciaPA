"""TTS adapters."""

from ipa_core.tts.adapter import TTSAdapter
from ipa_core.tts.piper import PiperTTS
from ipa_core.tts.system import SystemTTS

__all__ = ["TTSAdapter", "PiperTTS", "SystemTTS"]
