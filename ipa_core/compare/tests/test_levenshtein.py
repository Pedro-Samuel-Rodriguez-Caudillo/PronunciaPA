"""Tests para `LevenshteinComparator`."""
from __future__ import annotations

import pytest

from ipa_core.compare.levenshtein import LevenshteinComparator


import pytest
from ipa_core.compare.levenshtein import LevenshteinComparator

@pytest.mark.asyncio
async def test_compare_exact_match() -> None:
    cmp = LevenshteinComparator()

    result = await cmp.compare(["a", "b"], ["a", "b"])

    assert result["per"] == 0.0

@pytest.mark.asyncio
async def test_compare_counts_ops() -> None:
    cmp = LevenshteinComparator()

    result = await cmp.compare(["a", "b", "c"], ["a", "x", "c", "d"])

    assert pytest.approx(result["per"]) == 2 / 3


