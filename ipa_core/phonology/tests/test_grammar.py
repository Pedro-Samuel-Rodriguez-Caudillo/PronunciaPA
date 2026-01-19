"""Tests para rule.py y grammar.py."""
from __future__ import annotations

import pytest
from pathlib import Path

from ipa_core.phonology.rule import (
    PhonologicalRule,
    SPIRANTIZATION_ES,
    SESEO_ES,
    YEISMO_ES,
)
from ipa_core.phonology.grammar import (
    PhonologicalGrammar,
    create_spanish_mexican_grammar,
)
from ipa_core.phonology.inventory import PhoneticInventory


class TestPhonologicalRule:
    """Tests para PhonologicalRule."""
    
    def test_create_rule(self) -> None:
        """Crear regla básica."""
        rule = PhonologicalRule(
            name="Test",
            input_segments=["a"],
            output_segments=["b"],
        )
        assert rule.name == "Test"
        assert rule.can_apply("a")
        assert not rule.can_apply("c")
    
    def test_simple_transform(self) -> None:
        """Transformación simple sin contexto."""
        rule = PhonologicalRule(
            name="a→b",
            input_segments=["a"],
            output_segments=["b"],
        )
        assert rule.apply("casa") == "cbsb"
    
    def test_multiple_segments(self) -> None:
        """Regla con múltiples segmentos."""
        rule = PhonologicalRule(
            name="Devoicing",
            input_segments=["b", "d", "g"],
            output_segments=["p", "t", "k"],
        )
        assert rule.apply("dog") == "tok"
    
    def test_left_context(self) -> None:
        """Regla con contexto izquierdo."""
        rule = PhonologicalRule(
            name="Post-vocalic",
            input_segments=["b"],
            output_segments=["β"],
            left_context="[aeiou]",
        )
        # b después de vocal → β
        assert rule.apply("aba") == "aβa"
        # b inicial no cambia
        assert rule.apply("ba") == "ba"
    
    def test_right_context(self) -> None:
        """Regla con contexto derecho."""
        rule = PhonologicalRule(
            name="Pre-vocalic",
            input_segments=["k"],
            output_segments=["tʃ"],
            right_context="[ei]",
        )
        # k antes de e/i → tʃ
        assert rule.apply("ke") == "tʃe"
        assert rule.apply("ka") == "ka"
    
    def test_both_contexts(self) -> None:
        """Regla con ambos contextos."""
        rule = PhonologicalRule(
            name="Intervocalic",
            input_segments=["d"],
            output_segments=["ð"],
            left_context="[aeiou]",
            right_context="[aeiou]",
        )
        assert rule.apply("ada") == "aða"
        assert rule.apply("da") == "da"
        assert rule.apply("ad") == "ad"
    
    def test_mismatch_lengths_error(self) -> None:
        """Error si input y output tienen diferente longitud."""
        with pytest.raises(ValueError):
            PhonologicalRule(
                name="Bad",
                input_segments=["a", "b"],
                output_segments=["c"],
            )


class TestPredefinedRules:
    """Tests para reglas predefinidas."""
    
    def test_spirantization(self) -> None:
        """Espirantización española."""
        rule = SPIRANTIZATION_ES
        assert rule.apply("aba") == "aβa"
        assert rule.apply("odo") == "oðo"
        assert rule.apply("aga") == "aɣa"
        # No aplica al inicio
        assert rule.apply("ba") == "ba"
    
    def test_seseo(self) -> None:
        """Seseo."""
        rule = SESEO_ES
        assert rule.apply("θena") == "sena"
        assert rule.apply("kaθa") == "kasa"
    
    def test_yeismo(self) -> None:
        """Yeísmo."""
        rule = YEISMO_ES
        assert rule.apply("kaʎe") == "kaʝe"


class TestPhonologicalGrammar:
    """Tests para PhonologicalGrammar."""
    
    @pytest.fixture
    def spanish_grammar(self) -> PhonologicalGrammar:
        """Gramática de español mexicano."""
        return create_spanish_mexican_grammar()
    
    def test_create_grammar(self) -> None:
        """Crear gramática vacía."""
        g = PhonologicalGrammar(language="es", dialect="es-mx")
        assert g.language == "es"
        assert len(g.rules) == 0
    
    def test_add_rule_orders(self) -> None:
        """Reglas se ordenan por order."""
        g = PhonologicalGrammar(language="test", dialect="test")
        r1 = PhonologicalRule(name="Late", input_segments=["a"], output_segments=["b"], order=10)
        r2 = PhonologicalRule(name="Early", input_segments=["c"], output_segments=["d"], order=1)
        g.add_rule(r1)
        g.add_rule(r2)
        assert g.rules[0].name == "Early"
        assert g.rules[1].name == "Late"
    
    def test_derive_applies_rules(self, spanish_grammar: PhonologicalGrammar) -> None:
        """derive() aplica reglas en orden."""
        # dedo → deðo (espirantización de d intervocálica)
        result = spanish_grammar.derive("dedo")
        assert "ð" in result
    
    def test_derive_seseo(self, spanish_grammar: PhonologicalGrammar) -> None:
        """derive() aplica seseo."""
        result = spanish_grammar.derive("θena")
        assert result == "sena"
    
    def test_collapse_basic(self) -> None:
        """collapse() revierte alófonos."""
        inv = PhoneticInventory(language="es", dialect="es-mx")
        inv.add_phoneme("b")
        inv.add_allophone("β", "b")
        
        g = PhonologicalGrammar(language="es", dialect="es-mx", inventory=inv)
        
        result = g.collapse("[aβa]")
        assert result == "aba"
    
    def test_collapse_strips_diacritics(self) -> None:
        """collapse() elimina diacríticos."""
        g = PhonologicalGrammar(language="es", dialect="es-mx")
        result = g.collapse("[ˈka.sa]")
        assert result == "kasa"


class TestGrammarYAML:
    """Tests para carga/guardado YAML."""
    
    def test_from_yaml(self, tmp_path: Path) -> None:
        """Cargar gramática desde YAML."""
        yaml_content = """
language: es
dialect: es-mx
rules:
  - name: "Seseo"
    input: ["θ"]
    output: ["s"]
    order: 0
  - name: "Spirantization"
    input: ["b", "d", "g"]
    output: ["β", "ð", "ɣ"]
    left: "[aeiou]"
    order: 1
"""
        yaml_path = tmp_path / "grammar.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")
        
        g = PhonologicalGrammar.from_yaml(yaml_path)
        assert g.language == "es"
        assert len(g.rules) == 2
        assert g.rules[0].name == "Seseo"  # order 0 primero
