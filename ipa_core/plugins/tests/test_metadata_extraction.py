import unittest
from unittest.mock import patch, MagicMock
from ipa_core.plugins import discovery

class TestMetadataExtraction(unittest.TestCase):
    @patch("importlib.metadata.metadata")
    @patch("ipa_core.plugins.discovery.iter_plugin_entry_points")
    def test_extract_plugin_metadata(self, mock_iter, mock_metadata):
        """Should extract version, author, and description for a plugin."""
        ep = MagicMock()
        ep.name = "asr.test_plugin"
        # In real life ep.dist is available in newer python, 
        # but let's assume we use importlib.metadata directly on the package if possible
        # or use ep.module (if it points to the package)
        
        # Simulating that ep.value is something like 'my_plugin.asr:MyASR'
        # so the package name is 'my_plugin'
        ep.value = "my_plugin.asr:MyASR"
        
        mock_iter.return_value = [("asr", "test_plugin", ep)]
        
        # Mocking importlib.metadata.metadata for 'my_plugin'
        meta = MagicMock()
        meta.get.side_effect = lambda x, default=None: {
            "Version": "1.2.3",
            "Author": "Test Author",
            "Summary": "A test plugin description"
        }.get(x, default)
        mock_metadata.return_value = meta
        
        # New function we want to implement
        details = discovery.get_plugin_details("asr", "test_plugin")
        
        self.assertEqual(details["version"], "1.2.3")
        self.assertEqual(details["author"], "Test Author")
        self.assertEqual(details["description"], "A test plugin description")

    @patch("importlib.metadata.metadata")
    def test_get_metadata_by_package(self, mock_metadata):
        """Internal helper to get metadata from package name."""
        meta = MagicMock()
        meta.get.side_effect = lambda x, default=None: {
            "Version": "1.0.0",
            "Author": "Dev",
            "Summary": "Desc"
        }.get(x, default)
        mock_metadata.return_value = meta
        
        info = discovery.get_package_metadata("my_pkg")
        self.assertEqual(info["version"], "1.0.0")
        self.assertEqual(info["author"], "Dev")
        self.assertEqual(info["description"], "Desc")
