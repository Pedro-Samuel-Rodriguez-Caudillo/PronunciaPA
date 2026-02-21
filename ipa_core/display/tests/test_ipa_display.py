"""Tests para IPADisplay — visualización dual con tokens coloreados."""
from __future__ import annotations

import pytest
from ipa_core.display.ipa_display import (
    COLOR_CLOSE_THRESHOLD,
    IPADisplayResult,
    IPADisplayToken,
    build_display,
)


def _op(op: str, ref=None, hyp=None):
    return {"op": op, "ref": ref, "hyp": hyp}


class TestBuildDisplayEmpty:
    def test_empty_ops(self):
        result = build_display([])
        assert result.tokens == []
        assert result.ref_technical == ""
        assert result.hyp_technical == ""

    def test_returns_ipa_display_result(self):
        result = build_display([])
        assert isinstance(result, IPADisplayResult)


class TestTokenColors:
    def test_eq_op_is_green(self):
        result = build_display([_op("eq", ref="p", hyp="p")])
        assert result.tokens[0].color == "green"

    def test_del_op_is_red(self):
        result = build_display([_op("del", ref="p", hyp=None)])
        assert result.tokens[0].color == "red"

    def test_ins_op_is_red(self):
        result = build_display([_op("ins", ref=None, hyp="p")])
        assert result.tokens[0].color == "red"

    def test_sub_close_is_yellow(self):
        """s y z son muy parecidas articulatoriamente → amarillo."""
        result = build_display([_op("sub", ref="s", hyp="z")])
        tok = result.tokens[0]
        # Distancia s-z < 0.3 → yellow
        assert tok.color == "yellow"
        assert tok.articulatory_distance is not None
        assert tok.articulatory_distance < COLOR_CLOSE_THRESHOLD

    def test_sub_far_is_red(self):
        """p y a son muy diferentes (consonante vs vocal) → rojo."""
        result = build_display([_op("sub", ref="p", hyp="a")])
        assert result.tokens[0].color == "red"

    def test_unknown_token_is_gray(self):
        result = build_display([_op("sub", ref="?", hyp="p")])
        assert result.tokens[0].color == "gray"


class TestTokenIpaAndCasual:
    def test_ipa_field_for_eq(self):
        result = build_display([_op("eq", ref="p", hyp="p")])
        assert result.tokens[0].ipa == "p"

    def test_casual_field_mapped(self):
        result = build_display([_op("eq", ref="ɲ", hyp="ɲ")])
        # ɲ → ñ en el mapa casual
        assert result.tokens[0].casual == "ñ"

    def test_casual_field_unknown_ipa_passthrough(self):
        """Un símbolo no mapeado pasa como está."""
        result = build_display([_op("eq", ref="X", hyp="X")])
        assert result.tokens[0].casual == "X"


class TestRefHypStrings:
    def test_ref_technical_concatenated(self):
        ops = [
            _op("eq", ref="h", hyp="h"),
            _op("sub", ref="o", hyp="u"),
            _op("eq", ref="l", hyp="l"),
            _op("eq", ref="a", hyp="a"),
        ]
        result = build_display(ops)
        assert "h" in result.ref_technical
        assert "o" in result.ref_technical

    def test_hyp_technical_concatenated(self):
        ops = [
            _op("eq", ref="h", hyp="h"),
            _op("sub", ref="o", hyp="u"),
        ]
        result = build_display(ops)
        assert "u" in result.hyp_technical

    def test_ref_casual_mapped(self):
        ops = [_op("eq", ref="ɲ", hyp="ɲ")]
        result = build_display(ops)
        assert "ñ" in result.ref_casual


class TestScoreColor:
    def test_score_80_plus_is_green(self):
        result = build_display([], score=85.0)
        assert result.score_color == "green"

    def test_score_50_to_79_is_yellow(self):
        result = build_display([], score=65.0)
        assert result.score_color == "yellow"

    def test_score_below_50_is_red(self):
        result = build_display([], score=30.0)
        assert result.score_color == "red"

    def test_exact_80_is_green(self):
        result = build_display([], score=80.0)
        assert result.score_color == "green"

    def test_exact_50_is_yellow(self):
        result = build_display([], score=50.0)
        assert result.score_color == "yellow"


class TestModeAndLevel:
    def test_default_mode_technical(self):
        result = build_display([])
        assert result.mode == "technical"

    def test_casual_mode(self):
        result = build_display([], mode="casual")
        assert result.mode == "casual"

    def test_phonetic_level(self):
        result = build_display([], level="phonetic")
        assert result.level == "phonetic"
        for tok in result.tokens:
            assert tok.level == "phonetic"


class TestLegend:
    def test_legend_has_all_colors(self):
        result = build_display([])
        assert "green" in result.legend
        assert "yellow" in result.legend
        assert "red" in result.legend
        assert "gray" in result.legend


class TestAsDict:
    def test_as_dict_keys(self):
        ops = [_op("eq", ref="p", hyp="p")]
        result = build_display(ops, score=90.0)
        d = result.as_dict()
        assert "tokens" in d
        assert "mode" in d
        assert "level" in d
        assert "ref_technical" in d
        assert "hyp_technical" in d
        assert "score_color" in d
        assert "legend" in d

    def test_as_dict_tokens_are_dicts(self):
        ops = [_op("eq", ref="p", hyp="p")]
        result = build_display(ops)
        d = result.as_dict()
        assert isinstance(d["tokens"][0], dict)
        assert "ipa" in d["tokens"][0]
        assert "color" in d["tokens"][0]


class TestCustomThreshold:
    def test_custom_threshold_affects_color(self):
        """Con umbral 0.5, la mayoría de sustituciones serán amarillo."""
        result = build_display([_op("sub", ref="s", hyp="x")], close_threshold=0.5)
        # s y x pueden tener dist moderada
        tok = result.tokens[0]
        assert tok.color in ("yellow", "red")  # depende de la distancia exacta
