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
    """Convierte una cadena IPA en tokens conservando diacríticos."""
    sorted_mg = sorted(multigraphs or DEFAULT_MULTIGRAPHS, key=len, reverse=True)
    normalized = _prepare_text(text, strip_suprasegmentals)
    
    tokens: list[str] = []
    current: list[str] = []
    state = {"i": 0, "attach_next": False, "chars": list(normalized), "n": len(normalized)}

    while state["i"] < state["n"]:
        if _try_match_multigraph(state, sorted_mg, tokens, current):
            continue
        
        ch = state["chars"][state["i"]]
        if _process_special_char(ch, state, tokens, current):
            continue
            
        _process_base_char(ch, state, tokens, current)

    _flush(tokens, current)
    return [tok for tok in tokens if tok]


def _prepare_text(text: str, strip: bool) -> str:
    norm = unicodedata.normalize("NFC", text)
    if not strip:
        return norm
    return "".join(ch for ch in norm if ch not in _SUPRASEGMENTALS)


def _flush(tokens: list, current: list) -> None:
    if current:
        tokens.append("".join(current))
        current.clear()


def _try_match_multigraph(state: dict, multigraphs: list, tokens: list, current: list) -> bool:
    if current and state["attach_next"]:
        return False
        
    for mg in multigraphs:
        if _is_mg_at_pos(state, mg):
            _flush(tokens, current)
            return _apply_mg_match(state, mg, current)
    return False


def _is_mg_at_pos(state: dict, mg: str) -> bool:
    mg_len = len(mg)
    if state["i"] + mg_len > state["n"]:
        return False
    return "".join(state["chars"][state["i"] : state["i"] + mg_len]) == mg


def _apply_mg_match(state: dict, mg: str, current: list) -> bool:
    current.extend(state["chars"][state["i"] : state["i"] + len(mg)])
    state["i"] += len(mg)
    return True


def _process_special_char(ch: str, state: dict, tokens: list, current: list) -> bool:
    if ch.isspace():
        return _handle_space(state, tokens, current)
    if ch in _SUPRASEGMENTALS:
        return _handle_suprasegmental(ch, state, tokens, current)
    if _is_modifier(ch):
        current.append(ch)
        state["i"] += 1
        return True
    if ch in _TIE_BARS:
        current.append(ch)
        state["attach_next"] = True
        state["i"] += 1
        return True
    return False


def _handle_space(state: dict, tokens: list, current: list) -> bool:
    _flush(tokens, current)
    state["attach_next"] = False
    state["i"] += 1
    return True


def _handle_suprasegmental(ch: str, state: dict, tokens: list, current: list) -> bool:
    _flush(tokens, current)
    tokens.append(ch)
    state["attach_next"] = False
    state["i"] += 1
    return True


def _is_modifier(ch: str) -> bool:
    return unicodedata.combining(ch) or ch in _LENGTH_MARKS or ch in _ATTACHABLE_MODIFIERS


def _process_base_char(ch: str, state: dict, tokens: list, current: list) -> None:
    if not current or state["attach_next"]:
        current.append(ch)
        state["attach_next"] = False
    else:
        _flush(tokens, current)
        current.append(ch)
    state["i"] += 1


__all__ = [
    "tokenize_ipa",
    "DEFAULT_MULTIGRAPHS",
    "DIPHTHONG_MULTIGRAPHS",
]
