import pytest
from ipa_core.analysis.syllabic import syllabify, Syllable, get_syllabic_position
from ipa_core.analysis.drill_generator import extract_confusion_pairs, generate_drills_from_errors

def test_syllabify_basic():
    # p a l a b r a
    tokens = ["p", "a", "l", "a", "β", "r", "a"]
    sylls = syllabify(tokens)
    assert len(sylls) == 3
    assert sylls[0].nucleus == "a"
    assert sylls[0].onset == ["p"]
    assert sylls[1].onset == ["l"]
    assert sylls[2].onset == ["β", "r"]

def test_syllabify_no_vowels():
    tokens = ["s", "t", "r"]
    sylls = syllabify(tokens)
    assert len(sylls) == 1
    assert sylls[0].onset == ["s", "t", "r"]
    assert sylls[0].nucleus == ""

def test_get_syllabic_position():
    tokens = ["p", "a", "l", "a", "β", "r", "a"]
    # 'p' is onset of first syllable
    pos = get_syllabic_position(tokens, 0)
    assert pos["syllable_index"] == 0
    assert pos["position"] == "onset"
    assert pos["syllable_position"] == "initial"
    
    # 'r' is onset of last syllable
    pos = get_syllabic_position(tokens, 5)
    assert pos["syllable_index"] == 2
    assert pos["position"] == "onset"
    assert pos["syllable_position"] == "final"

def test_extract_confusion_pairs():
    ops = [
        {"op": "sub", "ref": "p", "hyp": "b"},
        {"op": "sub", "ref": "p", "hyp": "b"},
        {"op": "ins", "hyp": "ə"},
        {"op": "del", "ref": "h"}
    ]
    pairs = extract_confusion_pairs(ops)
    assert len(pairs) >= 3
    # Insertions and deletions have distance 1.0, impact 1.0
    # p->b has count 2, distance ~0.15, impact ~0.3
    # So the insertion/deletion should come first
    assert pairs[0]["ref"] == "_" or pairs[0]["hyp"] == "_"
    # Find p->b in the list
    pb_pair = next(p for p in pairs if p["ref"] == "p" and p["hyp"] == "b")
    assert pb_pair["count"] == 2

def test_generate_drills_from_errors():
    ops = [{"op": "sub", "ref": "r", "hyp": "l"}]
    drill_set = generate_drills_from_errors(ops, lang="es")
    assert drill_set.lang == "es"
    assert len(drill_set.items) > 0
    assert "r" in drill_set.target_phones
