"""Tests para `EpitranTextRef`."""
from __future__ import annotations

from ipa_core.textref.epitran import EpitranTextRef


class _FakeModel:
    def __init__(self, code: str, has_trans_list: bool = True) -> None:
        self.code = code
        self.has_trans_list = has_trans_list

    def trans_list(self, text: str):
        if not self.has_trans_list:
            raise AttributeError("no trans_list")
        return [text.replace(" ", ""), self.code]

    def transliterate(self, text: str) -> str:
        return text.replace(" ", "")


def test_epitran_uses_lang_mapping():
    provider = EpitranTextRef(factory=lambda code: _FakeModel(code))

    tokens = provider.to_ipa("hola", lang="es")

    assert tokens[-1] == "spa-Latn"


def test_epitran_fallback_transliterate():
    provider = EpitranTextRef(factory=lambda code: _FakeModel(code, has_trans_list=False))

    tokens = provider.to_ipa("ho la", lang="en")

    assert tokens == ["h", "o", "l", "a"]
