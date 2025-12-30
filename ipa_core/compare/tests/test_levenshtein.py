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
        cmp = LevenshteinComparator()
        result = await cmp.compare(["a", "b", "c"], ["a", "x", "c", "d"])
        assert pytest.approx(result["per"]) == 2 / 3