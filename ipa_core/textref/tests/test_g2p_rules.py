"""Tests para el motor de reglas G2P."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from ipa_core.textref.g2p_rules import (
    G2PRule,
    G2PRuleset,
    G2PRulesEngine,
)


class TestG2PRule:
    """Tests para G2PRule."""
    
    def test_simple_rule_matches(self) -> None:
        """Regla simple sin contexto."""
        rule = G2PRule(grapheme="a", phoneme="a")
        assert rule.matches("casa", 1) is True
        assert rule.matches("casa", 3) is True
    
    def test_rule_with_right_context(self) -> None:
        """Regla con contexto derecho."""
        rule = G2PRule(grapheme="c", phoneme="s", right_context="[ei]")
        assert rule.matches("cena", 0) is True  # c antes de e
        assert rule.matches("casa", 0) is False  # c antes de a
    
    def test_rule_with_left_context(self) -> None:
        """Regla con contexto izquierdo."""
        rule = G2PRule(grapheme="r", phoneme="r", left_context="^")
        assert rule.matches("rosa", 0) is True  # r inicial
        assert rule.matches("caro", 2) is False  # r no inicial
    
    def test_rule_with_both_contexts(self) -> None:
        """Regla con ambos contextos."""
        rule = G2PRule(grapheme="e", phoneme="", left_context="[^aeiou]", right_context="$")
        assert rule.matches("like", 3) is True  # e muda final
    
    def test_multigraph_rule(self) -> None:
        """Regla con múltiples grafemas."""
        rule = G2PRule(grapheme="ch", phoneme="tʃ")
        assert rule.matches("chocolate", 0) is True
        assert rule.matches("chocolate", 1) is False  # posición incorrecta
    
    def test_to_dict(self) -> None:
        """Conversión a diccionario."""
        rule = G2PRule(grapheme="c", phoneme="s", right_context="[ei]", priority=10)
        d = rule.to_dict()
        assert d["grapheme"] == "c"
        assert d["phoneme"] == "s"
        assert d["right"] == "[ei]"
        assert d["priority"] == 10


class TestG2PRuleset:
    """Tests para G2PRuleset."""
    
    @pytest.fixture
    def simple_ruleset(self) -> G2PRuleset:
        """Ruleset simple para testing."""
        ruleset = G2PRuleset(language="es", dialect="es-mx")
        ruleset.add_rule(G2PRule(grapheme="a", phoneme="a"))
        ruleset.add_rule(G2PRule(grapheme="c", phoneme="s", right_context="[ei]", priority=10))
        ruleset.add_rule(G2PRule(grapheme="c", phoneme="k"))
        ruleset.add_exception("méxico", "ˈmexiko")
        return ruleset
    
    def test_rules_sorted_by_priority(self, simple_ruleset: G2PRuleset) -> None:
        """Reglas ordenadas por prioridad descendente."""
        # La regla c→s (priority 10) debe estar antes que c→k (priority 0)
        c_rules = [r for r in simple_ruleset.rules if r.grapheme == "c"]
        assert c_rules[0].phoneme == "s"
        assert c_rules[1].phoneme == "k"
    
    def test_exception_added(self, simple_ruleset: G2PRuleset) -> None:
        """Excepción añadida correctamente."""
        assert "méxico" in simple_ruleset.exceptions
    
    def test_from_yaml(self, tmp_path: Path) -> None:
        """Carga desde YAML."""
        yaml_content = """
language: test
dialect: test-1
rules:
  - grapheme: a
    phoneme: ɑ
  - grapheme: b
    phoneme: b
    priority: 5
exceptions:
  hello: həˈloʊ
"""
        yaml_path = tmp_path / "rules.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")
        
        ruleset = G2PRuleset.from_yaml(yaml_path)
        assert ruleset.language == "test"
        assert len(ruleset.rules) == 2
        assert "hello" in ruleset.exceptions


class TestG2PRulesEngine:
    """Tests para G2PRulesEngine."""
    
    @pytest.fixture
    def spanish_engine(self) -> G2PRulesEngine:
        """Engine con reglas básicas de español."""
        ruleset = G2PRuleset(language="es", dialect="es-mx")
        # Vocales
        for v in "aeiou":
            ruleset.add_rule(G2PRule(grapheme=v, phoneme=v))
        # C con contexto
        ruleset.add_rule(G2PRule(grapheme="c", phoneme="s", right_context="[ei]", priority=10))
        ruleset.add_rule(G2PRule(grapheme="c", phoneme="k"))
        # Otras consonantes
        for c, p in [("s", "s"), ("n", "n"), ("l", "l")]:
            ruleset.add_rule(G2PRule(grapheme=c, phoneme=p))
        # Excepción
        ruleset.add_exception("méxico", "ˈmexiko")
        return G2PRulesEngine(ruleset)
    
    def test_exception_takes_precedence(self, spanish_engine: G2PRulesEngine) -> None:
        """Excepciones tienen prioridad sobre reglas."""
        result = spanish_engine.convert("méxico")
        assert result == "ˈmexiko"
    
    def test_simple_conversion(self, spanish_engine: G2PRulesEngine) -> None:
        """Conversión simple de palabra regular."""
        result = spanish_engine.convert("casa")
        assert result == "kasa"
    
    def test_context_sensitive_c(self, spanish_engine: G2PRulesEngine) -> None:
        """C sensible al contexto."""
        assert spanish_engine.convert("cena") == "sena"  # c + e → s
        assert spanish_engine.convert("casa") == "kasa"  # c + a → k
    
    def test_convert_text(self, spanish_engine: G2PRulesEngine) -> None:
        """Conversión de texto completo."""
        results = spanish_engine.convert_text("la casa")
        assert len(results) == 2
        assert results[0] == ("la", "la")
        assert results[1] == ("casa", "kasa")
    
    def test_unmapped_graphemes(self, spanish_engine: G2PRulesEngine) -> None:
        """Detecta grafemas sin regla."""
        result = spanish_engine.convert("xyz")
        unmapped = spanish_engine.get_unmapped_graphemes("xyz")
        assert "x" in unmapped
        assert "y" in unmapped
        assert "z" in unmapped


class TestRealRulesFiles:
    """Tests para archivos de reglas reales."""
    
    PACKS_DIR = Path(__file__).parent.parent.parent.parent / "plugins" / "language_packs"
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_rules_file_exists(self, pack_id: str) -> None:
        """Archivo de reglas existe."""
        rules_path = self.PACKS_DIR / pack_id / "g2p_rules.yaml"
        assert rules_path.exists(), f"Missing g2p_rules.yaml for {pack_id}"
    
    @pytest.mark.parametrize("pack_id", ["en-us", "es-mx"])
    def test_rules_load_successfully(self, pack_id: str) -> None:
        """Reglas cargan sin errores."""
        rules_path = self.PACKS_DIR / pack_id / "g2p_rules.yaml"
        ruleset = G2PRuleset.from_yaml(rules_path)
        assert len(ruleset.rules) > 0
    
    def test_spanish_rules_basic_words(self) -> None:
        """Reglas de español funcionan con palabras básicas."""
        rules_path = self.PACKS_DIR / "es-mx" / "g2p_rules.yaml"
        engine = G2PRulesEngine.from_yaml(rules_path)
        
        # Palabras regulares
        assert "k" in engine.convert("casa")  # c+a = k
        assert "s" in engine.convert("cena")  # c+e = s
        
        # Excepción
        assert engine.convert("méxico") == "ˈmexiko"
