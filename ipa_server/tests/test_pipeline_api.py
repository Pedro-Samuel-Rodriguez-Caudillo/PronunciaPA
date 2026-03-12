from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from httpx import ASGITransport, AsyncClient

from ipa_core.errors import ValidationError
from ipa_server.main import get_app
from ipa_server.routers import pipeline as pipeline_router
from tests.utils.audio import write_sine_wave


class DummyIpaASR:
    output_type = "ipa"


class DummyTextASR:
    output_type = "text"


class DummyKernel:
    def __init__(self, *, asr: Any | None = None, textref: Any | None = None, pre: Any | None = None, comp: Any | None = None) -> None:
        self.asr = asr or DummyIpaASR()
        self.textref = textref or object()
        self.pre = pre or object()
        self.comp = comp or object()
        self.setup_called = False
        self.teardown_called = False

    async def setup(self) -> None:
        self.setup_called = True

    async def teardown(self) -> None:
        self.teardown_called = True


class DummyQuickPreprocessor:
    async def process_audio(self, audio: dict[str, Any]) -> dict[str, Any]:
        return {"audio": audio, "meta": {}}


class DummyQuickASRNoTokens:
    output_type = "ipa"

    async def transcribe(self, audio: dict[str, Any], *, lang: Optional[str] = None, **kw: Any) -> dict[str, Any]:
        return {"tokens": [], "raw_text": "", "meta": {"lang": lang}}


class DummyQuickTextRef:
    async def to_ipa(self, text: str, *, lang: Optional[str] = None, **kw: Any) -> dict[str, Any]:
        return {"tokens": ["p", "a"], "meta": {"lang": lang}}


class DummyQuickComparator:
    async def compare(self, ref: list[str], hyp: list[str], **kw: Any) -> dict[str, Any]:
        return {"per": 0.0, "ops": [], "alignment": [], "meta": {}}


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


