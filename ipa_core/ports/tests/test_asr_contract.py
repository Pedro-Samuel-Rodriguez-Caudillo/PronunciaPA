import inspect
from ipa_core.ports.asr import ASRBackend

def test_asr_backend_is_async():
    """Verify that ASRBackend.transcribe is defined as an async method."""
    assert inspect.iscoroutinefunction(ASRBackend.transcribe), \
        "ASRBackend.transcribe must be an async method (coroutine function)"

def test_asr_backend_has_lifecycle():
    """Verify that ASRBackend includes setup and teardown."""
    assert hasattr(ASRBackend, 'setup'), "ASRBackend must have setup method"
    assert hasattr(ASRBackend, 'teardown'), "ASRBackend must have teardown method"
    
    # Verify they are async too
    assert inspect.iscoroutinefunction(ASRBackend.setup), "setup must be async"
    assert inspect.iscoroutinefunction(ASRBackend.teardown), "teardown must be async"
