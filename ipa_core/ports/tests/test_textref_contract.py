import inspect
from ipa_core.ports.textref import TextRefProvider

def test_textref_is_async():
    """Verify that TextRefProvider.to_ipa is defined as an async method."""
    assert inspect.iscoroutinefunction(TextRefProvider.to_ipa), \
        "TextRefProvider.to_ipa must be an async method"

def test_textref_has_lifecycle():
    """Verify that TextRefProvider includes setup and teardown."""
    assert hasattr(TextRefProvider, 'setup'), "Must have setup"
    assert hasattr(TextRefProvider, 'teardown'), "Must have teardown"
    
    assert inspect.iscoroutinefunction(TextRefProvider.setup)
    assert inspect.iscoroutinefunction(TextRefProvider.teardown)
