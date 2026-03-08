"""Realtime session contract tests."""
from __future__ import annotations

from fastapi.testclient import TestClient
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from ipa_core.audio.stream import AudioSegment, StreamState
from ipa_server.main import get_app
from ipa_server import realtime


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


def _make_session(*, reference_text: str | None = None) -> tuple[realtime.RealtimeSession, _FakeWebSocket]:
    ws = _FakeWebSocket()
    session = realtime.RealtimeSession(
        cast(Any, ws),
        realtime.WSConfig(
            lang="es",
            reference_text=reference_text,
            mode="objective",
            evaluation_level="phonemic",
        ),
    )
    session.kernel = cast(
        Any,
        SimpleNamespace(pre=object(), asr=object(), textref=object(), comp=object()),
    )
    return session, ws


@pytest.mark.asyncio
async def test_state_messages_are_nested_under_data() -> None:
    session, ws = _make_session()

    await session._on_state_change(
        StreamState(
            is_speaking=True,
            volume_level=0.42,
            buffer_duration_ms=750,
            status="speaking",
        )
    )

    assert ws.sent == [
        {
            "type": "state",
            "data": {
                "is_speaking": True,
                "volume_level": 0.42,
                "buffer_duration_ms": 750,
                "status": "speaking",
            },
        }
    ]


@pytest.mark.asyncio
async def test_segment_ready_sends_transcription_payload(monkeypatch, tmp_path) -> None:
    session, ws = _make_session()

    class _FakeTranscriptionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def transcribe_file(self, path: str, *, lang: str):
            assert path.endswith("segment.wav")
            assert lang == "es"
            return SimpleNamespace(ipa="o l a", tokens=["o", "l", "a"])

    monkeypatch.setattr(realtime, "TranscriptionService", _FakeTranscriptionService)

    audio_path = tmp_path / "segment.wav"
    audio_path.write_bytes(b"wav")
    segment = AudioSegment(audio_path=audio_path, duration_ms=321, speech_ratio=0.9)

    await session._on_segment_ready(segment)

    assert ws.sent[-1] == {
        "type": "transcription",
        "data": {
            "ipa": "o l a",
            "tokens": ["o", "l", "a"],
            "lang": "es",
            "meta": {"duration_ms": 321},
        },
    }
    assert not audio_path.exists()


@pytest.mark.asyncio
async def test_comparison_messages_match_http_shape(monkeypatch, tmp_path) -> None:
    session, ws = _make_session(reference_text="hola")
    session.ws_config.mode = "objective"
    session.ws_config.evaluation_level = "phonemic"

    class _FakeComparisonService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def compare_file_detail(
            self,
            path: str,
            text: str,
            *,
            lang: str,
            mode: str,
            evaluation_level: str,
        ):
            assert text == "hola"
            assert lang == "es"
            assert mode == "objective"
            assert evaluation_level == "phonemic"
            return SimpleNamespace(
                hyp_tokens=["o", "r", "a"],
                ref_tokens=["o", "l", "a"],
                result={
                    "per": 0.25,
                    "ops": [{"op": "sub", "ref": "l", "hyp": "r"}],
                    "alignment": [["o", "o"], ["l", "r"], ["a", "a"]],
                },
                mode="objective",
                evaluation_level="phonemic",
                meta={"warnings": ["demo"]},
                to_response=lambda extra_meta=None: {
                    "per": 0.25,
                    "ops": [{"op": "sub", "ref": "l", "hyp": "r"}],
                    "alignment": [["o", "o"], ["l", "r"], ["a", "a"]],
                    "score": 75.0,
                    "mode": "objective",
                    "evaluation_level": "phonemic",
                    "ipa": "o r a",
                    "tokens": ["o", "r", "a"],
                    "target_ipa": "o l a",
                    "meta": {"warnings": ["demo"]},
                },
            )

    monkeypatch.setattr(realtime, "ComparisonService", _FakeComparisonService)

    segment_path = tmp_path / "compare.wav"
    segment_path.write_bytes(b"wav")

    await session._send_comparison(str(segment_path), 123)

    assert ws.sent[-1] == {
        "type": "comparison",
        "data": {
            "per": 0.25,
            "ops": [{"op": "sub", "ref": "l", "hyp": "r"}],
            "alignment": [["o", "o"], ["l", "r"], ["a", "a"]],
            "score": 75.0,
            "mode": "objective",
            "evaluation_level": "phonemic",
            "ipa": "o r a",
            "tokens": ["o", "r", "a"],
            "target_ipa": "o l a",
            "meta": {"warnings": ["demo"]},
            "duration_ms": 123,
        },
    }


@pytest.mark.asyncio
async def test_send_error_includes_top_level_and_nested_message() -> None:
    session, ws = _make_session()

    await session._send_error("falló", "comparison_error")

    assert ws.sent == [
        {
            "type": "error",
            "message": "falló",
            "data": {"message": "falló", "code": "comparison_error"},
        }
    ]


