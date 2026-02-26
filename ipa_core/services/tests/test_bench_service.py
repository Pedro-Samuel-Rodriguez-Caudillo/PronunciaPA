"""Tests para bench/calibration service."""
from __future__ import annotations

import pytest

from ipa_core.services.bench import (
    AdapterBenchResult,
    BenchReport,
    _downgrade,
    _percentile,
    recommend_tier,
    run_bench,
    run_bench_all,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    name: str = "stub",
    json_valid_pct: float = 100.0,
    latency_p95: float = 100.0,
) -> AdapterBenchResult:
    return AdapterBenchResult(
        adapter_name=name,
        n_prompts=5,
        n_valid_json=int(json_valid_pct * 5 / 100),
        json_valid_pct=json_valid_pct,
        latency_median_ms=latency_p95 * 0.6,
        latency_p95_ms=latency_p95,
        latency_min_ms=20.0,
        latency_max_ms=latency_p95,
        rss_delta_mb=0.0,
    )


# ---------------------------------------------------------------------------
# _percentile
# ---------------------------------------------------------------------------

def test_percentile_median():
    data = sorted([10, 20, 30, 40, 50])
    assert _percentile(data, 50) == 30.0


def test_percentile_empty():
    assert _percentile([], 50) == 0.0


# ---------------------------------------------------------------------------
# _downgrade
# ---------------------------------------------------------------------------

def test_downgrade_7b_to_3b():
    assert _downgrade("7B") == "3B"


def test_downgrade_3b_to_1b():
    assert _downgrade("3B") == "1B"


def test_downgrade_1b_stays():
    assert _downgrade("1B") == "1B"


# ---------------------------------------------------------------------------
# recommend_tier
# ---------------------------------------------------------------------------

def test_recommend_tier_high_ram():
    result = _make_result(latency_p95=200.0, json_valid_pct=100.0)
    tier, reason = recommend_tier([result], available_ram_gb=16.0)
    assert tier == "7B"
    assert "RAM" in reason


def test_recommend_tier_low_ram():
    result = _make_result(latency_p95=200.0, json_valid_pct=100.0)
    tier, reason = recommend_tier([result], available_ram_gb=1.0)
    assert tier == "1B"


def test_recommend_tier_downgrade_for_latency():
    slow = _make_result(latency_p95=5000.0, json_valid_pct=100.0)
    tier, reason = recommend_tier([slow], available_ram_gb=10.0)
    # Should downgrade from 7B → 3B
    assert tier in ("3B", "1B")
    assert "downgraded" in reason


def test_recommend_tier_downgrade_for_low_json():
    bad_json = _make_result(latency_p95=200.0, json_valid_pct=50.0)
    tier, reason = recommend_tier([bad_json], available_ram_gb=10.0)
    assert tier in ("3B", "1B")
    assert "downgraded" in reason


def test_recommend_tier_no_results():
    tier, reason = recommend_tier([], available_ram_gb=8.0)
    assert tier == "7B"  # RAM ≥ 8 GB, no latency penalty


# ---------------------------------------------------------------------------
# run_bench (stub adapter)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_bench_stub():
    result = await run_bench("stub")
    assert result.adapter_name == "stub"
    assert result.n_prompts == 5
    assert result.json_valid_pct == 100.0
    assert result.latency_median_ms >= 0


@pytest.mark.asyncio
async def test_run_bench_stub_partial():
    result = await run_bench("stub", n_prompts=2)
    assert result.n_prompts == 2


# ---------------------------------------------------------------------------
# run_bench_all
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_bench_all():
    report = await run_bench_all(["stub"], n_prompts=3, available_ram_gb=8.0)
    assert isinstance(report, BenchReport)
    assert len(report.results) == 1
    assert report.recommended_tier is not None
    assert report.results[0].json_valid_pct == 100.0


@pytest.mark.asyncio
async def test_run_bench_all_unknown_adapter():
    """Unknown adapters should fall back to stub and not crash."""
    report = await run_bench_all(["nonexistent_adapter"], n_prompts=2)
    assert len(report.results) == 1


# ---------------------------------------------------------------------------
# BenchReport.best()
# ---------------------------------------------------------------------------

def test_bench_report_best():
    r1 = _make_result("a", json_valid_pct=80.0, latency_p95=500.0)
    r2 = _make_result("b", json_valid_pct=100.0, latency_p95=100.0)
    report = BenchReport(results=[r1, r2])
    assert report.best().adapter_name == "b"


def test_bench_report_best_empty():
    assert BenchReport().best() is None
