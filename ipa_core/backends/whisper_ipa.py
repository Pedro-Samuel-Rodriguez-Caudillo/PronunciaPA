# Placeholder para backend Whisper-IPA (Transformers)
# Implementar después: cargar pipeline y devolver IPA real.
from ipa_core.backends.base import ASRBackend

class WhisperIPABackend(ASRBackend):
    name = "whisper-ipa"

    def __init__(self, model_name: str = "neurlang/ipa-whisper-base"):
        self.model_name = model_name
        # TODO: inicializar pipeline HF aquí

    def transcribe_ipa(self, audio_path: str) -> str:
        raise NotImplementedError("Pendiente implementar backend Whisper-IPA")
