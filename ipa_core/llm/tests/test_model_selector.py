"""Tests para ModelSelector — detección de RAM y selección de tier LLM."""
from __future__ import annotations

import pytest
from ipa_core.llm.model_selector import (
    ModelTier,
    _STUB_TIER,
    _TIERS,
    get_runtime_config,
    recommend_model,
    select_tier,
)


class TestSelectTier:
    def test_zero_ram_returns_stub(self):
        tier = select_tier(0.0)
        assert tier.name == "stub"

    def test_1gb_ram_returns_stub(self):
        """Menos de 2 GB → stub (no alcanza el tier 1B)."""
        tier = select_tier(1.0)
        assert tier.name == "stub"

    def test_2gb_ram_returns_1b(self):
        tier = select_tier(2.5)
        assert tier.name == "1B"

    def test_4gb_ram_returns_3b(self):
        tier = select_tier(5.0)
        assert tier.name == "3B"

    def test_8gb_ram_returns_7b(self):
        tier = select_tier(10.0)
        assert tier.name == "7B"

    def test_large_ram_returns_7b(self):
        """Mucha RAM siempre devuelve el tier más exigente disponible (7B)."""
        tier = select_tier(64.0)
        assert tier.name == "7B"

    def test_exact_boundary_1b(self):
        """Exactamente en el límite mínimo del tier 1B."""
        tier = select_tier(2.0)
        assert tier.name == "1B"

    def test_exact_boundary_3b(self):
        tier = select_tier(4.0)
        assert tier.name == "3B"

    def test_exact_boundary_7b(self):
        tier = select_tier(8.0)
        assert tier.name == "7B"


class TestModelTierStructure:
    def test_all_tiers_have_suggested_models(self):
        for tier in _TIERS:
            assert len(tier.suggested_models) > 0, f"Tier {tier.name} sin modelos sugeridos"

    def test_tiers_ordered_by_ram(self):
        rams = [t.min_ram_gb for t in _TIERS]
        assert rams == sorted(rams), "Los tiers deben estar ordenados por RAM ascendente"

    def test_stub_tier_zero_ram(self):
        assert _STUB_TIER.min_ram_gb == 0.0
        assert _STUB_TIER.name == "stub"

    def test_tier_ctx_sizes_positive(self):
        for tier in _TIERS:
            assert tier.ctx_size > 0


class TestGetRuntimeConfig:
    def test_stub_tier_returns_stub_kind(self):
        config = get_runtime_config(_STUB_TIER)
        assert config["kind"] == "stub"

    def test_1b_tier_returns_llama_cpp(self):
        tier_1b = next(t for t in _TIERS if t.name == "1B")
        config = get_runtime_config(tier_1b)
        assert config["kind"] == "llama_cpp"
        assert "model_path" in config["params"]
        assert "n_ctx" in config["params"]

    def test_7b_tier_has_larger_context(self):
        tier_7b = next(t for t in _TIERS if t.name == "7B")
        tier_1b = next(t for t in _TIERS if t.name == "1B")
        config_7b = get_runtime_config(tier_7b)
        config_1b = get_runtime_config(tier_1b)
        assert config_7b["params"]["n_ctx"] >= config_1b["params"]["n_ctx"]


class TestRecommendModel:
    def test_non_interactive_returns_tier(self):
        tier = recommend_model(ram_override_gb=6.0)
        assert isinstance(tier, ModelTier)
        assert tier.name == "3B"

    def test_stub_when_no_ram(self):
        tier = recommend_model(ram_override_gb=0.5)
        assert tier.name == "stub"

    def test_7b_with_plenty_of_ram(self):
        tier = recommend_model(ram_override_gb=32.0)
        assert tier.name == "7B"
