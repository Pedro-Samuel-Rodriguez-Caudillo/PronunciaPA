import pytest
from ipa_core.plugins import registry

class BadPlugin:
    """Doesn't implement anything."""
    def __init__(self, params):
        pass

class GoodASR:
    """Implements ASRBackend Protocol."""
    def __init__(self, params):
        pass
    async def setup(self): pass
    async def teardown(self): pass
    async def transcribe(self, audio, *, lang=None, **kw):
        return {"tokens": [], "ipa": "", "meta": {}}

def test_validate_plugin_asr():
    # Should be valid
    is_valid, errors = registry.validate_plugin("asr", GoodASR)
    assert is_valid
    assert not errors

    # Should be invalid
    is_valid, errors = registry.validate_plugin("asr", BadPlugin)
    assert not is_valid
    assert len(errors) > 0
    assert any("transcribe" in err for err in errors)

def test_validate_plugin_invalid_category():
    with pytest.raises(ValueError):
        registry.validate_plugin("invalid", GoodASR)
