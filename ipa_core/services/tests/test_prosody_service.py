"""Tests para ProsodyMetrics y analyze_prosody."""
from __future__ import annotations

import pytest

from ipa_core.services.prosody import (
    ProsodyMetrics,
    analyze_prosody,
    apply_prosody_weight,
    _compute_rhythm_score,
)
from tests.utils.audio import write_sine_wave


# ---------------------------------------------------------------------------
# Tests de _compute_rhythm_score
# ---------------------------------------------------------------------------

def test_perfect_rhythm_score():
    """rate_ratio=1.0, no pauses → máximo puntaje (100.0)."""
    score = _compute_rhythm_score(
        rate_ratio=1.0,
        pause_count=0,
        avg_pause_ms=0.0,
        speech_ratio=0.8,
        total_ms=2000,
    )
    assert score == 100.0


def test_slow_speech_reduces_rate_score():
    """Velocidad 50 % de la referencia debe reducir la puntuación."""
    score_fast = _compute_rhythm_score(
        rate_ratio=1.0,
        pause_count=0,
        avg_pause_ms=0.0,
        speech_ratio=0.8,
        total_ms=2000,
    )
    score_slow = _compute_rhythm_score(
        rate_ratio=0.5,
        pause_count=0,
        avg_pause_ms=0.0,
        speech_ratio=0.8,
        total_ms=2000,
    )
    assert score_slow < score_fast


def test_long_pauses_reduce_score():
    """Pausas > threshold deben penalizar el score."""
    score_no_pause = _compute_rhythm_score(
        rate_ratio=1.0,
        pause_count=0,
        avg_pause_ms=0.0,
        speech_ratio=0.8,
        total_ms=3000,
    )
    score_pauses = _compute_rhythm_score(
        rate_ratio=1.0,
        pause_count=3,
        avg_pause_ms=1200.0,
        speech_ratio=0.8,
        total_ms=3000,
    )
    assert score_pauses < score_no_pause


def test_low_speech_ratio_reduces_score():
    """audio mayormente silencio debe tener menor puntuación."""
    score_normal = _compute_rhythm_score(
        rate_ratio=1.0, pause_count=0, avg_pause_ms=0.0, speech_ratio=0.8, total_ms=2000
    )
    score_silent = _compute_rhythm_score(
        rate_ratio=1.0, pause_count=0, avg_pause_ms=0.0, speech_ratio=0.1, total_ms=2000
    )
    assert score_silent < score_normal


# ---------------------------------------------------------------------------
# Tests de analyze_prosody
# ---------------------------------------------------------------------------

def test_analyze_prosody_basic(tmp_path):
    """analyze_prosody debe devolver ProsodyMetrics sin excepciones."""
    wav = write_sine_wave(tmp_path / "test.wav", seconds=1.0)
    metrics = analyze_prosody(wav, extract_f0=False)
    assert isinstance(metrics, ProsodyMetrics)
    assert metrics.total_ms > 0
    assert 0.0 <= metrics.rhythm_score <= 100.0


def test_analyze_prosody_with_phones(tmp_path):
    """Con observed_phones, la velocidad debe estar calculada."""
    wav = write_sine_wave(tmp_path / "phones.wav", seconds=1.0)
    phones = ["p", "a", "l", "a", "β", "ɾ", "a"]
    metrics = analyze_prosody(wav, observed_phones=phones, extract_f0=False)
    assert metrics.speech_rate_phones_per_sec > 0
    assert metrics.speech_rate_ratio > 0


def test_analyze_prosody_with_vad_pauses(tmp_path):
    """Con segmentos VAD, la duración de voz debe calcularse correctamente."""
    wav = write_sine_wave(tmp_path / "paused.wav", seconds=2.0)
    segments = [(100, 600), (1000, 1800)]
    pauses = [(600, 1000)]
    metrics = analyze_prosody(
        wav,
        vad_speech_segments=segments,
        vad_internal_pauses=pauses,
        vad_duration_ms=2000,
        extract_f0=False,
    )
    assert metrics.voiced_ms == 1300  # (500 + 800)
    assert metrics.pause_count == 1
    assert metrics.avg_pause_ms == 400.0


def test_analyze_prosody_file_not_found():
    """FileNotFoundError para rutas inexistentes."""
    with pytest.raises(FileNotFoundError):
        analyze_prosody("/no/such/file.wav", extract_f0=False)


# ---------------------------------------------------------------------------
# Tests de apply_prosody_weight
# ---------------------------------------------------------------------------

def test_apply_prosody_weight_zero():
    """Peso 0 → devuelve el score fonético sin cambio."""
    m = ProsodyMetrics(rhythm_score=50.0)
    assert apply_prosody_weight(80.0, m, prosody_weight=0.0) == 80.0


def test_apply_prosody_weight_blend():
    """Peso 0.2 debe mezclar correctamente."""
    m = ProsodyMetrics(rhythm_score=60.0)
    result = apply_prosody_weight(80.0, m, prosody_weight=0.2)
    expected = round(0.8 * 80.0 + 0.2 * 60.0, 1)
    assert result == expected
