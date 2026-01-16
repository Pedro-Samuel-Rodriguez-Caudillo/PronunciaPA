"""Tests for FeedbackStore persistence."""
from __future__ import annotations

import json

from ipa_core.services.feedback_store import FeedbackStore


def test_feedback_store_index_and_export(tmp_path) -> None:
    store = FeedbackStore(tmp_path)
    payload = {
        "report": {"lang": "es", "metrics": {"per": 0.1}},
        "compare": {"per": 0.1},
        "feedback": {"summary": "ok"},
    }
    store.append(payload, audio={"path": "audio.wav"}, meta={"lang": "es"})

    index_path = tmp_path / "index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data[0]["summary"] == "ok"

    export_path = store.export(tmp_path / "export.json")
    assert export_path.exists()
