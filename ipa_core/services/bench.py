"""Benchmark and auto-calibration for LLM adapter/tier selection — Step 19.

Runs a small synthetic corpus against one or more LLM adapters and measures:
- JSON-valid rate (%)
- Median and P95 latency (ms)
- Process RSS memory delta (MB)  — proxy for model memory footprint

Based on the results, ``recommend_tier()`` suggests the best-fitting tier
(1B / 3B / 7B) for the current device.

Usage (standalone CLI)::

    python -m ipa_core.services.bench --adapters stub ollama --prompts 5

Programmatic usage::

    from ipa_core.services.bench import run_bench, recommend_tier
    report = await run_bench(adapter_name="stub", n_prompts=5)
    tier  = recommend_tier(report, available_ram_gb=6.0)
"""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic corpus — minimal IPA feedback prompts
# ---------------------------------------------------------------------------

_SYNTHETIC_PROMPTS: list[str] = [
    (
        "You are an IPA pronunciation coach. "
        "Respond ONLY with valid JSON matching: "
        '{"summary":str,"advice_short":str,"advice_long":str,"drills":[{"type":str,"text":str}]}. '
        "Error: ref=[s a l] hyp=[z a l]. Give feedback."
    ),
    (
        "IPA coach. JSON only: "
        '{"summary":str,"advice_short":str,"advice_long":str,"drills":[{"type":str,"text":str}]}. '
        "Error: ref=[ɾ] hyp=[r]. Trill vs tap. Give feedback."
    ),
    (
        "IPA coach. JSON only: "
        '{"summary":str,"advice_short":str,"advice_long":str,"drills":[{"type":str,"text":str}]}. '
        "Error: ref=[θ] hyp=[s]. Dental vs alveolar. Give feedback."
    ),
    (
        "IPA coach. JSON only: "
        '{"summary":str,"advice_short":str,"advice_long":str,"drills":[{"type":str,"text":str}]}. '
        "No error detected. PER=0.0. Congratulate learner."
    ),
    (
        "IPA coach. JSON only: "
        '{"summary":str,"advice_short":str,"advice_long":str,"drills":[{"type":str,"text":str}]}. '
        "Error: ref=[x] hyp=[h]. Velar vs glottal fricative. Give feedback."
    ),
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class AdapterBenchResult:
    """Benchmark result for a single adapter run."""

    adapter_name: str
    n_prompts: int
    n_valid_json: int
    json_valid_pct: float

    latency_median_ms: float
    latency_p95_ms: float
    latency_min_ms: float
    latency_max_ms: float

    rss_delta_mb: float          # memory added during benchmark (proxy)

    errors: List[str] = field(default_factory=list)
    raw_responses: List[str] = field(default_factory=list)

    @property
    def tier_fit(self) -> str:
        """Heuristic tier label based on latency and JSON validity."""
        if self.json_valid_pct >= 90 and self.latency_median_ms < 500:
            return "fast"
        if self.json_valid_pct >= 70 and self.latency_median_ms < 2000:
            return "ok"
        return "slow"


@dataclass
class BenchReport:
    """Full benchmark report (may contain multiple adapter results)."""

    results: List[AdapterBenchResult] = field(default_factory=list)
    recommended_tier: Optional[str] = None
    recommendation_reason: str = ""

    def best(self) -> Optional[AdapterBenchResult]:
        """Return the adapter result with the highest JSON valid % and lowest latency."""
        if not self.results:
            return None
        return max(
            self.results,
            key=lambda r: (r.json_valid_pct, -r.latency_median_ms),
        )

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

async def run_bench(
    adapter_name: str = "stub",
    *,
    n_prompts: Optional[int] = None,
    extra_params: Optional[Dict[str, Any]] = None,
) -> AdapterBenchResult:
    """Run the benchmark against a single named LLM adapter.

    Args:
        adapter_name: Name registered in the plugin registry (e.g. ``"stub"``,
            ``"ollama"``, ``"llama_cpp"``).
        n_prompts: How many synthetic prompts to run (default: all 5).
        extra_params: Extra params forwarded to the adapter constructor.

    Returns:
        AdapterBenchResult with all metrics.
    """
    prompts = _SYNTHETIC_PROMPTS[:n_prompts] if n_prompts else _SYNTHETIC_PROMPTS

    # -- Resolve adapter ---------------------------------------------------
    adapter = _load_adapter(adapter_name, extra_params or {})
    await adapter.setup()

    # -- Memory snapshot before -------------------------------------------
    rss_before_mb = _rss_mb()

    latencies: list[float] = []
    valid_count = 0
    errors: list[str] = []
    responses: list[str] = []

    for prompt in prompts:
        t0 = time.perf_counter()
        try:
            raw = await adapter.complete(prompt)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
            responses.append(raw[:200])  # truncated
            # Validate JSON
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    valid_count += 1
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"JSON parse error on prompt {len(latencies)}: {exc}")
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
            errors.append(f"Adapter error: {exc}")

    rss_after_mb = _rss_mb()
    await adapter.teardown()

    n = len(prompts)
    latencies_sorted = sorted(latencies)

    return AdapterBenchResult(
        adapter_name=adapter_name,
        n_prompts=n,
        n_valid_json=valid_count,
        json_valid_pct=round(100 * valid_count / n, 1) if n else 0.0,
        latency_median_ms=round(_percentile(latencies_sorted, 50), 1),
        latency_p95_ms=round(_percentile(latencies_sorted, 95), 1),
        latency_min_ms=round(min(latencies), 1) if latencies else 0.0,
        latency_max_ms=round(max(latencies), 1) if latencies else 0.0,
        rss_delta_mb=round(max(0.0, rss_after_mb - rss_before_mb), 1),
        errors=errors,
        raw_responses=responses,
    )


