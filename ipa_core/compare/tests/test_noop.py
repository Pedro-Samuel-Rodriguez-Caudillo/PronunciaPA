import pytest
from ipa_core.compare.noop import NoOpComparator

@pytest.mark.asyncio
async def test_noop_compare():
    comparator = NoOpComparator()
    ref = ["a", "b"]
    hyp = ["c", "d"]
    
    result = await comparator.compare(ref, hyp)
    
    assert result["per"] == 0.0
    assert result["ops"] == []
    assert result["alignment"] == []
    assert result["meta"]["comparator"] == "noop"
