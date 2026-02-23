"""Tests para CMUDictTextRef (CMU Pronouncing Dictionary → IPA)."""
from __future__ import annotations

import pytest

from ipa_core.errors import NotReadyError
from ipa_core.textref.cmu_dict import CMUDictTextRef, _arpabet_to_ipa_token


# ── Conversión ARPAbet → IPA ─────────────────────────────────────────────────

class TestArpabetToIpa:
    def test_consonantes_simples(self):
        assert _arpabet_to_ipa_token("B") == "b"
        assert _arpabet_to_ipa_token("D") == "d"
        assert _arpabet_to_ipa_token("G") == "ɡ"
        assert _arpabet_to_ipa_token("K") == "k"
        assert _arpabet_to_ipa_token("P") == "p"
        assert _arpabet_to_ipa_token("T") == "t"
        assert _arpabet_to_ipa_token("M") == "m"
        assert _arpabet_to_ipa_token("N") == "n"
        assert _arpabet_to_ipa_token("L") == "l"
        assert _arpabet_to_ipa_token("R") == "ɹ"

    def test_africadas(self):
        assert _arpabet_to_ipa_token("CH") == "tʃ"
        assert _arpabet_to_ipa_token("JH") == "dʒ"

    def test_fricativas(self):
        assert _arpabet_to_ipa_token("DH") == "ð"
        assert _arpabet_to_ipa_token("TH") == "θ"
        assert _arpabet_to_ipa_token("SH") == "ʃ"
        assert _arpabet_to_ipa_token("ZH") == "ʒ"
        assert _arpabet_to_ipa_token("HH") == "h"
        assert _arpabet_to_ipa_token("NG") == "ŋ"

    def test_vocales_con_stress(self):
        """El dígito de stress (0/1/2) se elimina antes del lookup."""
        assert _arpabet_to_ipa_token("AE1") == "æ"
        assert _arpabet_to_ipa_token("IY2") == "i"
        assert _arpabet_to_ipa_token("OW0") == "oʊ"
        assert _arpabet_to_ipa_token("UW1") == "u"
        assert _arpabet_to_ipa_token("AW2") == "aʊ"

    def test_schwa_vs_cara(self):
        """AH0 (átono) → ə; AH1/AH2 (tónico) → ʌ."""
        assert _arpabet_to_ipa_token("AH0") == "ə"
        assert _arpabet_to_ipa_token("AH1") == "ʌ"
        assert _arpabet_to_ipa_token("AH2") == "ʌ"

    def test_vocales_rhoticas(self):
        """ER0 (átono) → ɚ; ER1 (tónico) → ɝ."""
        assert _arpabet_to_ipa_token("ER0") == "ɚ"
        assert _arpabet_to_ipa_token("ER1") == "ɝ"

    def test_sin_stress_digit(self):
        """Sin dígito de stress también funciona."""
        assert _arpabet_to_ipa_token("AH") == "ʌ"
        assert _arpabet_to_ipa_token("IY") == "i"

    def test_desconocido_retorna_minusculas(self):
        """Fonema desconocido → lowercase del input."""
        assert _arpabet_to_ipa_token("XQ") == "xq"


# ── Lookup en diccionario ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lookup_palabra_conocida():
    provider = CMUDictTextRef()
    provider._cmudict = {"hello": [["HH", "AH0", "L", "OW1"]]}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("hello", lang="en")
    # HH→h, AH0→ə, L→l, OW1→oʊ
    assert result["tokens"] == ["h", "ə", "l", "oʊ"]
    assert result["meta"]["oov_count"] == 0
    assert result["meta"]["method"] == "cmudict"


@pytest.mark.asyncio
async def test_lookup_usa_primera_pronunciacion():
    """CMU Dict puede tener varias pronunciaciones; se usa la primera."""
    provider = CMUDictTextRef()
    provider._cmudict = {
        "either": [
            ["IY1", "DH", "ER0"],   # /ˈiːðɚ/ (pronunciación 1)
            ["AY1", "DH", "ER0"],   # /ˈaɪðɚ/ (pronunciación 2)
        ]
    }
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("either", lang="en")
    assert result["tokens"] == ["i", "ð", "ɚ"]


