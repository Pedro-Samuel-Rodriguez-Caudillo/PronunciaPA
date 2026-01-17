"""Tests para `ComparisonService`."""
from __future__ import annotations

import pytest

from ipa_core.compare.levenshtein import LevenshteinComparator
from ipa_core.errors import ValidationError
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.services.comparison import ComparisonService
from tests.utils.audio import write_sine_wave


class RawTextASR:
    async def setup(self): pass
    async def teardown(self): pass
    async def transcribe(self, audio, *, lang=None, **kw):
        return {"raw_text": "hola"}


class TokenASR:
    async def setup(self): pass
    async def teardown(self): pass
    async def transcribe(self, audio, *, lang=None, **kw):
        return {"tokens": ["h", "o", "l", "a"]}


class FakeTextRef:
    async def setup(self): pass
    async def teardown(self): pass
    async def to_ipa(self, text: str, *, lang: str, **kw):
        return {"tokens": ["h", "o", "l", "a"]}


@pytest.mark.asyncio
async def test_comparison_service_detail_success(tmp_path):
    wav_path = write_sine_wave(tmp_path / "compare.wav")
    service = ComparisonService(
        preprocessor=BasicPreprocessor(),
        asr=TokenASR(),
        textref=FakeTextRef(),
        comparator=LevenshteinComparator(),
        default_lang="es",
    )
    payload = await service.compare_file_detail(wav_path, "hola", lang="es")
    assert payload.hyp_tokens == ["h", "o", "l", "a"]
    assert payload.ref_tokens == ["h", "o", "l", "a"]
    assert payload.result["per"] == 0.0


@pytest.mark.asyncio
async def test_comparison_service_detail_fallback(tmp_path):
    wav_path = write_sine_wave(tmp_path / "compare-fallback.wav")
    service = ComparisonService(
        preprocessor=BasicPreprocessor(),
        asr=RawTextASR(),
        textref=FakeTextRef(),
        comparator=LevenshteinComparator(),
        default_lang="es",
    )
    payload = await service.compare_file_detail(
        wav_path,
        "hola",
        lang="es",
        allow_textref_fallback=True,
    )
    assert payload.hyp_tokens == ["h", "o", "l", "a"]


@pytest.mark.asyncio
async def test_comparison_service_detail_strict(tmp_path):
    wav_path = write_sine_wave(tmp_path / "compare-strict.wav")
    service = ComparisonService(
        preprocessor=BasicPreprocessor(),
        asr=RawTextASR(),
        textref=FakeTextRef(),
        comparator=LevenshteinComparator(),
        default_lang="es",
    )
    with pytest.raises(ValidationError):
        await service.compare_file_detail(
            wav_path,
            "hola",
            lang="es",
            allow_textref_fallback=False,
        )
