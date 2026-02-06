"""Gramática fonológica - Conjunto ordenado de reglas.

La gramática aplica reglas en orden para derivar formas superficiales
desde subyacentes (derive) o para colapsar formas superficiales a
subyacentes (collapse).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ipa_core.phonology.rule import PhonologicalRule
from ipa_core.phonology.inventory import PhoneticInventory
from ipa_core.phonology.representation import tokenize_ipa


@dataclass
class PhonologicalGrammar:
    """Gramática fonológica de un dialecto.
    
    Atributos
    ---------
    language : str
        Código de idioma.
    dialect : str
        Código de dialecto.
    rules : List[PhonologicalRule]
        Reglas ordenadas por orden de aplicación.
    inventory : Optional[PhoneticInventory]
        Inventario fonético asociado.
    """
    language: str
    dialect: str
    rules: List[PhonologicalRule] = field(default_factory=list)
    inventory: Optional[PhoneticInventory] = None
    
    def add_rule(self, rule: PhonologicalRule) -> None:
        """Añadir regla y reordenar."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.order)
    
    def derive(
        self, 
        underlying: str, 
        *, 
        mode: str = "all",
        register: str = "all",
    ) -> str:
        """Derivar forma superficial desde subyacente.
        
        Aplica reglas en orden para transformar la representación
        fonémica (subyacente) a fonética (superficial).
        
        Parámetros
        ----------
        underlying : str
            Forma subyacente (fonémica), ej: "/kasa/".
        mode : str
            Modo de aplicación: "all", "casual", "objective", "phonetic".
        register : str
            Registro: "all", "formal", "informal".
            
        Retorna
        -------
        str
            Forma superficial (fonética), ej: "[ˈka.sa]".
        """
        # Limpiar delimitadores
        result = underlying.strip("/[]")

        for rule in self.rules:
            # Filtrar por register si no es "all"
            if register != "all" and rule.register != "all":
                if rule.register != register:
                    continue

            # Saltar reglas opcionales en modo estricto
            if mode == "phonetic" and rule.optional:
                continue

            result = rule.apply(result)

        return result
    
    def collapse(
        self, 
        surface: str,
        *,
        mode: str = "all",
    ) -> str:
        """Colapsar forma superficial a subyacente.
        
        Revierte alófonos a sus fonemas base usando el inventario.
        
        Parámetros
        ----------
        surface : str
            Forma superficial (fonética), ej: "[ˈka.sa]".
        mode : str
            Modo: afecta qué tanto se colapsa.
            
        Retorna
        -------
        str
            Forma subyacente (fonémica), ej: "/kasa/".
        """
        # Limpiar delimitadores y diacríticos comunes
        result = surface.strip("/[]")
        result = result.replace("ˈ", "").replace("ˌ", "").replace(".", "")

        # Aplicar reglas en orden inverso (cuando sea invertible)
        for rule in reversed(self.rules):
            # Si la regla era opcional y estamos en modo permisivo, igual podemos revertir
            if rule.optional and mode == "casual":
                continue  # dejamos variación libre sin colapsar
            result = rule.apply_inverse(result)

        if self.inventory is None:
            return result

        # Colapsar segmento a segmento usando inventario
        collapsed = []
        for seg in tokenize_ipa(result):
            base = self.inventory.collapse_to_phoneme(seg)
            collapsed.append(base)

        return "".join(collapsed)
    
    @classmethod
    def from_yaml(cls, path: Path, inventory: Optional[PhoneticInventory] = None) -> "PhonologicalGrammar":
        """Cargar gramática desde archivo YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        grammar = cls(
            language=data.get("language", ""),
            dialect=data.get("dialect", ""),
            inventory=inventory,
        )
        
        for rule_data in data.get("rules", []):
            rule = PhonologicalRule(
                name=rule_data.get("name", ""),
                input_segments=rule_data.get("input", []),
                output_segments=rule_data.get("output", []),
                left_context=rule_data.get("left", ""),
                right_context=rule_data.get("right", ""),
                order=rule_data.get("order", 0),
                optional=rule_data.get("optional", False),
                register=rule_data.get("register", "all"),
                description=rule_data.get("description", ""),
            )
            grammar.add_rule(rule)
        
        return grammar
    
    def to_yaml(self) -> str:
        """Serializar a YAML."""
        data = {
            "language": self.language,
            "dialect": self.dialect,
            "rules": [r.to_dict() for r in self.rules],
        }
        return yaml.dump(data, allow_unicode=True, sort_keys=False)


# Gramática predefinida para español mexicano
def create_spanish_mexican_grammar(inventory: Optional[PhoneticInventory] = None) -> PhonologicalGrammar:
    """Crear gramática de español mexicano con reglas comunes."""
    from ipa_core.phonology.rule import (
        SPIRANTIZATION_ES,
        NASAL_VELAR_ASSIMILATION_ES,
        SESEO_ES,
        YEISMO_ES,
        D_ELISION_ES,
    )
    
    grammar = PhonologicalGrammar(
        language="es",
        dialect="es-mx",
        inventory=inventory,
    )
    
    grammar.add_rule(SESEO_ES)
    grammar.add_rule(YEISMO_ES)
    grammar.add_rule(SPIRANTIZATION_ES)
    grammar.add_rule(NASAL_VELAR_ASSIMILATION_ES)
    grammar.add_rule(D_ELISION_ES)
    
    return grammar


__all__ = [
    "PhonologicalGrammar",
    "create_spanish_mexican_grammar",
]
