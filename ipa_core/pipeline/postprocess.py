"""Post-processing filters for ASR output.

Cleans up raw IPA transcriptions from Allosaurus and other backends
to improve comparison accuracy. Filters include:
- Removing diacritics not relevant for the target language
- Collapsing duplicate consecutive phonemes
- Filtering non-IPA artifacts (numbers, punctuation, etc.)
- Normalizing common Allosaurus quirks per language
"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

from ipa_core.types import Token


# ── IPA character validation ──────────────────────────────────────────
_IPA_BLOCK = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸ"
    "θœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʕʢʡ"
    "ˈˌːˑ̃ʰʷʲˠˤ̠̪̺̻̥̬̤̰̼"
    "ɫ"
)

_NON_IPA_PATTERN = re.compile(r"[0-9\[\]{}()<>!@#$%^&*+=|\\:;\"',./?\-_`~]")

# Diacritics to strip per language (keep only those meaningful for comparison)
_STRIP_DIACRITICS: dict[str, set[str]] = {
    "es": {
        "\u0330",  # creaky voice (tilde below)
        "\u0324",  # breathy voice (diaeresis below)
        "\u032A",  # dental (bridge below) — sometimes irrelevant noise
    },
    "en": {
        "\u0330",
        "\u0324",
    },
    "fr": {
        "\u0330",
        "\u0324",
    },
    "de": {
        "\u0330",
        "\u0324",
    },
}

# Common Allosaurus substitutions to normalize.
# NOTE: do NOT add 'r' here — it is handled exclusively per-language in
# _LANG_FIXES so that EN gets /ɹ/, ES gets /ɾ/, FR/DE get /ʁ/, etc.
_ALLOSAURUS_FIXES: dict[str, str] = {
    "g": "ɡ",       # Latin g → IPA ɡ (U+0261)
    "ɡ̥": "k",       # Devoiced ɡ → k
    "'": "ˈ",       # ASCII apostrophe → IPA stress
    ":": "ː",       # ASCII colon → IPA length
}

_LANG_FIXES: dict[str, dict[str, str]] = {
    "es": {
        "r": "ɾ",   # ASCII r (Allosaurus) → IPA tap ɾ — normalización ASCII→IPA, no alófono
        "ɹ": "ɾ",   # English approx → Spanish tap
        "ʁ": "r",   # French r → Spanish trill
    },
    "en": {
        "r": "ɹ",   # English r = approximant
        "ɾ": "ɾ",   # Keep tap (flap in AmE)
    },
    "fr": {
        "r": "ʁ",   # French r = uvular
    },
    "de": {
        "r": "ʁ",   # German r = uvular (standard)
    },
}


def postprocess_tokens(
    tokens: List[Token],
    *,
    lang: Optional[str] = None,
    collapse_duplicates: bool = True,
    strip_artifacts: bool = True,
    apply_lang_fixes: bool = True,
) -> List[Token]:
    """Clean and normalize a list of IPA tokens from ASR output.

    Parameters
    ----------
    tokens : list[str]
        Raw IPA tokens from the ASR backend.
    lang : str, optional
        Target language code for language-specific normalization.
    collapse_duplicates : bool
        Merge consecutive identical phonemes (common ASR artifact).
    strip_artifacts : bool
        Remove non-IPA characters like digits and punctuation.
    apply_lang_fixes : bool
        Apply language-specific phoneme mappings.

    Returns
    -------
    list[str]
        Cleaned token list.
    """
    result: List[Token] = []

    for token in tokens:
        cleaned = _clean_token(token, lang=lang, strip_artifacts=strip_artifacts, apply_fixes=apply_lang_fixes)
        if not cleaned:
            continue

        # Collapse consecutive duplicates
        if collapse_duplicates and result and result[-1] == cleaned:
            continue

        result.append(cleaned)

    return result


def _clean_token(
    token: Token,
    *,
    lang: Optional[str] = None,
    strip_artifacts: bool = True,
    apply_fixes: bool = True,
) -> Optional[Token]:
    """Clean a single IPA token."""
    if not token or not token.strip():
        return None

    t = token.strip()

    # Remove non-IPA artifacts
    if strip_artifacts:
        t = _NON_IPA_PATTERN.sub("", t)
        if not t:
            return None

    # Apply universal fixes
    if apply_fixes:
        for old, new in _ALLOSAURUS_FIXES.items():
            t = t.replace(old, new)

    # Apply language-specific fixes
    if apply_fixes and lang:
        lang_key = lang[:2].lower()
        fixes = _LANG_FIXES.get(lang_key, {})
        for old, new in fixes.items():
            t = t.replace(old, new)

    # Strip irrelevant diacritics for the target language
    if lang:
        lang_key = lang[:2].lower()
        strip_set = _STRIP_DIACRITICS.get(lang_key, set())
        if strip_set:
            t = "".join(ch for ch in t if ch not in strip_set)

    # Final validation: must contain at least one IPA-ish char
    if not t or all(unicodedata.category(c) == "Mn" for c in t):
        return None

    return t


def filter_silence_tokens(tokens: List[Token]) -> List[Token]:
    """Remove silence/pause markers and standalone suprasegmental markers."""
    # Silencio/pausa
    silence_markers = {"sil", "SIL", "<sil>", "sp", "SP", "<sp>", ""}
    # Marcadores suprasegmentales que espeak emite como tokens independientes.
    # Son irrelevantes para la comparaci\u00f3n fon\u00e9mica porque no son fonemas:
    # el acento afecta la s\u00edlaba, no el fonema en s\u00ed, y el comparador
    # trabaja a nivel de segmento.
    suprasegmental_markers = {"\u02c8", "\u02cc", "\u02d1", "\u203f", "|", "\u2016"}
    skip = silence_markers | suprasegmental_markers
    return [t for t in tokens if t not in skip]


__all__ = ["postprocess_tokens", "filter_silence_tokens"]
