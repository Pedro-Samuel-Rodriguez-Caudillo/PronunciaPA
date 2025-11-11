# Test: CLI stub presence
from ipa_core.api import cli
assert hasattr(cli,"cli_transcribe")
print("cli_transcribe present")
