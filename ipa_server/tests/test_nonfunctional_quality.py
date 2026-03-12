from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, Optional

import pytest
from httpx import ASGITransport, AsyncClient

from ipa_core.errors import ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.pipeline.runner import execute_pipeline
from ipa_server.kernel_provider import get_or_create_kernel, peek_kernel, teardown_kernel_singleton
from ipa_server.main import get_app
from ipa_server.routers import pipeline as pipeline_router
from ipa_core.types import ASRResult, AudioInput, CompareResult, CompareWeights, PreprocessorResult, TextRefResult, TokenSeq
from tests.utils.audio import write_sine_wave


class DummyIpaASR:
    output_type = "ipa"


class DummyKernel:
    def __init__(self, *, asr: Any | None = None) -> None:
        self.asr = asr or DummyIpaASR()
        self.textref = object()
        self.pre = object()
        self.comp = object()
        self.setup_called = False
        self.teardown_called = False

    async def setup(self) -> None:
        self.setup_called = True

    async def teardown(self) -> None:
        self.teardown_called = True


class PerfPreprocessor(BasePlugin):
    async def process_audio(self, audio: AudioInput, **kw: Any) -> PreprocessorResult:
        return {"audio": audio, "meta": {"audio_quality": {"passed": True, "issues": []}}}

    async def normalize_tokens(self, tokens: TokenSeq, **kw: Any) -> PreprocessorResult:
        return {"tokens": list(tokens)}


class PerfASR(BasePlugin):
    output_type: Literal["ipa", "text", "none"] = "ipa"

    async def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw: Any) -> ASRResult:
        return {"tokens": ["p", "a", "t", "o"], "meta": {"lang": lang, "backend": "perf_asr", "model": "test-double"}}


class PerfTextRef(BasePlugin):
    async def to_ipa(self, text: str, *, lang: Optional[str] = None, **kw: Any) -> TextRefResult:
        return {"tokens": ["p", "a", "t", "o"], "meta": {"lang": lang}}


class PerfComparator(BasePlugin):
    async def compare(self, ref: TokenSeq, hyp: TokenSeq, *, weights: Optional[CompareWeights] = None, **kw: Any) -> CompareResult:
        return {
            "per": 0.0,
            "ops": [{"op": "eq", "ref": "p", "hyp": "p"}],
            "alignment": [("p", "p")],
            "meta": {"distance": 0.0},
        }


@pytest.fixture
async def api_client():
    app = get_app()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield client, app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def wav_bytes(tmp_path: Path) -> bytes:
    wav_path = tmp_path / "sample.wav"
    write_sine_wave(wav_path, seconds=0.8)
    return wav_path.read_bytes()


@pytest.mark.performance
async def test_health_endpoint_responds_within_500ms(api_client) -> None:
    """QA-02 case 1=B: /health debe responder en menos de 500 ms en modo stub."""
    client, _app = api_client

    started = time.perf_counter()
    response = await client.get("/health")
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 500


@pytest.mark.performance
async def test_execute_pipeline_finishes_under_two_seconds_in_stub_mode() -> None:
    """QA-01 case 2=B: execute_pipeline en stub mode debe terminar en menos de 2 s."""
    started = time.perf_counter()
    result = await execute_pipeline(
        PerfPreprocessor(),
        PerfASR(),
        PerfTextRef(),
        PerfComparator(),
        audio={"path": "sample.wav", "sample_rate": 16000, "channels": 1},
        text="pato",
        lang="es",
    )
    elapsed_s = time.perf_counter() - started

    assert result.score == 100.0
    assert elapsed_s < 2.0


@pytest.mark.security
async def test_feedback_rejects_client_supplied_external_prompt_path_before_fs_use(api_client, wav_bytes: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """QA-03 case 3=A: rutas arbitrarias del cliente deben rechazarse antes de usar el FS."""
    client, _app = api_client
    external_prompt = tmp_path / "external_prompt.md"
    external_prompt.write_text("forbidden external prompt", encoding="utf-8")
    analyze_called = False

    async def fake_get_or_create_kernel():
        return SimpleNamespace(asr=DummyIpaASR())

    async def fake_analyze(self, *args: Any, **kwargs: Any):
        nonlocal analyze_called
        analyze_called = True
        return {
            "report": {
                "target_text": "pato",
                "target_ipa": "p a t o",
                "observed_ipa": "p a t o",
                "metrics": {},
                "ops": [],
                "alignment": [],
                "lang": "es",
                "meta": {},
            },
            "compare": {
                "per": 0.0,
                "score": 100.0,
                "mode": "objective",
                "evaluation_level": "phonemic",
                "ipa": "p a t o",
                "target_ipa": "p a t o",
                "tokens": ["p", "a", "t", "o"],
                "ops": [],
                "alignment": [],
                "meta": {},
            },
            "feedback": {"summary": "ok"},
        }

    monkeypatch.setattr(pipeline_router, "get_or_create_kernel", fake_get_or_create_kernel)
    monkeypatch.setattr("ipa_server.routers.pipeline.FeedbackService.analyze", fake_analyze)

    response = await client.post(
        "/v1/feedback",
        data={
            "text": "pato",
            "lang": "es",
            "prompt_path": str(external_prompt),
        },
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code in (400, 422)
    assert analyze_called is False


@pytest.mark.security
async def test_compare_empty_audio_returns_descriptive_validation_without_traceback(api_client, monkeypatch: pytest.MonkeyPatch) -> None:
    """QA-04 case 4=A: audio vacio debe producir error descriptivo, no traceback interno."""
    client, app = api_client
    kernel = DummyKernel()

    async def fake_compare_file_detail(self, path: str, *args: Any, **kwargs: Any):
        if Path(path).stat().st_size == 0:
            raise ValidationError("Archivo de audio vacío")
        raise AssertionError("El archivo de prueba debía estar vacío")

    monkeypatch.setattr("ipa_server.routers.pipeline.ComparisonService.compare_file_detail", fake_compare_file_detail)
    app.dependency_overrides[pipeline_router._get_kernel] = lambda: kernel

    response = await client.post(
        "/v1/compare",
        data={"text": "pato", "lang": "es"},
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code in (400, 422)
    assert "Archivo de audio vacío" in response.json()["detail"]
    assert "Traceback" not in response.text


@pytest.mark.reliability
async def test_kernel_singleton_survives_three_create_destroy_cycles() -> None:
    """QA-05 case 5=A: crear/destruir kernel 3 veces seguidas no debe fallar."""
    await teardown_kernel_singleton()

    for _ in range(3):
        kernel = await get_or_create_kernel()
        assert kernel is not None
        assert peek_kernel() is kernel
        await teardown_kernel_singleton()
        assert peek_kernel() is None


@pytest.mark.reliability
async def test_missing_plugin_returns_clear_client_error(api_client, wav_bytes: bytes) -> None:
    """QA-08 case 6=A: plugin inexistente debe retornar error claro para el cliente."""
    client, app = api_client
    kernel = DummyKernel()
    app.dependency_overrides[pipeline_router._get_kernel] = lambda: kernel

    response = await client.post(
        "/v1/transcribe",
        data={"lang": "es", "backend": "missing_backend_xyz"},
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["type"] == "plugin_not_found"
    assert "missing_backend_xyz" in response.json()["detail"]