@pytest.mark.asyncio
async def test_multiples_palabras():
    provider = CMUDictTextRef(oov_fallback="skip")
    provider._cmudict = {
        "cat": [["K", "AE1", "T"]],
        "sat": [["S", "AE1", "T"]],
    }
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("cat sat", lang="en")
    assert result["tokens"] == ["k", "æ", "t", "s", "æ", "t"]
    assert result["meta"]["oov_count"] == 0


@pytest.mark.asyncio
async def test_normalizacion_mayusculas():
    """El lookup normaliza la palabra a minúsculas."""
    provider = CMUDictTextRef()
    provider._cmudict = {"hello": [["HH", "AH0", "L", "OW1"]]}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("Hello", lang="en")
    assert result["tokens"] == ["h", "ə", "l", "oʊ"]


# ── Manejo de OOV (Out-Of-Vocabulary) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_oov_grapheme_fallback():
    provider = CMUDictTextRef(oov_fallback="grapheme")
    provider._cmudict = {}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("xyz", lang="en")
    assert result["tokens"] == ["x", "y", "z"]
    assert result["meta"]["oov_count"] == 1
    assert "xyz" in result["meta"]["oov_words"]


@pytest.mark.asyncio
async def test_oov_skip_fallback():
    """OOV con skip: la palabra desconocida no aporta tokens."""
    provider = CMUDictTextRef(oov_fallback="skip")
    provider._cmudict = {"cat": [["K", "AE1", "T"]]}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("cat xyz", lang="en")
    assert result["tokens"] == ["k", "æ", "t"]
    assert result["meta"]["oov_count"] == 1


@pytest.mark.asyncio
async def test_oov_espeak_fallback():
    """OOV con espeak: delega al proveedor eSpeak inyectado."""
    class FakeEspeak:
        async def to_ipa(self, text, *, lang):
            return {"tokens": ["f", "e", "k"]}

    provider = CMUDictTextRef(oov_fallback="espeak")
    provider._cmudict = {}
    provider._espeak = FakeEspeak()
    provider._ready = True

    result = await provider.to_ipa("xyz", lang="en")
    assert result["tokens"] == ["f", "e", "k"]


# ── Soporte de dialectos ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_en_gb_acepta_ingles():
    """en-GB se trata como inglés para lookup en CMU Dict."""
    provider = CMUDictTextRef()
    provider._cmudict = {"cat": [["K", "AE1", "T"]]}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("cat", lang="en-gb")
    assert result["tokens"] == ["k", "æ", "t"]


@pytest.mark.asyncio
async def test_en_au_acepta_ingles():
    """en-AU se trata como inglés para lookup en CMU Dict."""
    provider = CMUDictTextRef()
    provider._cmudict = {"cat": [["K", "AE1", "T"]]}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("cat", lang="en-au")
    assert result["tokens"] == ["k", "æ", "t"]


@pytest.mark.asyncio
async def test_idioma_no_ingles_delega_a_espeak():
    """Para lang='es', delega a eSpeak (CMU Dict es solo inglés)."""
    class FakeEspeak:
        async def to_ipa(self, text, *, lang):
            return {"tokens": ["o", "l", "a"]}

    provider = CMUDictTextRef()
    provider._cmudict = {}
    provider._espeak = FakeEspeak()
    provider._ready = True

    result = await provider.to_ipa("hola", lang="es")
    assert result["tokens"] == ["o", "l", "a"]


@pytest.mark.asyncio
async def test_idioma_no_ingles_sin_espeak_retorna_grafemas():
    """Sin eSpeak, idioma no inglés → grafemas."""
    provider = CMUDictTextRef(oov_fallback="grapheme")
    provider._cmudict = {}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("hi", lang="de")
    assert isinstance(result["tokens"], list)


# ── Estado del proveedor ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_not_ready_lanza_error():
    provider = CMUDictTextRef()
    # No se llama setup()
    with pytest.raises(NotReadyError):
        await provider.to_ipa("hello", lang="en")


@pytest.mark.asyncio
async def test_texto_vacio():
    provider = CMUDictTextRef()
    provider._cmudict = {}
    provider._espeak = None
    provider._ready = True

    result = await provider.to_ipa("", lang="en")
    assert result["tokens"] == []
    assert result["meta"]["oov_count"] == 0
