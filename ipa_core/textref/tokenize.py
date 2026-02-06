"""Tokenización IPA con soporte de diacríticos y suprasegmentales."""
from __future__ import annotations

import unicodedata
from typing import Optional, Sequence

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

# Multigrafos IPA estándar (africadas y secuencias comunes)
DEFAULT_MULTIGRAPHS: tuple[str, ...] = (
    "tʃ", "dʒ", "ts", "dz",
)

# Diptongos frecuentes en inventarios ES/EN
DIPHTHONG_MULTIGRAPHS: tuple[str, ...] = (
    "aɪ", "aʊ", "ɔɪ", "oʊ", "eɪ",
    "ai", "ei", "oi", "au", "eu", "iu",
)


def tokenize_ipa(
    text: str,
    *,
    multigraphs: Optional[Sequence[str]] = None,
    strip_suprasegmentals: bool = False,
) -> list[str]:
    """Convierte una cadena IPA en tokens conservando diacríticos.

    Parámetros
    ----------
    text : str
        Cadena IPA a tokenizar.
    multigraphs : Sequence[str] | None
        Secuencias de caracteres que deben tratarse como un solo token
        (ej: africadas ``tʃ``, ``dʒ``). Si None, usa solo las africadas
        estándar ``DEFAULT_MULTIGRAPHS``.
    strip_suprasegmentals : bool
        Si True, elimina acentos y separadores silábicos del resultado.
    """
    if multigraphs is None:
        multigraphs = DEFAULT_MULTIGRAPHS

    # Pre-compute sorted by length descending for greedy matching
    sorted_mg = sorted(multigraphs, key=len, reverse=True) if multigraphs else []
    max_mg_len = max((len(m) for m in sorted_mg), default=0)

    normalized = unicodedata.normalize("NFC", text)
    # Optionally strip suprasegmentals before tokenizing
    if strip_suprasegmentals:
        normalized = "".join(
            ch for ch in normalized
            if ch not in _SUPRASEGMENTALS
        )

    tokens: list[str] = []
    current: list[str] = []
    attach_next = False
    i = 0
    chars = list(normalized)
    n = len(chars)

    def flush() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    while i < n:
        ch = chars[i]

        # Try multigraph match from current position (only at segment boundary)
        if not current or (current and not attach_next):
            matched_mg = False
            for mg in sorted_mg:
                mg_len = len(mg)
                if i + mg_len <= n:
                    candidate = "".join(chars[i:i + mg_len])
                    if candidate == mg:
                        flush()
                        current.extend(chars[i:i + mg_len])
                        i += mg_len
                        matched_mg = True
                        break
            if matched_mg:
                continue

        if ch.isspace():
            flush()
            attach_next = False
            i += 1
            continue
        if ch in _SUPRASEGMENTALS:
            flush()
            tokens.append(ch)
            attach_next = False
            i += 1
            continue
        if unicodedata.combining(ch):
            current.append(ch)
            i += 1
            continue
        if ch in _LENGTH_MARKS or ch in _ATTACHABLE_MODIFIERS:
            current.append(ch)
            i += 1
            continue
        if ch in _TIE_BARS:
            current.append(ch)
            attach_next = True
            i += 1
            continue

        if not current:
            current.append(ch)
            i += 1
            continue
        if attach_next:
            current.append(ch)
            attach_next = False
            i += 1
            continue

        flush()
        current.append(ch)
        i += 1

    flush()
    return [tok for tok in tokens if tok]


__all__ = [
    "tokenize_ipa",
    "DEFAULT_MULTIGRAPHS",
    "DIPHTHONG_MULTIGRAPHS",
]
