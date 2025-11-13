"""Tests para `LevenshteinComparator`."""
from __future__ import annotations

import pytest

from ipa_core.compare.levenshtein import LevenshteinComparator


def test_compare_exact_match() -> None:
    cmp = LevenshteinComparator()

    result = cmp.compare(["a", "b"], ["a", "b"])

    assert result["per"] == 0.0
    assert all(op["op"] == "eq" for op in result["ops"])


def test_compare_counts_ops() -> None:
    cmp = LevenshteinComparator()

    result = cmp.compare(["a", "b", "c"], ["a", "x", "c", "d"])

    assert pytest.approx(result["per"]) == 2 / 3
    assert [op["op"] for op in result["ops"]] == ["eq", "sub", "eq", "ins"]
    assert result["alignment"][-1] == (None, "d")