async def run_bench_all(
    adapter_names: List[str],
    *,
    n_prompts: Optional[int] = None,
    available_ram_gb: Optional[float] = None,
) -> BenchReport:
    """Benchmark multiple adapters sequentially and build a report.

    Also calls ``recommend_tier()`` if ``available_ram_gb`` is provided.
    """
    results: list[AdapterBenchResult] = []
    for name in adapter_names:
        try:
            result = await run_bench(name, n_prompts=n_prompts)
            results.append(result)
        except Exception as exc:
            logger.warning("Benchmark failed for adapter '%s': %s", name, exc)
            results.append(
                AdapterBenchResult(
                    adapter_name=name,
                    n_prompts=n_prompts or len(_SYNTHETIC_PROMPTS),
                    n_valid_json=0,
                    json_valid_pct=0.0,
                    latency_median_ms=0.0,
                    latency_p95_ms=0.0,
                    latency_min_ms=0.0,
                    latency_max_ms=0.0,
                    rss_delta_mb=0.0,
                    errors=[str(exc)],
                )
            )

    report = BenchReport(results=results)

    if available_ram_gb is not None:
        tier, reason = recommend_tier(results, available_ram_gb=available_ram_gb)
        report.recommended_tier = tier
        report.recommendation_reason = reason

    return report


# ---------------------------------------------------------------------------
# Tier recommendation
# ---------------------------------------------------------------------------

_RAM_TIER: list[tuple[float, str]] = [
    (8.0, "7B"),
    (4.0, "3B"),
    (2.0, "1B"),
]