@pytest.mark.asyncio
async def test_handle_message_updates_config_and_controls(monkeypatch) -> None:
    session, ws = _make_session()
    flush_calls: list[str] = []
    reset_calls: list[str] = []
    state_calls: list[StreamState] = []

    async def _flush() -> None:
        flush_calls.append("flush")

    def _reset() -> None:
        reset_calls.append("reset")

    async def _state_change(state: StreamState) -> None:
        state_calls.append(state)

    monkeypatch.setattr(session.buffer, "flush", _flush)
    monkeypatch.setattr(session.buffer, "reset", _reset)
    monkeypatch.setattr(session, "_on_state_change", _state_change)

    await session.handle_message(
        {
            "type": "config",
            "data": {
                "lang": "en",
                "reference_text": "hello",
                "mode": "phonetic",
                "evaluation_level": "phonetic",
            },
        }
    )
    await session.handle_message({"type": "flush"})
    await session.handle_message({"type": "reset"})
    await session.handle_message({"type": "ping"})

    assert session.ws_config.lang == "en"
    assert session.ws_config.reference_text == "hello"
    assert session.ws_config.mode == "phonetic"
    assert session.ws_config.evaluation_level == "phonetic"
    assert flush_calls == ["flush"]
    assert reset_calls == ["reset"]
    assert len(state_calls) == 1
    assert ws.sent[-1] == {"type": "pong"}


def test_websocket_endpoint_ready_ping_and_invalid_json() -> None:
    client = TestClient(get_app())

    with client.websocket_connect("/ws/practice") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "ready"
        assert ready["config"]["lang"] == "es"

        websocket.send_text('{"type": "ping"}')
        assert websocket.receive_json() == {"type": "pong"}

        websocket.send_text("{")
        assert websocket.receive_json() == {
            "type": "error",
            "message": "JSON inválido",
            "data": {"message": "JSON inválido", "code": "invalid_json"},
        }


def test_websocket_endpoint_binary_audio_emits_transcription(monkeypatch, tmp_path) -> None:
    class _FakeTranscriptionService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def transcribe_file(self, path: str, *, lang: str):
            assert path.endswith("ws-segment.wav")
            assert lang == "es"
            return SimpleNamespace(ipa="o l a", tokens=["o", "l", "a"])

    async def _fake_add_chunk(self, audio_data: bytes):
        assert audio_data == b"pcm"
        segment_path = tmp_path / "ws-segment.wav"
        segment_path.write_bytes(b"wav")
        await self._on_segment_ready(
            AudioSegment(audio_path=segment_path, duration_ms=200, speech_ratio=0.9)
        )
        return self.state

    monkeypatch.setattr(realtime, "TranscriptionService", _FakeTranscriptionService)
    monkeypatch.setattr(realtime.AudioBuffer, "add_chunk", _fake_add_chunk)

    client = TestClient(get_app())
    with client.websocket_connect("/ws/practice") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "ready"

        websocket.send_bytes(b"pcm")
        transcription = websocket.receive_json()
        assert transcription == {
            "type": "transcription",
            "data": {
                "ipa": "o l a",
                "tokens": ["o", "l", "a"],
                "lang": "es",
                "meta": {"duration_ms": 200},
            },
        }


def test_websocket_endpoint_binary_audio_emits_comparison(monkeypatch, tmp_path) -> None:
    class _FakeComparisonService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def compare_file_detail(
            self,
            path: str,
            text: str,
            *,
            lang: str,
            mode: str,
            evaluation_level: str,
        ):
            assert path.endswith("ws-compare.wav")
            assert text == "hola"
            assert lang == "es"
            assert mode == "phonetic"
            assert evaluation_level == "phonetic"
            return SimpleNamespace(
                hyp_tokens=["o", "r", "a"],
                ref_tokens=["o", "l", "a"],
                result={
                    "per": 0.25,
                    "ops": [{"op": "sub", "ref": "l", "hyp": "r"}],
                    "alignment": [["o", "o"], ["l", "r"], ["a", "a"]],
                },
                mode="phonetic",
                evaluation_level="phonetic",
                meta={"warnings": ["demo"]},
                to_response=lambda extra_meta=None: {
                    "per": 0.25,
                    "ops": [{"op": "sub", "ref": "l", "hyp": "r"}],
                    "alignment": [["o", "o"], ["l", "r"], ["a", "a"]],
                    "score": 75.0,
                    "mode": "phonetic",
                    "evaluation_level": "phonetic",
                    "ipa": "o r a",
                    "tokens": ["o", "r", "a"],
                    "target_ipa": "o l a",
                    "meta": {"warnings": ["demo"]},
                },
            )

    async def _fake_add_chunk(self, audio_data: bytes):
        assert audio_data == b"pcm"
        segment_path = tmp_path / "ws-compare.wav"
        segment_path.write_bytes(b"wav")
        await self._on_segment_ready(
            AudioSegment(audio_path=segment_path, duration_ms=180, speech_ratio=0.9)
        )
        return self.state

    monkeypatch.setattr(realtime, "ComparisonService", _FakeComparisonService)
    monkeypatch.setattr(realtime.AudioBuffer, "add_chunk", _fake_add_chunk)

    client = TestClient(get_app())
    with client.websocket_connect("/ws/practice") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "ready"

        websocket.send_json(
            {
                "type": "config",
                "data": {
                    "reference_text": "hola",
                    "mode": "phonetic",
                    "evaluation_level": "phonetic",
                },
            }
        )
        websocket.send_bytes(b"pcm")

        comparison = websocket.receive_json()
        assert comparison == {
            "type": "comparison",
            "data": {
                "per": 0.25,
                "ops": [{"op": "sub", "ref": "l", "hyp": "r"}],
                "alignment": [["o", "o"], ["l", "r"], ["a", "a"]],
                "score": 75.0,
                "mode": "phonetic",
                "evaluation_level": "phonetic",
                "ipa": "o r a",
                "tokens": ["o", "r", "a"],
                "target_ipa": "o l a",
                "meta": {"warnings": ["demo"]},
                "duration_ms": 180,
            },
        }