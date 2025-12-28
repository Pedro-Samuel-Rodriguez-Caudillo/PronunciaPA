import pytest
from ipa_core.textref.simple import GraphemeTextRef

@pytest.mark.asyncio
async def test_grapheme_textref():
    provider = GraphemeTextRef()
    text = "HéLLo"
    
    result = await provider.to_ipa(text, lang="en")
    
    assert result["tokens"] == ["h", "é", "l", "l", "o"]
    assert result["meta"]["method"] == "grapheme"
    assert result["meta"]["lang"] == "en"

@pytest.mark.asyncio
async def test_grapheme_textref_normalization():
    provider = GraphemeTextRef()
    # NFD normalization check (e + combining acute)
    text = "e\u0301" 
    
    result = await provider.to_ipa(text, lang="es")
    
    # Expect NFC 'é' (\u00e9)
    assert result["tokens"] == ["\u00e9"]
