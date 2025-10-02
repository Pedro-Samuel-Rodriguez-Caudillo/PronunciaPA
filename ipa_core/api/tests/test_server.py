"""Tests for the FastAPI server wiring."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from ipa_core.api.server import AnalysisService, create_app
from ipa_core.compare.base import CompareResult, PhonemeStats
from ipa_core.kernel import KernelConfig


class DummyASR:
    def __init__(self) -> None:
        self.last_path: str | None = None

    def transcribe_ipa(self, audio_path: str) -> str:
        self.last_path = audio_path
        return "dɛmo"


class DummyTextRef:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def text_to_ipa(self, text: str, lang: str | None = None) -> str:
        self.calls.append((text, lang))
        return "sɪstema"


class DummyComparator:
    def compare(self, ref_ipa: str, hyp_ipa: str) -> CompareResult:
        stats = PhonemeStats(matches=1, substitutions=1)
        return CompareResult(
            per=0.25,
            ops=[("match", "s", "d"), ("substitution", "ɪ", "ɛ")],
            total_ref_tokens=4,
            matches=1,
            substitutions=1,
            insertions=0,
            deletions=0,
            per_class={"s": stats},
        )


class DummyKernel:
    def __init__(self) -> None:
        self.config = KernelConfig(asr_backend="null", textref="noop", comparator="noop")
        self.asr = DummyASR()
        self.textref = DummyTextRef()
        self.comparator = DummyComparator()


def create_test_client() -> tuple[TestClient, DummyKernel]:
    kernel = DummyKernel()
    service = AnalysisService(kernel=kernel)
    app = create_app(service=service)
    return TestClient(app), kernel


def test_healthcheck_returns_ok() -> None:
    client, _ = create_test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_plugins_endpoint_uses_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = create_test_client()

    def fake_list_plugins(group: str) -> list[str]:  # pragma: no cover - trivial wrapper
        return [group]

    monkeypatch.setattr("ipa_core.api.server.list_plugins", fake_list_plugins)

    response = client.get("/api/plugins")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload["plugins"]) == {"asr", "textref", "comparator", "preprocessor"}
    assert payload["plugins"]["asr"] == ["ipa_core.backends.asr"]


def test_analyze_serialises_response() -> None:
    client, kernel = create_test_client()
    files = {"audio": ("sample.wav", b"data", "audio/wav")}
    data = {"text": "Hola", "lang": "es"}

    response = client.post("/api/analyze", data=data, files=files)

    assert response.status_code == 200
    payload = response.json()

    assert payload["ref_ipa"] == "sɪstema"
    assert payload["hyp_ipa"] == "dɛmo"
    assert pytest.approx(payload["per"], rel=1e-6) == 0.25
    assert payload["config"]["asr_backend"] == "null"
    assert payload["ops"][0] == {"op": "match", "ref": "s", "hyp": "d"}
    assert payload["per_class"]["s"]["errors"] == 1
    assert kernel.asr.last_path is not None
    assert kernel.asr.last_path.endswith(".wav")


def test_analyze_rejects_empty_audio() -> None:
    client, _ = create_test_client()

    response = client.post(
        "/api/analyze",
        data={"text": "Hola"},
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "El archivo de audio está vacío"
