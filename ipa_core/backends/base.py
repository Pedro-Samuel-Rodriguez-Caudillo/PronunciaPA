from abc import ABC, abstractmethod

class ASRBackend(ABC):
    name: str = "base"

    @abstractmethod
    def transcribe_ipa(self, audio_path: str) -> str:
        """Retorna una cadena IPA a partir del audio."""
        raise NotImplementedError
