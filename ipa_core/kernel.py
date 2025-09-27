from dataclasses import dataclass
from ipa_core.plugins import load_plugin

@dataclass
class KernelConfig:
    asr: str = "null"
    textref: str = "noop"
    comparator: str = "noop"

class Kernel:
    def __init__(self, cfg: KernelConfig):
        ASR = load_plugin("ipa_core.backends.asr", cfg.asr)
        TXT = load_plugin("ipa_core.plugins.textref", cfg.textref)
        CMP = load_plugin("ipa_core.plugins.compare", cfg.comparator)
        self.asr = ASR()
        self.textref = TXT()
        self.cmp = CMP()

    def audio_to_ipa(self, audio_path: str) -> str:
        return self.asr.transcribe_ipa(audio_path)

    def text_to_ipa(self, text: str, lang: str | None = None) -> str:
        return self.textref.text_to_ipa(text, lang)

    def compare(self, ref_ipa: str, hyp_ipa: str):
        return self.cmp.compare(ref_ipa, hyp_ipa)
