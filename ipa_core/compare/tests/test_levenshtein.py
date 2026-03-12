from __future__ import annotations

import pytest

from ipa_core.compare.levenshtein import LevenshteinComparator


@pytest.mark.unit
@pytest.mark.functional
async def test_per_is_zero_for_identical_pronunciation() -> None:
    """RF-02: pronunciacion identica debe tener PER 0.0."""
    comparator = LevenshteinComparator()

    result = await comparator.compare(["p", "a", "t", "o"], ["p", "a", "t", "o"])

    assert "per" in result
    assert result["per"] == 0.0


@pytest.mark.unit
@pytest.mark.functional
async def test_per_for_single_substitution_uses_articulatory_similarity_band() -> None:
    """RF-02: una sustitucion fonetica similar debe caer en banda [0.1, 0.3]."""
    comparator = LevenshteinComparator()

    result = await comparator.compare(["p", "a", "t", "o"], ["p", "a", "d", "o"])

    assert "per" in result
    assert 0.1 <= result["per"] <= 0.3


@pytest.mark.unit
@pytest.mark.functional
async def test_per_is_one_for_completely_different_sequences() -> None:
    """RF-02: secuencias totalmente diferentes deben dar PER 1.0."""
    comparator = LevenshteinComparator(use_articulatory=False)

    result = await comparator.compare(["a", "b", "c"], ["x", "y", "z"])

    assert "per" in result
    assert result["per"] == 1.0


@pytest.mark.unit
@pytest.mark.functional
async def test_compare_rejects_empty_reference_and_hypothesis() -> None:
    """RF-03: comparar secuencias vacias se considera entrada invalida."""
    comparator = LevenshteinComparator()

    with pytest.raises(ValueError):
        await comparator.compare([], [])


@pytest.mark.unit
@pytest.mark.functional
async def test_ops_include_eq_and_sub_in_order() -> None:
    """RF-03: ops debe incluir eq y sub en orden para alineacion interpretable."""
    comparator = LevenshteinComparator(use_articulatory=False)

    result = await comparator.compare(["a", "b"], ["a", "x"])

    assert "ops" in result
    assert result["ops"] == [
        {"op": "eq", "ref": "a", "hyp": "a"},
        {"op": "sub", "ref": "b", "hyp": "x"},
    ]
