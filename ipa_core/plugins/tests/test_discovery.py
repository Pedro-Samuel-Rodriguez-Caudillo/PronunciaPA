import unittest
from unittest.mock import patch, MagicMock
from ipa_core.plugins import discovery

class TestDiscovery(unittest.TestCase):
    def test_available_plugins_structure(self):
        """Ensure it returns the expected dictionary structure."""
        result = discovery.available_plugins()
        self.assertIsInstance(result, dict)
        for key in ("asr", "comparator", "preprocessor", "textref", "tts", "llm"):
            self.assertIn(key, result)
        for val in result.values():
            self.assertIsInstance(val, list)

    @patch("importlib.metadata.entry_points")
    def test_finds_external_plugins(self, mock_entry_points):
        """Should parse entry points with 'category.name' format."""
        
        # Mock EntryPoints
        # For Python 3.9, entry_points() returns a dict-like object
        
        ep1 = MagicMock()
        ep1.name = "asr.whisper"
        ep1.value = "pkg.module:WhisperASR"
        
        ep2 = MagicMock()
        ep2.name = "textref.my_g2p"
        ep2.value = "pkg.g2p:MyG2P"
        
        ep3 = MagicMock()
        ep3.name = "invalid_format" 
        ep3.value = "pkg:Bad"

        # Simulating the behavior of entry_points() returning a dict
        mock_eps = {
            "pronunciapa.plugins": [ep1, ep2, ep3]
        }
        mock_entry_points.return_value = mock_eps

        result = discovery.available_plugins()

        self.assertIn("whisper", result["asr"])
        self.assertIn("my_g2p", result["textref"])
        
        # Ensure invalid format didn't end up in random places
        for cat in result:
            self.assertNotIn("invalid_format", result[cat])
        
        # Verify it does not crash on missing group
        mock_entry_points.return_value = {}
        result_empty = discovery.available_plugins()
        self.assertEqual(result_empty["asr"], [])

    @patch("importlib.metadata.entry_points")
    def test_iter_plugin_entry_points(self, mock_entry_points):
        """Should yield (category, name, ep) tuples."""
        ep1 = MagicMock()
        ep1.name = "asr.whisper"
        
        mock_eps = {"pronunciapa.plugins": [ep1]}
        mock_entry_points.return_value = mock_eps
        
        results = list(discovery.iter_plugin_entry_points())
        self.assertEqual(len(results), 1)
        cat, name, ep = results[0]
        self.assertEqual(cat, "asr")
        self.assertEqual(name, "whisper")
        self.assertEqual(ep, ep1)