def recommend_tier(
    results: List[AdapterBenchResult],
    *,
    available_ram_gb: float,
) -> tuple[str, str]:
    """Recommend a model tier given benchmark results and available RAM.

    Decision logic (priority order):
    1. If available RAM < 2 GB → "1B" (forced)
    2. Select highest tier whose min_ram_gb ≤ available_ram_gb
    3. Downgrade one tier if latency P95 > 3000 ms in the benchmark
    4. Downgrade one tier if JSON-valid rate < 70 %

    Returns:
        (tier_name, reason_string)
    """
    # RAM-based initial tier
    selected_tier = "1B"
    for min_gb, tier_name in _RAM_TIER:
        if available_ram_gb >= min_gb:
            selected_tier = tier_name
            break

    reason_parts = [f"RAM={available_ram_gb:.1f}GB → base tier {selected_tier}"]

    # Find the benchmark result with lowest latency/best quality
    if results:
        best = max(results, key=lambda r: (r.json_valid_pct, -r.latency_median_ms))

        # Penalize high latency: downgrade one tier
        if best.latency_p95_ms > 3000 and selected_tier != "1B":
            prev = selected_tier
            selected_tier = _downgrade(selected_tier)
            reason_parts.append(
                f"P95 latency {best.latency_p95_ms:.0f}ms > 3000ms → downgraded {prev}→{selected_tier}"
            )

        # Penalize low JSON validity: downgrade one tier
        if best.json_valid_pct < 70 and selected_tier != "1B":
            prev = selected_tier
            selected_tier = _downgrade(selected_tier)
            reason_parts.append(
                f"JSON valid {best.json_valid_pct:.0f}% < 70% → downgraded {prev}→{selected_tier}"
            )

    return selected_tier, "; ".join(reason_parts)


def _downgrade(tier: str) -> str:
    """Return one tier lower: 7B→3B, 3B→1B, 1B stays 1B."""
    order = ["1B", "3B", "7B"]
    idx = order.index(tier) if tier in order else 0
    return order[max(0, idx - 1)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_adapter(name: str, params: Dict[str, Any]):
    """Instantiate an LLM adapter by name from the plugin registry."""
    from ipa_core.llm.stub import StubLLMAdapter

    _KNOWN: dict[str, Any] = {
        "stub": StubLLMAdapter,
    }

    # Attempt dynamic import from registry
    try:
        from ipa_core.plugins.registry import PluginRegistry  # type: ignore[attr-defined]

        registry = PluginRegistry.get_instance()
        cls = registry.get("llm", name)
        return cls(params)
    except Exception:
        pass

    # Fallback to known map
    if name in _KNOWN:
        return _KNOWN[name](params)

    # Last resort: stub
    logger.warning("Adapter '%s' not found; using StubLLMAdapter", name)
    return StubLLMAdapter(params)


def _rss_mb() -> float:
    """Return current process RSS in MB (0.0 if psutil not available)."""
    try:
        import os
        import psutil  # type: ignore[import]

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def _percentile(sorted_data: list, pct: float) -> float:
    """Compute percentile of a pre-sorted list (0–100)."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    idx = (pct / 100) * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="PronunciaPA LLM bench")
    parser.add_argument(
        "--adapters",
        nargs="+",
        default=["stub"],
        help="Adapter names to benchmark (default: stub)",
    )
    parser.add_argument("--prompts", type=int, default=None, help="Number of prompts")
    parser.add_argument("--ram", type=float, default=None, help="Available RAM in GB")
    args = parser.parse_args()

    report = asyncio.run(
        run_bench_all(args.adapters, n_prompts=args.prompts, available_ram_gb=args.ram)
    )

    print("\n=== PronunciaPA LLM Benchmark ===\n")
    for r in report.results:
        print(f"Adapter : {r.adapter_name}")
        print(f"  JSON valid : {r.json_valid_pct:.1f}%  ({r.n_valid_json}/{r.n_prompts})")
        print(f"  Latency    : median={r.latency_median_ms:.0f}ms  P95={r.latency_p95_ms:.0f}ms")
        print(f"  RSS delta  : {r.rss_delta_mb:.1f} MB")
        if r.errors:
            print(f"  Errors     : {len(r.errors)} (first: {r.errors[0][:80]})")
        print()

    if report.recommended_tier:
        print(f"Recommended tier : {report.recommended_tier}")
        print(f"Reason           : {report.recommendation_reason}")


if __name__ == "__main__":
    main()


__all__ = [
    "AdapterBenchResult",
    "BenchReport",
    "run_bench",
    "run_bench_all",
    "recommend_tier",
]
