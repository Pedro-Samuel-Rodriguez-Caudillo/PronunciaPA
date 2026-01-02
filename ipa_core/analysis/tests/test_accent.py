from __future__ import annotations

import pytest
from ipa_core.analysis.accent import build_feedback, extract_features, rank_accents


def test_rank_accents_orders_by_per():
    ranking = rank_accents({"en-us": 0.1, "en-uk": 0.3}, {"en-us": "US", "en-uk": "UK"})
    assert ranking[0]["accent"] == "en-us"
    assert ranking[0]["label"] == "US"
    assert ranking[0]["per"] == 0.1
    assert sum(item["confidence"] for item in ranking) == pytest.approx(1.0)


def test_extract_features_counts_pairs():
    alignment = [("t", "ʔ"), ("ɹ", None), ("s", "s")]
    features = [
        {"id": "t_glottal", "label": "T-glottalization", "pairs": [["t", "ʔ"]]},
        {"id": "rhoticity", "label": "Rhoticity", "pairs": [["ɹ", "_"]]},
    ]
    result = extract_features(alignment, features)
    t_feat = next(item for item in result if item["id"] == "t_glottal")
    r_feat = next(item for item in result if item["id"] == "rhoticity")
    assert t_feat["matches"] == 1
    assert r_feat["matches"] == 1


def test_build_feedback_groups_ops():
    ops = [
        {"op": "eq", "ref": "a", "hyp": "a"},
        {"op": "sub", "ref": "t", "hyp": "ʔ"},
        {"op": "del", "ref": "s", "hyp": None},
        {"op": "ins", "ref": None, "hyp": "h"},
    ]
    feedback = build_feedback(ops)
    keys = {(item["ref"], item["hyp"]) for item in feedback}
    assert ("t", "ʔ") in keys
    assert ("s", "_") in keys
    assert ("_", "h") in keys
