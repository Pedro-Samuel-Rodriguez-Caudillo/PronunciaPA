"""Tokenización IPA con soporte de diacríticos y suprasegmentales."""
from __future__ import annotations

import unicodedata

_TIE_BARS = {"\u0361", "\u035C"}
_LENGTH_MARKS = {"\u02D0", "\u02D1"}
_SUPRASEGMENTALS = {
    "\u02C8",  # ˈ primary stress
    "\u02CC",  # ˌ secondary stress
    ".",       # syllable break
    "|",       # minor break
    "\u2016",  # ‖ major break
    "\u203F",  # ‿ linking mark
    "\u02E5",  # ˥ tone
    "\u02E6",  # ˦ tone
    "\u02E7",  # ˧ tone
    "\u02E8",  # ˨ tone
    "\u02E9",  # ˩ tone
}
_ATTACHABLE_MODIFIERS = {
    "\u02B0",  # ʰ aspiration
    "\u02B1",  # ʱ breathy-voice
    "\u02B2",  # ʲ palatalization
    "\u02B7",  # ʷ labialization
    "\u02BC",  # ʼ ejective
    "\u02C0",  # ˀ glottalization
    "\u02C1",  # ˁ pharyngealization
    "\u02E0",  # ˠ velarization
    "\u02E4",  # ˤ pharyngealization
    "\u02DE",  # ˞ rhoticity
    "\u1D5B",  # ᵛ voiced labiodental fricative
    "\u1D50",  # ᵐ nasal release
    "\u207F",  # ⁿ nasal release
    "\u1D51",  # ᵑ nasal release
    "\u1D5A",  # ᶺ
    "\u1D3E",  # ᵾ
    "\u1D3F",  # ᵿ
}


def tokenize_ipa(text: str) -> list[str]:
    """Convierte una cadena IPA en tokens conservando diacríticos."""
    normalized = unicodedata.normalize("NFC", text)
    tokens: list[str] = []
    current: list[str] = []
    attach_next = False

    def flush() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    for ch in normalized:
        if ch.isspace():
            flush()
            attach_next = False
            continue
        if ch in _SUPRASEGMENTALS:
            flush()
            tokens.append(ch)
            attach_next = False
            continue
        if unicodedata.combining(ch):
            current.append(ch)
            continue
        if ch in _LENGTH_MARKS or ch in _ATTACHABLE_MODIFIERS:
            current.append(ch)
            continue
        if ch in _TIE_BARS:
            current.append(ch)
            attach_next = True
            continue

        if not current:
            current.append(ch)
            continue
        if attach_next:
            current.append(ch)
            attach_next = False
            continue

        flush()
        current.append(ch)

    flush()
    return [tok for tok in tokens if tok]


__all__ = ["tokenize_ipa"]
