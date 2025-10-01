from __future__ import annotations

import sys
from importlib import metadata
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from ipa_core.kernel import Kernel, KernelConfig
from ipa_core.plugins import PLUGIN_GROUPS, list_plugins, load_plugin


class DummyEntryPoints:
    def __init__(self, entries: list[metadata.EntryPoint]):
        self._entries = entries

    def select(self, *, group: str):
        return [ep for ep in self._entries if ep.group == group]


@pytest.fixture(autouse=True)
def cleanup_fake_module():
    yield
    sys.modules.pop("fake_plugin", None)


def register_fake_plugin(monkeypatch, group: str, name: str, obj):
    module = ModuleType("fake_plugin")
    setattr(module, "Plugin", obj)
    sys.modules["fake_plugin"] = module

    ep = metadata.EntryPoint(name=name, value="fake_plugin:Plugin", group=group)
    monkeypatch.setattr(
        "ipa_core.plugins.metadata.entry_points",
        lambda: DummyEntryPoints([ep]),
    )
    return ep


def test_load_plugin_success(monkeypatch):
    class Dummy:
        pass

    register_fake_plugin(monkeypatch, "ipa_core.backends.asr", "dummy", Dummy)

    loaded = load_plugin("ipa_core.backends.asr", "dummy")
    assert loaded is Dummy


def test_list_plugins_sorted(monkeypatch):
    class Dummy:
        pass

    ep1 = metadata.EntryPoint(name="b", value="fake_plugin:Plugin", group="grp")
    ep2 = metadata.EntryPoint(name="a", value="fake_plugin:Plugin", group="grp")
    monkeypatch.setattr(
        "ipa_core.plugins.metadata.entry_points",
        lambda: DummyEntryPoints([ep1, ep2]),
    )

    assert list_plugins("grp") == ["a", "b"]


def test_load_plugin_missing(monkeypatch):
    monkeypatch.setattr(
        "ipa_core.plugins.metadata.entry_points",
        lambda: DummyEntryPoints([]),
    )

    with pytest.raises(ValueError):
        load_plugin("grp", "missing")


def test_kernel_instantiation(monkeypatch, tmp_path: Path):
    class DummyASR:
        def __call__(self):
            return self

        def transcribe_ipa(self, path: str) -> str:  # pragma: no cover - stub
            return f"ipa::{path}"

    class DummyText:
        def __call__(self):
            return self

        def text_to_ipa(self, text: str, lang: str | None = None) -> str:  # pragma: no cover - stub
            return f"ipa::{text}::{lang}"

    class DummyCmp:
        def __call__(self):
            return self

        def compare(self, ref: str, hyp: str):  # pragma: no cover - stub
            return (ref, hyp)

    def fake_loader(group: str, name: str):
        mapping = {
            PLUGIN_GROUPS["asr"].entrypoint_group: DummyASR,
            PLUGIN_GROUPS["textref"].entrypoint_group: DummyText,
            PLUGIN_GROUPS["comparator"].entrypoint_group: DummyCmp,
        }
        return mapping[group]

    monkeypatch.setattr("ipa_core.kernel.load_plugin", fake_loader)

    cfg = KernelConfig(asr_backend="a", textref="b", comparator="c")
    kernel = Kernel(cfg)
    result = kernel.run(tmp_path, dry_run=True)

    assert result["plugins"]["asr_backend"] == "a"
    assert result["plugins"]["textref"] == "b"
    assert result["plugins"]["comparator"] == "c"
    assert result["dry_run"] is True


def test_kernel_run_collects_files(monkeypatch, tmp_path: Path):
    audio_file = tmp_path / "sample.wav"
    audio_file.write_text("fake")

    class DummyPlugin:
        def __call__(self):
            return self

    monkeypatch.setattr(
        "ipa_core.kernel.load_plugin",
        lambda group, name: DummyPlugin,
    )

    cfg = KernelConfig(asr_backend="null", textref="noop", comparator="noop")
    kernel = Kernel(cfg)
    result = kernel.run(tmp_path, dry_run=False)

    assert result["files"] == ["sample.wav"]
    assert result["dry_run"] is False


def test_kernel_config_from_yaml(tmp_path: Path):
    yaml_content = """
plugins:
  asr_backend: foo
  textref: bar
  comparator: baz
  preprocessor:
"""
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(yaml_content)

    cfg = KernelConfig.from_yaml(cfg_path)

    assert cfg.asr_backend == "foo"
    assert cfg.textref == "bar"
    assert cfg.comparator == "baz"
    assert cfg.preprocessor is None


def test_kernel_config_invalid_section():
    with pytest.raises(ValueError):
        KernelConfig.from_mapping({"plugins": "no-es-un-mapeo"})
