"""Tests para `ComparisonService`."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from ipa_core.compare.levenshtein import LevenshteinComparator
from ipa_core.errors import ValidationError
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.phonology.representation import ComparisonResult, PhonologicalRepresentation
from ipa_core.services.comparison import ComparisonService
from tests.utils.audio import write_sine_wave


from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.textref import TextRefProvider

class RawTextASR(ASRBackend):
    async def setup(self): pass
    async def teardown(self): pass
    async def transcribe(self, audio, *, lang=None, **kw):
        return {"raw_text": "hola"}


class TokenASR(ASRBackend):
    async def setup(self): pass
    async def teardown(self): pass
    async def transcribe(self, audio, *, lang=None, **kw):
        # Usa fonemas válidos en español: /m a l/ (inventario universal)
        return {"tokens": ["m", "a", "l"]}


class FakeTextRef(TextRefProvider):
    async def setup(self): pass
    async def teardown(self): pass
    async def to_ipa(self, text: str, *, lang: str, **kw):
        return {"tokens": ["m", "a", "l"]}


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
    payload = await service.compare_file_detail(wav_path, "mal", lang="es")
    # Ambas rutas deben producir los mismos tokens y PER = 0
    assert payload.hyp_tokens == payload.ref_tokens
    assert payload.result["per"] == 0.0


@pytest.mark.asyncio
async def test_comparison_service_detail_rejects_raw_text_even_with_flag(tmp_path):
    wav_path = write_sine_wave(tmp_path / "compare-fallback.wav")
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
            "mal",
            lang="es",
            allow_textref_fallback=True,
        )


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


@pytest.mark.asyncio
async def test_comparison_service_delegates_to_execute_pipeline(tmp_path, monkeypatch):
    wav_path = write_sine_wave(tmp_path / "compare-delegate.wav")
    service = ComparisonService(
        preprocessor=BasicPreprocessor(),
        asr=TokenASR(),
        textref=FakeTextRef(),
        comparator=LevenshteinComparator(),
        default_lang="es",
    )

    fake_result = ComparisonResult(
        target=PhonologicalRepresentation.phonemic("mal"),
        observed=PhonologicalRepresentation.phonemic("mal"),
        mode="objective",
        evaluation_level="phonemic",
        distance=0.0,
        score=100.0,
        operations=[],
    )
    execute_mock = AsyncMock(return_value=fake_result)
    monkeypatch.setattr("ipa_core.services.comparison.execute_pipeline", execute_mock)

    payload = await service.compare_file_detail(wav_path, "mal", lang="es")

    execute_mock.assert_awaited_once()
    assert payload.hyp_tokens == ["m", "a", "l"]
    assert payload.ref_tokens == ["m", "a", "l"]
    assert payload.result["per"] == 0.0
