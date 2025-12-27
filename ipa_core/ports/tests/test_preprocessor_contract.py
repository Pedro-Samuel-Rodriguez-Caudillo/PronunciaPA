import inspect
from ipa_core.ports.preprocess import Preprocessor

def test_preprocessor_is_async():
    """Verify that Preprocessor methods are async."""
    assert inspect.iscoroutinefunction(Preprocessor.process_audio), \
        "Preprocessor.process_audio must be an async method"
    assert inspect.iscoroutinefunction(Preprocessor.normalize_tokens), \
        "Preprocessor.normalize_tokens must be an async method"

def test_preprocessor_has_lifecycle():
    """Verify that Preprocessor includes setup and teardown."""
    assert hasattr(Preprocessor, 'setup')
    assert hasattr(Preprocessor, 'teardown')
    
    assert inspect.iscoroutinefunction(Preprocessor.setup)
    assert inspect.iscoroutinefunction(Preprocessor.teardown)
