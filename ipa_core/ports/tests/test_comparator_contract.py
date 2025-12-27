import inspect
from ipa_core.ports.compare import Comparator

def test_comparator_is_async():
    """Verify that Comparator.compare is defined as an async method."""
    assert inspect.iscoroutinefunction(Comparator.compare), \
        "Comparator.compare must be an async method"

def test_comparator_has_lifecycle():
    """Verify that Comparator includes setup and teardown."""
    assert hasattr(Comparator, 'setup')
    assert hasattr(Comparator, 'teardown')
    
    assert inspect.iscoroutinefunction(Comparator.setup)
    assert inspect.iscoroutinefunction(Comparator.teardown)
