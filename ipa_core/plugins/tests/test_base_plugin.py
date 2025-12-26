"""Pruebas para BasePlugin.
"""
from __future__ import annotations
import pytest
from ipa_core.plugins.base import BasePlugin

class MockPlugin(BasePlugin):
    pass

@pytest.mark.anyio
async def test_base_plugin_lifecycle_defaults() -> None:
    """Verifica que setup y teardown existan y sean asíncronos por defecto."""
    plugin = MockPlugin()
    # No deberían lanzar error
    await plugin.setup()
    await plugin.teardown()

@pytest.mark.anyio
async def test_base_plugin_custom_lifecycle() -> None:
    """Verifica que se puedan sobreescribir."""
    class CustomPlugin(BasePlugin):
        def __init__(self):
            self.setup_called = False
            self.teardown_called = False
            
        async def setup(self) -> None:
            self.setup_called = True
            
        async def teardown(self) -> None:
            self.teardown_called = True
            
    plugin = CustomPlugin()
    await plugin.setup()
    assert plugin.setup_called is True
    await plugin.teardown()
    assert plugin.teardown_called is True
