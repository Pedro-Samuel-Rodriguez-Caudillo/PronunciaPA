from __future__ import annotations

import math
import wave

import sys
from array import array
from importlib import metadata
from pathlib import Path
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ipa_core.api.cli import app
from ipa_core.backends.whisper_ipa import WhisperIPABackend
from ipa_core.plugins import PLUGIN_GROUPS


class DummyEntryPoints:
    def __init__(self, entries):
        self._entries = entries

    def select(self, *, group: str):
        return [ep for ep in self._entries if ep.group == group]


def _write_wav(path: Path, samples: list[float], sample_rate: int) -> None:
    clipped = [max(-1.0, min(1.0, value)) for value in samples]
    int_samples = array("h", (int(round(value * 32767.0)) for value in clipped))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int_samples.tobytes())


def test_transcribe_ipa_invoca_pipeline(tmp_path: Path):
    calls = {}

    def fake_pipeline(task, **kwargs):
        assert task == "automatic-speech-recognition"
        calls["pipeline_kwargs"] = kwargs

        def run(audio, sampling_rate, **call_kwargs):
            calls["audio"] = audio
            calls["sampling_rate"] = sampling_rate
            calls["call_kwargs"] = call_kwargs
            return {"text": "t͡sa?!"}

        return run

    backend = WhisperIPABackend(model_name="dummy-model", pipeline_factory=fake_pipeline)

    audio_path = tmp_path / "sample.wav"
    samples = [math.sin(2 * math.pi * 440 * (i / 22_050)) for i in range(2_205)]
    _write_wav(audio_path, samples, sample_rate=22_050)

    ipa = backend.transcribe_ipa(str(audio_path))

    assert ipa == "tsa"
    assert calls["sampling_rate"] == backend.target_sample_rate
    max_abs = max(abs(value) for value in calls["audio"])
    assert abs(max_abs - 1.0) < 1e-3
    assert calls["call_kwargs"]["generate_kwargs"]["task"] == "transcribe"


def test_cli_lists_whisper_backend(monkeypatch):
    ep = metadata.EntryPoint(
        name="whisper-ipa",
        value="fake:Plugin",
        group=PLUGIN_GROUPS["asr"].entrypoint_group,
    )

    monkeypatch.setattr(
        "ipa_core.plugins.metadata.entry_points",
        lambda: DummyEntryPoints([ep]),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["plugins", "list", "--group", "asr"])

    assert result.exit_code == 0
    assert "whisper-ipa" in result.stdout
