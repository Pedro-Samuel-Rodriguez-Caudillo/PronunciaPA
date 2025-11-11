# Test: preprocessor basic normalization
from ipa_core.preprocessor_basic import BasicPreprocessor
print(BasicPreprocessor().normalize_tokens([" A ","b","  ","C"]))
