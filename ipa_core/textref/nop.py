from ipa_core.textref.base import TextRef

class NoopTextRef(TextRef):
    def text_to_ipa(self, text: str, lang: str | None = None) -> str:
        # Stub: marca fija para probar el flujo
        return "sɪstema"