@pytest.mark.system
@pytest.mark.functional
async def test_transcribe_returns_transcription_response_schema(api_client, wav_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-07 case 1=A: /v1/transcribe responde 200 con schema TranscriptionResponse completo."""
    client, app = api_client
    kernel = DummyKernel()

    async def fake_transcribe_file(self, path: str, *, lang: Optional[str] = None, user_id: Optional[str] = None):
        return SimpleNamespace(ipa="h o l a", tokens=["h", "o", "l", "a"], meta={"backend": "test_ipa", "lang": lang})

    monkeypatch.setattr("ipa_server.routers.pipeline.TranscriptionService.transcribe_file", fake_transcribe_file)
    app.dependency_overrides[pipeline_router._get_kernel] = lambda: kernel

    response = await client.post(
        "/v1/transcribe",
        data={"lang": "es"},
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ipa"] == "h o l a"
    assert body["tokens"] == ["h", "o", "l", "a"]
    assert body["lang"] == "es"
    assert body["meta"]["backend"] == "test_ipa"


@pytest.mark.system
@pytest.mark.usability
async def test_transcribe_rejects_non_ipa_backend_before_kernel_setup(api_client, wav_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    """QA-07 case 2=A: backend no IPA se rechaza de inmediato sin llamar setup()."""
    client, app = api_client
    kernel = DummyKernel()

    from ipa_core.plugins import registry

    registry.register("asr", "non_ipa_test", lambda _params: DummyTextASR())
    app.dependency_overrides[pipeline_router._get_kernel] = lambda: kernel

    response = await client.post(
        "/v1/transcribe",
        data={"lang": "es", "backend": "non_ipa_test"},
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 503
    assert "se requiere 'ipa'" in response.json()["detail"]
    assert kernel.setup_called is False


@pytest.mark.system
@pytest.mark.functional
async def test_compare_returns_score_and_alignment_payload(api_client, wav_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    """RF-07 case 3=A: /v1/compare devuelve 200 con score=80.0 y campos de comparacion."""
    client, app = api_client
    kernel = DummyKernel()

    class FakeComparePayload:
        def to_response(self) -> dict[str, Any]:
            return {
                "per": 0.2,
                "score": 80.0,
                "mode": "objective",
                "evaluation_level": "phonemic",
                "ipa": "p a d o",
                "target_ipa": "p a t o",
                "tokens": ["p", "a", "d", "o"],
                "ops": [{"op": "sub", "ref": "t", "hyp": "d"}],
                "alignment": [["t", "d"]],
                "meta": {"distance": 0.2},
            }

    async def fake_compare_file_detail(self, *args: Any, **kwargs: Any) -> FakeComparePayload:
        return FakeComparePayload()

    monkeypatch.setattr("ipa_server.routers.pipeline.ComparisonService.compare_file_detail", fake_compare_file_detail)
    app.dependency_overrides[pipeline_router._get_kernel] = lambda: kernel

    response = await client.post(
        "/v1/compare",
        data={"text": "pato", "lang": "es"},
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 80.0
    assert body["per"] == 0.2
    assert body["mode"] == "objective"
    assert body["evaluation_level"] == "phonemic"
    assert body["ops"] == [{"op": "sub", "ref": "t", "hyp": "d"}]
    assert body["alignment"] == [["t", "d"]]


@pytest.mark.system
@pytest.mark.usability
async def test_compare_rejects_invalid_audio_with_422_not_500(api_client, wav_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    """QA-07 case 4=A: audio invalido debe responder 422 con detail claro, nunca 500."""
    client, app = api_client
    kernel = DummyKernel()

    async def fake_compare_file_detail(self, *args: Any, **kwargs: Any):
        raise ValidationError("Audio corrupto o ilegible")

    monkeypatch.setattr("ipa_server.routers.pipeline.ComparisonService.compare_file_detail", fake_compare_file_detail)
    app.dependency_overrides[pipeline_router._get_kernel] = lambda: kernel

    response = await client.post(
        "/v1/compare",
        data={"text": "pato", "lang": "es"},
        files={"audio": ("broken.wav", b"not-a-real-wav", "audio/wav")},
    )

    assert response.status_code == 422
    assert "Audio corrupto o ilegible" in response.json()["detail"]


@pytest.mark.system
@pytest.mark.usability
async def test_quick_compare_returns_descriptive_validation_error_when_asr_has_no_tokens(api_client, wav_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    """QA-07 case 5=A: quick-compare sin tokens debe responder 422 con causa descriptiva."""
    client, _app = api_client
    kernel = SimpleNamespace(
        asr=DummyQuickASRNoTokens(),
        textref=DummyQuickTextRef(),
        comp=DummyQuickComparator(),
        pre=DummyQuickPreprocessor(),
    )

    async def fake_get_or_create_kernel():
        return kernel

    monkeypatch.setattr(pipeline_router, "get_or_create_kernel", fake_get_or_create_kernel)

    response = await client.post(
        "/v1/quick-compare",
        data={"text": "pa", "lang": "es"},
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 422
    assert "ASR no devolvio tokens IPA" in response.json()["detail"] or "ASR no devolvió tokens IPA" in response.json()["detail"]


@pytest.mark.system
@pytest.mark.usability
async def test_feedback_rejects_missing_prompt_path_immediately(api_client, wav_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    """QA-07 case 6=A: prompt_path inexistente debe rechazarse de forma descriptiva e inmediata."""
    client, _app = api_client
    kernel = SimpleNamespace(asr=DummyIpaASR())

    async def fake_get_or_create_kernel():
        return kernel

    monkeypatch.setattr(pipeline_router, "get_or_create_kernel", fake_get_or_create_kernel)

    response = await client.post(
        "/v1/feedback",
        data={
            "text": "pato",
            "lang": "es",
            "prompt_path": str(Path("C:/does/not/exist/prompt.md")),
        },
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 422
    assert "Prompt file not found" in response.json()["detail"]


@pytest.mark.system
@pytest.mark.functional
async def test_compare_forwards_adaptation_policy_flags(api_client, wav_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    """compare debe propagar force_phonetic y allow_quality_downgrade al servicio."""
    client, app = api_client
    kernel = DummyKernel()
    captured_kwargs: dict[str, Any] = {}

    class FakeComparePayload:
        def to_response(self) -> dict[str, Any]:
            return {
                "per": 0.0,
                "score": 100.0,
                "mode": "phonetic",
                "evaluation_level": "phonetic",
                "ipa": "p a t o",
                "target_ipa": "p a t o",
                "tokens": ["p", "a", "t", "o"],
                "ops": [],
                "alignment": [],
                "meta": {},
            }

    async def fake_compare_file_detail(self, *args: Any, **kwargs: Any) -> FakeComparePayload:
        captured_kwargs.update(kwargs)
        return FakeComparePayload()

    monkeypatch.setattr("ipa_server.routers.pipeline.ComparisonService.compare_file_detail", fake_compare_file_detail)
    app.dependency_overrides[pipeline_router._get_kernel] = lambda: kernel

    response = await client.post(
        "/v1/compare",
        data={
            "text": "pato",
            "lang": "es",
            "force_phonetic": "true",
            "allow_quality_downgrade": "false",
        },
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 200
    assert captured_kwargs["force_phonetic"] is True
    assert captured_kwargs["allow_quality_downgrade"] is False
