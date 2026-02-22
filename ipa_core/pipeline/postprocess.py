"""Post-processing filters for ASR output.

Cleans up raw IPA transcriptions from Allosaurus and other backends
to improve comparison accuracy. Filters include:
- Removing diacritics not relevant for the target language
- Collapsing duplicate consecutive phonemes
- Filtering non-IPA artifacts (numbers, punctuation, etc.)
- Normalizing common Allosaurus quirks per language
- Normalizing phonetic allophones to phonemic form for fair comparison
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

_NON_IPA_PATTERN = re.compile(r"[0-9\[\]{}()<>!@#$%^&*+=|\\;\"',./?\-_`~]")

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

# Common Allosaurus substitutions to normalize (APPLIED BEFORE strip_artifacts).
# NOTE: do NOT add 'r' here — it is handled exclusively per-language in
# _LANG_FIXES so that EN gets /ɹ/, ES gets /ɾ/, FR/DE get /ʁ/, etc.
# NOTE: ':' is removed from _NON_IPA_PATTERN so it reaches these fixes.
_ALLOSAURUS_FIXES: dict[str, str] = {
    "g": "ɡ",       # Latin g → IPA ɡ (U+0261)
    "ɡ̥": "k",       # Devoiced ɡ → k
    "'": "ˈ",       # ASCII apostrophe → IPA stress (filtered later as suprasegmental)
    ":": "ː",       # ASCII colon → IPA length mark (filtered as standalone suprasegmental)
}

# Language-specific phoneme normalization.
# These mappings collapse PHONETIC allophones to their PHONEMIC form so that
# ASR output (which may produce allophones from acoustic confusion) and TextRef
# output (eSpeak --ipa=3 which always produces phonetic IPA) both arrive at
# the same canonical phonemic representation before comparison.
#
# Without this, a correctly pronounced Spanish /b/ between vowels yields:
#   ASR (Allosaurus/spa):  "b"   (stop phoneme — constrained by lang inventory)
#   TextRef (eSpeak/es):   "β"   (lenited fricative allophone)
#   Result:                MISMATCH even for perfect pronunciation  ← BUG
#
# With this normalization applied to BOTH paths, both yield "b" and the
# comparison is fair.
_LANG_FIXES: dict[str, dict[str, str]] = {
    "es": {
        # ── r variants ──────────────────────────────────────────────────
        "r": "ɾ",   # ASCII r (Allosaurus quirk) → IPA tap ɾ
        "ɹ": "ɾ",   # English approximant → Spanish tap (cross-lingual confusion)
        "ʁ": "r",   # French/German uvular → Spanish trill
        # ── Obstruent allophones → phonemes (lenición española) ────────
        # eSpeak --ipa=3 produces the PHONETIC form (lenited fricative);
        # Allosaurus with spa inventory produces the PHONEMIC form (stop).
        # Normalizing both to the phoneme ensures fair comparison.
        "β": "b",   # [β] fricative allophone of /b/ → phoneme /b/
        "ð": "d",   # [ð] fricative allophone of /d/ → phoneme /d/
        "ɣ": "ɡ",   # [ɣ] fricative allophone of /g/ → phoneme /ɡ/
        "ʝ": "j",   # [ʝ] fricative allophone of /y/ → approximant /j/
    },
    "en": {
        "r": "ɹ",   # ASCII r → English approximant (standard AmE/BrE)
        "ɾ": "ɾ",   # Keep flap (intervocalic t/d in AmE: "butter" → [ˈbʌɾɚ])
        "ɨ": "ɪ",   # Close central → near-close front (Allosaurus confusion)
    },
    "fr": {
        "r": "ʁ",   # French uvular fricative/trill
        "ʀ": "ʁ",   # Uvular trill → uvular fricative (standard written IPA)
    },
    "de": {
        "r": "ʁ",   # German standard r (uvular in most dialects)
        "ʀ": "ʁ",   # Uvular trill → uvular fricative
    },
    "pt": {
        # European Portuguese uses different allophones than Brazilian
        "r": "ɾ",   # Default: Brazilian Portuguese tap (most common variant)
        "β": "b",   # Portuguese lenition of /b/ → phoneme /b/
        "ð": "d",   # Portuguese lenition of /d/ → phoneme /d/
        "ɣ": "ɡ",   # Portuguese lenition of /g/ → phoneme /ɡ/
        "ʁ": "ʁ",   # Keep for EP (European Portuguese coda r)
    },
    "it": {
        "r": "r",   # Italian alveolar trill — keep as-is
    },
    "ca": {
        # Catalan shares lenition patterns with Spanish
        "β": "b",
        "ð": "d",
        "ɣ": "ɡ",
        "r": "ɾ",
    },
    "gl": {
        # Galician similar to Portuguese/Spanish
        "β": "b",
        "ð": "d",
        "ɣ": "ɡ",
        "r": "ɾ",
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
        Apply language-specific phoneme mappings (including allophone →
        phoneme normalization). Should be True for BOTH ASR and TextRef
        paths to ensure a common phonemic reference for comparison.

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
    """Clean a single IPA token.

    Order of operations (critical for correctness):
    1. Apply _ALLOSAURUS_FIXES first — converts ':' → 'ː' and "'" → 'ˈ'
       BEFORE strip_artifacts would discard them as punctuation.
    2. Strip non-IPA artifacts.
    3. Apply language-specific allophone → phoneme fixes.
    4. Strip irrelevant diacritics for the target language.
    """
    if not token or not token.strip():
        return None

    t = token.strip()

    # ── Step 1: Apply universal backend-quirk fixes FIRST ────────────
    # IMPORTANT: must run before strip_artifacts or ':' and "'" get discarded.
    if apply_fixes:
        for old, new in _ALLOSAURUS_FIXES.items():
            t = t.replace(old, new)

    # ── Step 2: Remove non-IPA artifacts ─────────────────────────────
    if strip_artifacts:
        t = _NON_IPA_PATTERN.sub("", t)
        if not t:
            return None

    # ── Step 3: Apply language-specific allophone → phoneme mapping ───
    if apply_fixes and lang:
        lang_key = lang[:2].lower()
        fixes = _LANG_FIXES.get(lang_key, {})
        for old, new in fixes.items():
            t = t.replace(old, new)

    # ── Step 4: Strip irrelevant diacritics for the target language ───
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
    """Remove silence/pause markers and standalone suprasegmental markers.

    Suprasegmental markers are filtered when they appear as *standalone*
    tokens (as eSpeak emits them). When embedded in a token (e.g. "aː"
    for a long vowel), they are preserved — the comparison at phoneme
    level then handles them via the _LANG_FIXES normalization.
    """
    # Silencio/pausa
    silence_markers = {"sil", "SIL", "<sil>", "sp", "SP", "<sp>", ""}
    # Marcadores suprasegmentales que espeak emite como tokens independientes.
    # Son irrelevantes para la comparación fonémica porque no son fonemas:
    # el acento afecta la sílaba, no el fonema en sí, y el comparador
    # trabaja a nivel de segmento.
    suprasegmental_markers = {
        "\u02c8",   # ˈ primary stress
        "\u02cc",   # ˌ secondary stress
        "\u02d0",   # ː length mark (standalone — eSpeak/Allosaurus artifact)
        "\u02d1",   # ˑ half-length
        "\u203f",   # ‿ linking/undertie
        "|",        # minor break
        "\u2016",   # ‖ major break
    }
    skip = silence_markers | suprasegmental_markers
    return [t for t in tokens if t not in skip]


__all__ = ["postprocess_tokens", "filter_silence_tokens"]
