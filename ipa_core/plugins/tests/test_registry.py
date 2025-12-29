import unittest
from unittest.mock import patch, MagicMock
from ipa_core.plugins import registry

class TestRegistry(unittest.TestCase):
    def setUp(self):
        # Save original registry to restore? 
        # Since it is a global variable, we should be careful.
        # Ideally registry should be a class, but it is a module with global state.
        self.original_registry = {k: v.copy() for k, v in registry._REGISTRY.items()}
        # Clear for test
        registry._REGISTRY = {
            "asr": {},
            "textref": {},
            "comparator": {},
            "preprocessor": {},
        }

    def tearDown(self):
        registry._REGISTRY = self.original_registry

    def test_register_and_resolve(self):
        mock_factory = MagicMock(return_value="instance")
        registry.register("asr", "test", mock_factory)
        
        instance = registry.resolve("asr", "test")
        self.assertEqual(instance, "instance")
        mock_factory.assert_called_with({})

    @patch("ipa_core.plugins.discovery.iter_plugin_entry_points")
    def test_register_discovered_plugins(self, mock_iter):
        """Should load entry points and register them."""
        # Mock entry point loading a class
        mock_plugin_class = MagicMock()
        mock_plugin_class.return_value = "plugin_instance"
        
        mock_ep = MagicMock()
        mock_ep.load.return_value = mock_plugin_class
        
        mock_iter.return_value = [("asr", "discovered", mock_ep)]
        
        registry.register_discovered_plugins()
        
        # Verify it's registered
        instance = registry.resolve("asr", "discovered", {"foo": "bar"})
        self.assertEqual(instance, "plugin_instance")
        
        # Verify instantiation
        mock_plugin_class.assert_called_with({"foo": "bar"})
