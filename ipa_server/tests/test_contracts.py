from typing import List
import pytest
from pydantic import ValidationError

# This import will fail initially
try:
    from ipa_server.models import (
        TranscriptionResponse,
        TextRefResponse,
        CompareResponse,
        EditOp,
        ErrorResponse,
        AudioUploadMeta
    )
except ImportError:
    pass


def test_transcription_response_schema():
    """Verify TranscriptionResponse model structure."""
    # Create a valid instance
    resp = TranscriptionResponse(
        ipa="t e s t",
        tokens=["t", "e", "s", "t"],
        lang="es",
        meta={"duration": 1.5}
    )
    assert resp.ipa == "t e s t"
    assert resp.tokens == ["t", "e", "s", "t"]
    assert resp.lang == "es"
    assert resp.meta["duration"] == 1.5

    # Check serialization
    data = resp.model_dump()
    assert data["ipa"] == "t e s t"
    assert "tokens" in data


def test_compare_response_schema():
    """Verify CompareResponse model structure."""
    ops = [
        EditOp(op="eq", ref="a", hyp="a"),
        EditOp(op="sub", ref="b", hyp="p")
    ]
    resp = CompareResponse(
        per=0.5,
        ops=ops,
        alignment=[["a", "a"], ["b", "p"]],
        meta={"confidence": 0.9}
    )
    assert resp.per == 0.5
    assert len(resp.ops) == 2
    assert resp.ops[0].op == "eq"
    assert resp.alignment[0] == ["a", "a"]

def test_textref_response_schema():
    """Verify TextRefResponse model structure."""
    resp = TextRefResponse(
        ipa="h o l a",
        tokens=["h", "o", "l", "a"],
        lang="es",
        meta={"method": "grapheme"}
    )
    assert resp.ipa == "h o l a"
    assert resp.tokens == ["h", "o", "l", "a"]
    assert resp.lang == "es"
    assert resp.meta["method"] == "grapheme"


def test_error_response_schema():
    """Verify ErrorResponse model structure."""
    err = ErrorResponse(
        detail="Something went wrong",
        type="validation_error",
        code=400
    )
    assert err.detail == "Something went wrong"
    assert err.type == "validation_error"
    assert err.code == 400


def test_audio_upload_meta_schema():
    """Verify AudioUploadMeta model structure (for form data)."""
    # This might be used to validate form fields if we use Pydantic for Form
    # or just as a documentation contract.
    meta = AudioUploadMeta(
        lang="es",
        sample_rate=16000
    )
    assert meta.lang == "es"
    assert meta.sample_rate == 16000
