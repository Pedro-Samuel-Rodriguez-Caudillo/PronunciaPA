"""Tests para OOVHandler — colapso y marcado de fonemas fuera de inventario."""
from __future__ import annotations

import pytest
from ipa_core.compare.oov_handler import (
    OOVHandler,
    OOVResult,
    OOVStats,
    UNKNOWN_TOKEN,
    apply_oov_handling,
)

# Inventario básico español
_INVENTORY = ["p", "b", "t", "d", "k", "g", "f", "s", "x", "m", "n", "l", "r", "ɾ",
               "j", "w", "a", "e", "i", "o", "u"]


class TestOOVHandlerInit:
    def test_valid_init(self):
        h = OOVHandler(_INVENTORY)
        assert h.collapse_threshold == OOVHandler.COLLAPSE_THRESHOLD_DEFAULT
        assert h.level == "phonemic"

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            OOVHandler(_INVENTORY, collapse_threshold=1.5)

    def test_empty_inventory(self):
        h = OOVHandler([])
        r = h.resolve("p")
        assert r.decision == "unknown"
        assert r.resolved == UNKNOWN_TOKEN


class TestResolveInInventory:
    def test_token_in_inventory(self):
        h = OOVHandler(_INVENTORY)
        r = h.resolve("p")
        assert r.decision == "in_inventory"
        assert r.resolved == "p"
        assert r.distance == 0.0

    def test_vowel_in_inventory(self):
        h = OOVHandler(_INVENTORY)
        r = h.resolve("a")
        assert r.decision == "in_inventory"
        assert r.resolved == "a"


class TestResolveCollapse:
    def test_close_phone_collapses(self):
        """ʃ (postalveolar fricative) debe colapsar a 's' (alveolar fricative)."""
        h = OOVHandler(_INVENTORY, collapse_threshold=0.3)
        r = h.resolve("ʃ")
        assert r.decision == "collapse"
        assert r.distance < 0.3
        assert r.resolved != UNKNOWN_TOKEN

    def test_voiced_alveolar_fricative_collapses(self):
        """z es muy parecida a s, debe colapsar."""
        h = OOVHandler(_INVENTORY, collapse_threshold=0.3)
        r = h.resolve("z")
        assert r.decision == "collapse"
        assert r.distance < 0.3

    def test_allophone_beta_collapses(self):
        """β (bilabial fricativo voiced) debería colapsar a b o m."""
        h = OOVHandler(_INVENTORY, collapse_threshold=0.3)
        r = h.resolve("β")
        assert r.decision == "collapse"
        assert r.distance < 0.3


class TestResolveUnknown:
    def test_very_distant_phone_marked_unknown(self):
        """Fonema sin parecido articulatorio → marcado como desconocido."""
        # Usar inventario mínimo sin fricativas
        tiny_inventory = ["a", "e", "i", "o", "u"]
        h = OOVHandler(tiny_inventory, collapse_threshold=0.3)
        r = h.resolve("ʀ")  # Uvular trill — muy distinto de vocales
        assert r.decision == "unknown"
        assert r.resolved == UNKNOWN_TOKEN

    def test_threshold_zero_all_unknown(self):
        """Con umbral 0, todo OOV es desconocido."""
        h = OOVHandler(_INVENTORY, collapse_threshold=0.0)
        r = h.resolve("ʃ")
        assert r.decision == "unknown"

    def test_threshold_one_all_collapse(self):
        """Con umbral 1.0, todo OOV se colapsa."""
        h = OOVHandler(_INVENTORY, collapse_threshold=1.0)
        r = h.resolve("ʃ")
        assert r.decision == "collapse"


class TestResolveSequence:
    def test_sequence_mixed(self):
        h = OOVHandler(_INVENTORY)
        results = h.resolve_sequence(["p", "ʃ", "a"])
        assert results[0].decision == "in_inventory"
        assert results[2].decision == "in_inventory"
        # ʃ puede colapsar o marcarse, pero debe haber resultado
        assert results[1].decision in ("collapse", "unknown")

    def test_filter_sequence_excludes_unknown(self):
        tiny = ["a", "e", "i", "o", "u"]
        h = OOVHandler(tiny, collapse_threshold=0.3)
        # Usar un consonante muy raro que no colapsará con vocales
        filtered = h.filter_sequence(["a", "ʀ", "e"], exclude_unknown=True)
        assert "?" not in filtered
        assert "a" in filtered
        assert "e" in filtered

    def test_filter_sequence_keeps_unknown_if_not_excluded(self):
        tiny = ["a", "e", "i"]
        h = OOVHandler(tiny, collapse_threshold=0.0)
        filtered = h.filter_sequence(["a", "ʃ", "i"], exclude_unknown=False)
        assert UNKNOWN_TOKEN in filtered


class TestNormalizePair:
    def test_both_in_inventory(self):
        h = OOVHandler(_INVENTORY)
        ref, hyp = h.normalize_pair(["p", "a"], ["b", "a"])
        assert ref == ["p", "a"]
        assert hyp == ["b", "a"]

    def test_oov_excluded_from_pair(self):
        tiny = ["a", "e", "i", "o", "u"]
        h = OOVHandler(tiny, collapse_threshold=0.0)
        ref, hyp = h.normalize_pair(["a", "ʃ", "e"], ["a", "ʒ", "e"])
        # ʃ y ʒ son OOV con threshold=0, se excluyen
        assert "?" not in ref
        assert "?" not in hyp


class TestStats:
    def test_stats_count(self):
        h = OOVHandler(_INVENTORY)
        h.resolve("p")   # in_inventory
        h.resolve("ʃ")   # collapse
        stats = h.stats
        assert stats.total == 2
        assert stats.in_inventory == 1

    def test_reset_stats(self):
        h = OOVHandler(_INVENTORY)
        h.resolve("p")
        h.reset_stats()
        assert h.stats.total == 0

    def test_stats_as_dict(self):
        h = OOVHandler(_INVENTORY)
        h.resolve("p")
        d = h.stats.as_dict()
        assert "total" in d
        assert "oov_rate" in d


class TestApplyOOVHandling:
    def test_convenience_function(self):
        ref_norm, hyp_norm, stats = apply_oov_handling(
            ["p", "a", "ʃ"],
            ["p", "a", "s"],
            _INVENTORY,
        )
        assert isinstance(ref_norm, list)
        assert isinstance(hyp_norm, list)
        assert isinstance(stats, OOVStats)

    def test_empty_sequences(self):
        ref_norm, hyp_norm, stats = apply_oov_handling([], [], _INVENTORY)
        assert ref_norm == []
        assert hyp_norm == []
        assert stats.total == 0


class TestFromInventoryDict:
    def test_from_dict_with_keys(self):
        inv_dict = {
            "inventory": {
                "consonants": ["p", "t", "k"],
                "vowels": ["a", "e", "i"],
            }
        }
        h = OOVHandler.from_inventory_dict(inv_dict)
        assert h.resolve("p").decision == "in_inventory"
        assert h.resolve("a").decision == "in_inventory"
