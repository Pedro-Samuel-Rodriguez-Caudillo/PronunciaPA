"""Tests para MinimalPairGenerator y pares curados."""
from __future__ import annotations

import pytest
from ipa_core.packs.minimal_pairs import (
    MinimalPair,
    MinimalPairGenerator,
    _check_minimal_pair,
    get_curated_pairs,
)


# ---------------------------------------------------------------------------
# _check_minimal_pair
# ---------------------------------------------------------------------------

class TestCheckMinimalPair:
    def test_exact_one_diff(self):
        pair = _check_minimal_pair(
            "pata", ["p", "a", "t", "a"],
            "bata", ["b", "a", "t", "a"],
        )
        assert pair is not None
        assert pair.phoneme1 == "p"
        assert pair.phoneme2 == "b"
        assert pair.position == 0

    def test_no_diff_same_words(self):
        pair = _check_minimal_pair(
            "casa", ["k", "a", "s", "a"],
            "casa", ["k", "a", "s", "a"],
        )
        assert pair is None

    def test_two_diffs_not_minimal(self):
        pair = _check_minimal_pair(
            "pata", ["p", "a", "t", "a"],
            "beto", ["b", "e", "t", "o"],
        )
        assert pair is None

    def test_different_lengths_not_minimal(self):
        pair = _check_minimal_pair(
            "pero", ["p", "e", "ɾ", "o"],
            "perro", ["p", "e", "r", "r", "o"],
        )
        assert pair is None

    def test_vowel_contrast_coda(self):
        pair = _check_minimal_pair(
            "pesa", ["p", "e", "s", "a"],
            "pisa", ["p", "i", "s", "a"],
        )
        assert pair is not None
        assert pair.phoneme1 == "e"
        assert pair.phoneme2 == "i"
        assert pair.position == 1

    def test_rhotic_contrast(self):
        # "pero" /p e ɾ o/ vs "perro" /p e r r o/ — distinta longitud, no es par mínimo
        pair = _check_minimal_pair(
            "pero",  ["p", "e", "ɾ", "o"],
            "perro", ["p", "e", "r", "r", "o"],
        )
        assert pair is None

    def test_language_stored(self):
        pair = _check_minimal_pair(
            "pata", ["p", "a", "t", "a"],
            "bata", ["b", "a", "t", "a"],
            language="es-mx",
        )
        assert pair is not None
        assert pair.language == "es-mx"


# ---------------------------------------------------------------------------
# MinimalPair dataclass
# ---------------------------------------------------------------------------

class TestMinimalPair:
    def test_contrast_label(self):
        pair = MinimalPair("pata", "p a t a", "bata", "b a t a", "p", "b", 0)
        assert pair.contrast_label() == "/p/ vs /b/"

    def test_as_dict_keys(self):
        pair = MinimalPair("pata", "p a t a", "bata", "b a t a", "p", "b", 0,
                           language="es-mx", tags=["stop"])
        d = pair.as_dict()
        assert "word1" in d
        assert "word2" in d
        assert "ipa1" in d
        assert "ipa2" in d
        assert "phoneme1" in d
        assert "phoneme2" in d
        assert "contrast_label" in d
        assert "tags" in d

    def test_defaults(self):
        pair = MinimalPair("a", "a", "e", "e", "a", "e", 0)
        assert pair.difficulty == 1
        assert pair.language == "es"
        assert pair.tags == []


# ---------------------------------------------------------------------------
# MinimalPairGenerator desde léxico
# ---------------------------------------------------------------------------

_LEXICON = {
    "pata": ["p", "a", "t", "a"],
    "bata": ["b", "a", "t", "a"],
    "gata": ["g", "a", "t", "a"],
    "casa": ["k", "a", "s", "a"],
    "pasa": ["p", "a", "s", "a"],
    "masa": ["m", "a", "s", "a"],
    "tasa": ["t", "a", "s", "a"],
    "loco": ["l", "o", "k", "o"],
    "poco": ["p", "o", "k", "o"],
}


class TestMinimalPairGeneratorInit:
    def test_from_lexicon(self):
        gen = MinimalPairGenerator(_LEXICON, language="es-mx")
        assert gen.language == "es-mx"

    def test_from_lexicon_strings(self):
        lex_str = {"pata": "p a t a", "bata": "b a t a"}
        gen = MinimalPairGenerator.from_lexicon_strings(lex_str, language="es")
        assert gen.language == "es"


