"""Tipos de datos para ejercicios de pronunciación.

Define las estructuras de datos para drills, pares mínimos,
y sets de ejercicios generados por el G2P Generator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MinimalPair:
    """Par mínimo de palabras que difieren en un solo fonema.
    
    Atributos
    ---------
    word_a : str
        Primera palabra del par.
    word_b : str
        Segunda palabra del par.
    ipa_a : str
        Transcripción IPA de word_a.
    ipa_b : str
        Transcripción IPA de word_b.
    target_phone : str
        Fonema objetivo que difiere entre las palabras.
    contrast_phone : str
        Fonema contrastante.
    position : str
        Posición del contraste: "initial", "medial", "final".
    """
    word_a: str
    word_b: str
    ipa_a: str
    ipa_b: str
    target_phone: str
    contrast_phone: str
    position: str = "medial"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "word_a": self.word_a,
            "word_b": self.word_b,
            "ipa_a": self.ipa_a,
            "ipa_b": self.ipa_b,
            "target_phone": self.target_phone,
            "contrast_phone": self.contrast_phone,
            "position": self.position,
        }


@dataclass
class DrillItem:
    """Elemento individual de un drill de pronunciación.
    
    Atributos
    ---------
    text : str
        Texto a pronunciar.
    ipa : str
        Transcripción IPA del texto.
    target_phones : list[str]
        Fonemas objetivo para practicar.
    difficulty : int
        Nivel de dificultad (1-5).
    hints : list[str]
        Consejos para la pronunciación.
    """
    text: str
    ipa: str
    target_phones: List[str] = field(default_factory=list)
    difficulty: int = 1
    hints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "text": self.text,
            "ipa": self.ipa,
            "target_phones": self.target_phones,
            "difficulty": self.difficulty,
            "hints": self.hints,
        }


@dataclass
class DrillSet:
    """Conjunto de ejercicios de pronunciación.
    
    Atributos
    ---------
    name : str
        Nombre del set de ejercicios.
    description : str
        Descripción del objetivo del set.
    lang : str
        Código de idioma.
    target_phones : list[str]
        Fonemas objetivo del set completo.
    items : list[DrillItem]
        Lista de ejercicios.
    minimal_pairs : list[MinimalPair]
        Pares mínimos relacionados.
    """
    name: str
    description: str
    lang: str
    target_phones: List[str] = field(default_factory=list)
    items: List[DrillItem] = field(default_factory=list)
    minimal_pairs: List[MinimalPair] = field(default_factory=list)
    
    def add_item(self, item: DrillItem) -> None:
        """Añadir un ejercicio al set."""
        self.items.append(item)
    
    def add_minimal_pair(self, pair: MinimalPair) -> None:
        """Añadir un par mínimo al set."""
        self.minimal_pairs.append(pair)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "name": self.name,
            "description": self.description,
            "lang": self.lang,
            "target_phones": self.target_phones,
            "items": [item.to_dict() for item in self.items],
            "minimal_pairs": [pair.to_dict() for pair in self.minimal_pairs],
        }
    
    def __len__(self) -> int:
        """Número total de ejercicios."""
        return len(self.items) + len(self.minimal_pairs)


__all__ = [
    "DrillItem",
    "DrillSet",
    "MinimalPair",
]
