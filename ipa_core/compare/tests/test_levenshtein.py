"""Tests para `LevenshteinComparator`."""
from __future__ import annotations

import pytest
from ipa_core.compare.levenshtein import LevenshteinComparator
from ipa_core.testing.contracts.comparator import ComparatorContract


class TestLevenshteinComparator(ComparatorContract):
    
    @pytest.fixture
    def comparator(self):
        return LevenshteinComparator()

    @pytest.mark.asyncio
    async def test_compare_exact_match_specific(self) -> None:
        cmp = LevenshteinComparator()
        result = await cmp.compare(["a", "b"], ["a", "b"])
        assert result["per"] == 0.0

        @pytest.mark.asyncio
        async def test_compare_counts_ops(self) -> None:
            # Without articulatory weights, PER = 2/3 (1 substitution + 1 insertion)
            cmp_basic = LevenshteinComparator(use_articulatory=False)
            result_basic = await cmp_basic.compare(["a", "b", "c"], ["a", "x", "c", "d"])
            assert pytest.approx(result_basic["per"]) == 2 / 3
    
            # With articulatory weights, PER < 2/3 because b->x substitution is weighted
            cmp = LevenshteinComparator(use_articulatory=True)
            result = await cmp.compare(["a", "b", "c"], ["a", "x", "c", "d"])
            assert 0.0 < result["per"] < 2 / 3
    