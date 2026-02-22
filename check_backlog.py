"""Quick smoke-test for all backlog implementations."""
import asyncio, sys

errors = []

def ok(msg):
    print(f"  OK  {msg}")

def fail(msg, exc):
    print(f" FAIL {msg}: {exc}")
    errors.append(msg)

# 1. PLACE_DISTANCE_TABLE + Tenseness
try:
    from ipa_core.compare.articulatory import PLACE_DISTANCE_TABLE, Tenseness, VOWEL_FEATURES
    assert len(PLACE_DISTANCE_TABLE) > 50
    assert VOWEL_FEATURES["i"].tenseness == Tenseness.TENSE
    assert VOWEL_FEATURES["\u026a"].tenseness == Tenseness.LAX
    ok("articulatory PLACE_DISTANCE_TABLE + Tenseness")
except Exception as e:
    fail("articulatory", e)

# 2. OOV port
try:
    from ipa_core.ports.oov import OOVHandlerPort, PassthroughOOVHandler
    p = PassthroughOOVHandler()
    assert p.filter_sequence(["a","b"]) == ["a","b"]
    ok("OOVHandlerPort + PassthroughOOVHandler")
except Exception as e:
    fail("oov port", e)

# 3. F1 metric
try:
    from ipa_core.compare.metrics import compute_phoneme_f1, compute_per_and_f1
    result = compute_phoneme_f1(["a","b","c"], ["a","b","d"])
    assert 0 < result.f1 < 1
    ok(f"compute_phoneme_f1 f1={result.f1:.3f}")
except Exception as e:
    fail("metrics", e)

# 4. SQLite history (import only – don't touch DB)
try:
    from ipa_core.history.sqlite import SQLiteHistory
    ok("SQLiteHistory import")
except Exception as e:
    fail("sqlite history", e)

# 5. Allosaurus LANG_MAP
try:
    from ipa_core.backends.allosaurus_backend import AllosaurusBackend
    lang_map = AllosaurusBackend._LANG_MAP
    assert len(lang_map) > 50, len(lang_map)
    ok(f"Allosaurus LANG_MAP ({len(lang_map)} entries)")
except Exception as e:
    fail("allosaurus lang_map", e)

# 6. Syllabic analysis
try:
    from ipa_core.analysis.syllabic import syllabify, Syllable
    syls = syllabify(["p","a","t","a"])
    assert len(syls) >= 1
    ok(f"syllabify -> {len(syls)} syllables")
except Exception as e:
    fail("syllabic", e)

# 7. Position classifier
try:
    from ipa_core.analysis.position import classify_errors_by_position, error_distribution
    fake_ops = [
        {"op": "equal", "ref": "a", "hyp": "a", "ref_pos": 0},
        {"op": "sub",   "ref": "b", "hyp": "d", "ref_pos": 1},
        {"op": "equal", "ref": "c", "hyp": "c", "ref_pos": 2},
    ]
    out = classify_errors_by_position(fake_ops, ref_tokens=["a","b","c"])
    ok(f"position classifier -> {len(out)} entries")
except Exception as e:
    fail("position", e)

# 8. Phoneme corpus port
async def _check_corpus():
    from ipa_core.ports.phoneme_corpus import NullPhonemeCorpus, DiskPhonemeCorpus
    n = NullPhonemeCorpus()
    result = await n.get_phone_audio("a", lang="es")
    assert result is None
    return True
try:
    asyncio.get_event_loop().run_until_complete(_check_corpus())
    ok("PhonemeCorpusPort (NullPhonemeCorpus)")
except Exception as e:
    fail("phoneme_corpus", e)

# 9. SVG vocal tract
try:
    from ipa_core.display.vocal_tract_svg import render_phone_svg, phone_svg_data_uri
    svg = render_phone_svg("p")
    assert "<svg" in svg
    ok(f"render_phone_svg -> {len(svg)} chars SVG")
except Exception as e:
    fail("vocal_tract_svg", e)

# 10. Suprasegmentals
try:
    from ipa_core.phonology.suprasegmentals import strip_suprasegmentals, extract_suprasegmentals
    clean = strip_suprasegmentals("\u02c8pa\u02d0pa", mode="phonemic")
    assert "\u02c8" not in clean
    ok(f"suprasegmentals strip -> '{clean}'")
except Exception as e:
    fail("suprasegmentals", e)

# 11. Drill generator proximity grouping
try:
    from ipa_core.analysis.drill_generator import group_phones_by_articulatory_proximity
    groups = group_phones_by_articulatory_proximity(["p","b","t","d","k","g"])
    assert len(groups) >= 1
    ok(f"drill proximity grouping -> {len(groups)} groups")
except Exception as e:
    fail("drill_generator", e)

# 12. Ports __init__ exports
try:
    from ipa_core.ports import OOVHandlerPort, PhonemeCorpusPort, HistoryPort
    ok("ports __init__ exports OOVHandlerPort, PhonemeCorpusPort, HistoryPort")
except Exception as e:
    fail("ports __init__", e)

# 13. runner.py oov_handler param
try:
    import inspect
    from ipa_core.pipeline.runner import execute_pipeline, run_pipeline_with_pack
    sig_exec = inspect.signature(execute_pipeline)
    sig_wrap = inspect.signature(run_pipeline_with_pack)
    assert "oov_handler" in sig_exec.parameters, "execute_pipeline missing oov_handler"
    assert "oov_handler" in sig_wrap.parameters, "run_pipeline_with_pack missing oov_handler"
    ok("runner.py oov_handler param in execute_pipeline + run_pipeline_with_pack")
except Exception as e:
    fail("runner oov_handler", e)

print()
if errors:
    print(f"FAILED ({len(errors)}): {errors}")
    sys.exit(1)
else:
    print(f"All {13} checks passed.")
