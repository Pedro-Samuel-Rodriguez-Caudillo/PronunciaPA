"""Puertos (interfaces) del microkernel.

Todos los contratos (Protocol) se re-exportan aquí para facilitar imports:

    from ipa_core.ports import ASRBackend, Comparator, TTSProvider
"""

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.features import FeatureExtractor
from ipa_core.ports.history import HistoryPort
from ipa_core.ports.llm import LLMAdapter
from ipa_core.ports.oov import OOVHandlerPort, PassthroughOOVHandler
from ipa_core.ports.phoneme_corpus import PhonemeCorpusPort, DiskPhonemeCorpus, NullPhonemeCorpus
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.ports.tts import TTSProvider

__all__ = [
    "ASRBackend",
    "Comparator",
    "DiskPhonemeCorpus",
    "FeatureExtractor",
    "HistoryPort",
    "LLMAdapter",
    "NullPhonemeCorpus",
    "OOVHandlerPort",
    "PassthroughOOVHandler",
    "PhonemeCorpusPort",
    "Preprocessor",
    "TextRefProvider",
    "TTSProvider",
]

