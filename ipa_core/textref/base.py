from abc import ABC, abstractmethod

class TextRef(ABC):
    @abstractmethod
    def text_to_ipa(self, text: str, lang: str | None = None) -> str:
        """Convierte texto de referencia a IPA."""
        raise NotImplementedError
