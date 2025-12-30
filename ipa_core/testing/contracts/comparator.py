"""Contract tests for Comparator plugins."""
from __future__ import annotations

import pytest
from ipa_core.ports.compare import Comparator


class ComparatorContract:
    """Base class for Comparator contract tests."""

    @pytest.fixture
    def comparator(self) -> Comparator:
        """Should return an instance of the comparator being tested."""
        raise NotImplementedError("Subclasses must implement the `comparator` fixture.")

    @pytest.mark.asyncio
    async def test_setup_teardown(self, comparator: Comparator):
        """Verify setup and teardown lifecycle."""
        await comparator.setup()
        await comparator.teardown()

    @pytest.mark.asyncio
    async def test_compare_structure(self, comparator: Comparator):
        """Verify that compare returns the expected structure."""
        await comparator.setup()
        try:
            result = await comparator.compare(["h", "o", "l", "a"], ["o", "l", "a"])
            
            assert isinstance(result, dict)
            assert "per" in result
            assert isinstance(result["per"], (int, float))
            assert 0.0 <= result["per"] <= 1.0
            
            if "ops" in result:
                assert isinstance(result["ops"], list)
                for op in result["ops"]:
                    assert "op" in op
                    assert op["op"] in ["eq", "sub", "ins", "del"]
            
            if "alignment" in result:
                assert isinstance(result["alignment"], list)
                for pair in result["alignment"]:
                    assert isinstance(pair, (list, tuple))
                    assert len(pair) == 2
        finally:
            await comparator.teardown()

    @pytest.mark.asyncio
    async def test_compare_identical(self, comparator: Comparator):
        """Verify that compare returns PER 0 for identical sequences."""
        await comparator.setup()
        try:
            result = await comparator.compare(["a", "b"], ["a", "b"])
            assert result["per"] == 0.0
        finally:
            await comparator.teardown()
