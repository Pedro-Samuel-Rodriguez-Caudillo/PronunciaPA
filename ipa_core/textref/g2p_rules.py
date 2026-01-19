"""Motor de reglas G2P (Grapheme-to-Phoneme) sensibles al contexto.

Permite definir reglas de conversión grafema→fonema que dependen
del contexto (caracteres anteriores/posteriores), reduciendo la
necesidad de léxicos manuales extensos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ipa_core.errors import ValidationError


@dataclass
class G2PRule:
    """Regla de conversión grafema a fonema.
    
    Atributos
    ---------
    grapheme : str
        Grafema(s) a convertir (puede ser múltiple, ej: "ph", "tion").
    phoneme : str
        Fonema(s) IPA resultante(s).
    left_context : str
        Regex para contexto izquierdo (antes del grafema).
        Vacío = cualquier contexto.
    right_context : str
        Regex para contexto derecho (después del grafema).
        Vacío = cualquier contexto.
    priority : int
        Prioridad de la regla (mayor = se evalúa primero).
    comment : str
        Descripción de la regla.
    """
    grapheme: str
    phoneme: str
    left_context: str = ""
    right_context: str = ""
    priority: int = 0
    comment: str = ""
    
    def __post_init__(self) -> None:
        # Compilar regexes de contexto
        self._left_re = re.compile(f"({self.left_context})$") if self.left_context else None
        self._right_re = re.compile(f"^({self.right_context})") if self.right_context else None
    
    def matches(self, word: str, position: int) -> bool:
        """Verificar si la regla aplica en esta posición.
        
        Parámetros
        ----------
        word : str
            Palabra completa (en minúsculas).
        position : int
            Posición donde comienza el grafema.
            
        Retorna
        -------
        bool
            True si la regla aplica.
        """
        # Verificar que el grafema coincide
        end_pos = position + len(self.grapheme)
        if word[position:end_pos] != self.grapheme.lower():
            return False
        
        # Verificar contexto izquierdo
        if self._left_re:
            left_text = word[:position]
            if not self._left_re.search(left_text):
                return False
        
        # Verificar contexto derecho
        if self._right_re:
            right_text = word[end_pos:]
            if not self._right_re.match(right_text):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        d = {"grapheme": self.grapheme, "phoneme": self.phoneme}
        if self.left_context:
            d["left"] = self.left_context
        if self.right_context:
            d["right"] = self.right_context
        if self.priority:
            d["priority"] = self.priority
        if self.comment:
            d["comment"] = self.comment
        return d


@dataclass
class G2PRuleset:
    """Conjunto de reglas G2P para un idioma/dialecto.
    
    Atributos
    ---------
    language : str
        Código de idioma.
    dialect : str
        Código de dialecto.
    rules : list[G2PRule]
        Reglas ordenadas por prioridad.
    exceptions : dict[str, str]
        Diccionario de excepciones (palabra → IPA).
    """
    language: str
    dialect: str
    rules: List[G2PRule] = field(default_factory=list)
    exceptions: Dict[str, str] = field(default_factory=dict)
    
    def add_rule(self, rule: G2PRule) -> None:
        """Añadir regla y reordenar por prioridad."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: (-r.priority, -len(r.grapheme)))
    
    def add_exception(self, word: str, ipa: str) -> None:
        """Añadir excepción al léxico."""
        self.exceptions[word.lower()] = ipa
    
    @classmethod
    def from_yaml(cls, path: Path) -> "G2PRuleset":
        """Cargar ruleset desde archivo YAML."""
        if not path.exists():
            raise ValidationError(f"Rules file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        ruleset = cls(
            language=data.get("language", ""),
            dialect=data.get("dialect", ""),
        )
        
        # Cargar reglas
        for rule_data in data.get("rules", []):
            rule = G2PRule(
                grapheme=rule_data["grapheme"],
                phoneme=rule_data["phoneme"],
                left_context=rule_data.get("left", ""),
                right_context=rule_data.get("right", ""),
                priority=rule_data.get("priority", 0),
                comment=rule_data.get("comment", ""),
            )
            ruleset.add_rule(rule)
        
        # Cargar excepciones
        for word, ipa in data.get("exceptions", {}).items():
            ruleset.add_exception(word, ipa)
        
        return ruleset
    
    def to_yaml(self, path: Path) -> None:
        """Guardar ruleset a archivo YAML."""
        data = {
            "language": self.language,
            "dialect": self.dialect,
            "rules": [r.to_dict() for r in self.rules],
            "exceptions": self.exceptions,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)


class G2PRulesEngine:
    """Motor de conversión G2P basado en reglas.
    
    Aplica reglas sensibles al contexto para convertir
    texto a IPA, consultando excepciones primero.
    """
    
    def __init__(self, ruleset: G2PRuleset) -> None:
        self._ruleset = ruleset
    
    @classmethod
    def from_yaml(cls, path: Path) -> "G2PRulesEngine":
        """Crear engine desde archivo YAML."""
        ruleset = G2PRuleset.from_yaml(path)
        return cls(ruleset)
    
    def convert(self, word: str) -> str:
        """Convertir palabra a IPA.
        
        Parámetros
        ----------
        word : str
            Palabra a convertir.
            
        Retorna
        -------
        str
            Transcripción IPA.
        """
        word_lower = word.lower().strip()
        
        # 1. Buscar en excepciones primero
        if word_lower in self._ruleset.exceptions:
            return self._ruleset.exceptions[word_lower]
        
        # 2. Aplicar reglas
        result = []
        pos = 0
        
        while pos < len(word_lower):
            matched = False
            
            # Buscar regla que aplique (ya ordenadas por prioridad y longitud)
            for rule in self._ruleset.rules:
                if pos + len(rule.grapheme) <= len(word_lower):
                    if rule.matches(word_lower, pos):
                        result.append(rule.phoneme)
                        pos += len(rule.grapheme)
                        matched = True
                        break
            
            if not matched:
                # No hay regla: copiar carácter o marcar como desconocido
                char = word_lower[pos]
                if char.isalpha():
                    result.append(f"?{char}?")  # Marcar como no mapeado
                # Ignorar espacios, puntuación, etc.
                pos += 1
        
        return "".join(result)
    
    def convert_text(self, text: str) -> List[Tuple[str, str]]:
        """Convertir texto completo a IPA.
        
        Parámetros
        ----------
        text : str
            Texto a convertir.
            
        Retorna
        -------
        list[tuple[str, str]]
            Lista de (palabra, IPA).
        """
        words = re.findall(r'\b\w+\b', text)
        return [(word, self.convert(word)) for word in words]
    
    def get_unmapped_graphemes(self, word: str) -> List[str]:
        """Obtener grafemas que no tienen regla."""
        ipa = self.convert(word)
        unmapped = re.findall(r'\?(.)\?', ipa)
        return unmapped
    
    @property
    def ruleset(self) -> G2PRuleset:
        """Obtener el ruleset."""
        return self._ruleset


__all__ = [
    "G2PRule",
    "G2PRuleset",
    "G2PRulesEngine",
]
