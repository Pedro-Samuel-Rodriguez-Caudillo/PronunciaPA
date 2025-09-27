from ipa_core.backends.base import ASRBackend

class NullASRBackend(ASRBackend):
    name = "null"

    def transcribe_ipa(self, audio_path: str) -> str:
        # Stub: cadena fija para probar el wiring del kernel
        return "dɛmo"