class TestBuildAllPairs:
    def test_finds_pata_bata(self):
        gen = MinimalPairGenerator(_LEXICON)
        pairs = list(gen.iter_pairs())
        words = {(p.word1, p.word2) for p in pairs}
        words_rev = {(p.word2, p.word1) for p in pairs}
        assert ("pata", "bata") in words or ("bata", "pata") in words_rev or \
               any(p for p in pairs if set([p.word1, p.word2]) == {"pata", "bata"})

    def test_no_false_pairs(self):
        """No debe generar pares con más de una diferencia."""
        gen = MinimalPairGenerator(_LEXICON)
        for pair in gen.iter_pairs():
            # Verificar que la diferencia sea exactamente 1
            t1 = pair.ipa1.split()
            t2 = pair.ipa2.split()
            diffs = sum(1 for a, b in zip(t1, t2) if a != b)
            assert diffs == 1, f"Par falso: {pair.word1}/{pair.word2} — {diffs} diferencias"
            assert len(t1) == len(t2)

    def test_cache_idempotent(self):
        gen = MinimalPairGenerator(_LEXICON)
        pairs1 = list(gen.iter_pairs())
        pairs2 = list(gen.iter_pairs())
        assert len(pairs1) == len(pairs2)


class TestFindPairsForPhoneme:
    def test_find_p(self):
        gen = MinimalPairGenerator(_LEXICON)
        pairs = gen.find_pairs_for_phoneme("p")
        assert len(pairs) > 0
        for p in pairs:
            assert p.phoneme1 == "p" or p.phoneme2 == "p"

    def test_unknown_phoneme_empty(self):
        gen = MinimalPairGenerator(_LEXICON)
        pairs = gen.find_pairs_for_phoneme("ʘ")  # click no presente
        assert pairs == []


class TestFindPairsForContrast:
    def test_p_b_contrast(self):
        gen = MinimalPairGenerator(_LEXICON)
        pairs = gen.find_pairs_for_contrast("p", "b")
        assert len(pairs) > 0
        for p in pairs:
            assert {p.phoneme1, p.phoneme2} == {"p", "b"}

    def test_symmetric(self):
        gen = MinimalPairGenerator(_LEXICON)
        pairs_pb = gen.find_pairs_for_contrast("p", "b")
        pairs_bp = gen.find_pairs_for_contrast("b", "p")
        assert len(pairs_pb) == len(pairs_bp)


class TestMaxPairs:
    def test_max_pairs_respected(self):
        gen = MinimalPairGenerator(_LEXICON, max_pairs=2)
        pairs = list(gen.iter_pairs())
        assert len(pairs) <= 2


# ---------------------------------------------------------------------------
# Pares curados
# ---------------------------------------------------------------------------

class TestGetCuratedPairs:
    def test_es_mx_has_pairs(self):
        pairs = get_curated_pairs("es-mx")
        assert len(pairs) > 0

    def test_es_alias(self):
        pairs_es = get_curated_pairs("es")
        pairs_mx = get_curated_pairs("es-mx")
        assert len(pairs_es) == len(pairs_mx)

    def test_en_us_has_pairs(self):
        pairs = get_curated_pairs("en-us")
        assert len(pairs) > 0

    def test_unknown_language_empty(self):
        pairs = get_curated_pairs("xx-yy")
        assert pairs == []

    def test_rhotic_pair_present_es_mx(self):
        """El contraste r/ɾ debe estar en los pares curados de es-mx."""
        pairs = get_curated_pairs("es-mx")
        rhotic = [p for p in pairs if {p.phoneme1, p.phoneme2} == {"r", "ɾ"}]
        assert len(rhotic) > 0, "No hay pares r/ɾ en es-mx"

    def test_pairs_have_valid_ipa(self):
        pairs = get_curated_pairs("es-mx")
        for p in pairs:
            assert p.ipa1.strip()
            assert p.ipa2.strip()

    def test_curated_pairs_by_difficulty(self):
        gen = MinimalPairGenerator({}, language="es-mx")
        diff3 = gen.find_pairs_by_difficulty(3)
        assert len(diff3) > 0  # Los pares r/ɾ son dificultad 3

    def test_curated_pairs_by_tag(self):
        gen = MinimalPairGenerator({}, language="es-mx")
        rhotic = gen.find_pairs_by_tag("rhotic")
        assert len(rhotic) > 0


# ---------------------------------------------------------------------------
# Integración: from_lexicon_strings + find
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_workflow(self):
        lex = {"pata": "p a t a", "bata": "b a t a", "kata": "k a t a"}
        gen = MinimalPairGenerator.from_lexicon_strings(lex, language="es-mx")
        pairs = gen.find_pairs_for_contrast("p", "b")
        assert len(pairs) == 1
        assert pairs[0].word1 in ("pata", "bata")
        assert pairs[0].word2 in ("pata", "bata")

    def test_empty_lexicon(self):
        gen = MinimalPairGenerator({}, language="es")
        assert list(gen.iter_pairs()) == []
