import math

import pytest

from ..base import CompareResult
from ..levenshtein import INSERTION, MATCH, SUBSTITUTION, LevenshteinComparator


@pytest.fixture()
def comparator() -> LevenshteinComparator:
    return LevenshteinComparator()


def test_exact_match(comparator: LevenshteinComparator) -> None:
    result = comparator.compare("p a", "p a")

    assert math.isclose(result.per, 0.0)
    assert result.total_ref_tokens == 2
    assert result.matches == 2
    assert result.substitutions == 0
    assert result.insertions == 0
    assert result.deletions == 0
    assert result.ops == [
        (MATCH, "p", "p"),
        (MATCH, "a", "a"),
    ]
    assert result.per_class["p"].matches == 1
    assert result.per_class["a"].matches == 1


def test_single_substitution(comparator: LevenshteinComparator) -> None:
    result = comparator.compare("p a", "p o")

    assert math.isclose(result.per, 0.5)
    assert result.total_ref_tokens == 2
    assert result.matches == 1
    assert result.substitutions == 1
    assert result.ops == [
        (MATCH, "p", "p"),
        (SUBSTITUTION, "a", "o"),
    ]
    assert result.per_class["a"].substitutions == 1
    assert "p" in result.per_class and result.per_class["p"].matches == 1


def test_insertion(comparator: LevenshteinComparator) -> None:
    result = comparator.compare("p a", "p a o")

    assert math.isclose(result.per, 0.5)
    assert result.total_ref_tokens == 2
    assert result.insertions == 1
    assert result.ops[-1] == (INSERTION, "", "o")
    assert result.per_class["+o"].insertions == 1


def test_empty_reference(comparator: LevenshteinComparator) -> None:
    result = comparator.compare("", "p a")

    assert result.total_ref_tokens == 0
    assert math.isclose(result.per, 0.0)
    assert result.insertions == 2
    assert result.ops == [
        (INSERTION, "", "p"),
        (INSERTION, "", "a"),
    ]


def test_compare_result_repr(comparator: LevenshteinComparator) -> None:
    result = comparator.compare("p", "p")
    assert isinstance(result, CompareResult)
