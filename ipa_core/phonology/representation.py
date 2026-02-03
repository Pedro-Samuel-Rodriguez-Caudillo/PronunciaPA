"""Representaciones fonológicas con nivel (fonémico/fonético).

Este módulo provee tipos para distinguir entre representaciones
subyacentes (fonémicas) y superficiales (fonéticas).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, TYPE_CHECKING


def tokenize_ipa(ipa: str) -> List[str]:
    """Tokenizar cadena IPA en segmentos (dígrafos + suprasegmentales removidos).

    Elimina acentos primario/secundario y separadores silábicos para trabajar
    sobre la secuencia de segmentos pura. Soporta dígrafos comunes.
    """
    clean = ipa.replace("ˈ", "").replace("ˌ", "").replace(".", "")
    # Lista de multigrafos comunes en inventarios ES/EN
    multigraphs = (
        "tʃ",
        "dʒ",
        "ts",
        "dz",
        # diptongos frecuentes (se tratan como unidad)
        "aɪ",
        "aʊ",
        "ɔɪ",
        "oʊ",
        "eɪ",
        "ai",
        "ei",
        "oi",
        "au",
        "eu",
        "iu",
    )
    segments: List[str] = []
    i = 0
    while i < len(clean):
        # Intentar coincidir multigráfos en orden de longitud (aquí todos 2)
        matched = False
        if i + 1 < len(clean):
            pair = clean[i:i+2]
            if pair in multigraphs:
                segments.append(pair)
                i += 2
                matched = True
        if not matched:
            segments.append(clean[i])
            i += 1
    return segments

if TYPE_CHECKING:
    from ipa_core.phonology.segment import Segment


# Tipo para nivel de representación
RepresentationLevel = Literal["phonemic", "phonetic"]


@dataclass
class PhonologicalRepresentation:
    """Representación fonológica con nivel explícito.
    
    Atributos
    ---------
    ipa : str
        Cadena IPA (sin delimitadores).
    level : RepresentationLevel
        Nivel: "phonemic" (subyacente) o "phonetic" (superficial).
    segments : List[str]
        Lista de segmentos individuales.
    """
    ipa: str
    level: RepresentationLevel
    segments: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        # Limpiar delimitadores si existen
        self.ipa = self.ipa.strip("/[]")
        
        # Tokenizar si no hay segmentos
        if not self.segments and self.ipa:
            self.segments = tokenize_ipa(self.ipa)
    
    def to_ipa(self, with_delimiters: bool = True) -> str:
        """Convertir a string IPA con delimitadores apropiados.
        
        Parámetros
        ----------
        with_delimiters : bool
            Si True, añade /.../ o [...] según nivel.
        """
        if not with_delimiters:
            return self.ipa
        
        if self.level == "phonemic":
            return f"/{self.ipa}/"
        return f"[{self.ipa}]"
    
    @classmethod
    def phonemic(cls, ipa: str) -> "PhonologicalRepresentation":
        """Crear representación fonémica."""
        return cls(ipa=ipa, level="phonemic")
    
    @classmethod
    def phonetic(cls, ipa: str) -> "PhonologicalRepresentation":
        """Crear representación fonética."""
        return cls(ipa=ipa, level="phonetic")
    
    def __len__(self) -> int:
        return len(self.segments)
    
    def __iter__(self):
        return iter(self.segments)
    
    def __repr__(self) -> str:
        return self.to_ipa()


@dataclass
class TranscriptionResult:
    """Resultado de transcripción con ambos niveles.
    
    Atributos
    ---------
    text : str
        Texto original.
    phonemic : PhonologicalRepresentation
        Representación fonémica (subyacente).
    phonetic : Optional[PhonologicalRepresentation]
        Representación fonética (superficial), si se derivó.
    source : str
        Fuente: "espeak", "epitran", "allosaurus", "g2p_rules".
    """
    text: str
    phonemic: PhonologicalRepresentation
    phonetic: Optional[PhonologicalRepresentation] = None
    source: str = ""
    
    def get_at_level(self, level: RepresentationLevel) -> PhonologicalRepresentation:
        """Obtener representación al nivel solicitado."""
        if level == "phonemic":
            return self.phonemic
        if self.phonetic is not None:
            return self.phonetic
        raise ValueError("Phonetic representation not available")


@dataclass
class ComparisonResult:
    """Resultado de comparación con metadatos.
    
    Atributos
    ---------
    target : PhonologicalRepresentation
        Representación objetivo (referencia).
    observed : PhonologicalRepresentation
        Representación observada (del usuario).
    mode : str
        Modo de evaluación: casual, objective, phonetic.
    evaluation_level : RepresentationLevel
        Nivel usado para comparación.
    distance : float
        Distancia calculada (0 = perfecto).
    score : float
        Puntuación (0-100, 100 = perfecto).
    operations : List[dict]
        Lista de operaciones de edición (S/I/D).
    """
    target: PhonologicalRepresentation
    observed: PhonologicalRepresentation
    mode: str
    evaluation_level: RepresentationLevel
    distance: float = 0.0
    score: float = 100.0
    operations: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to CompareResult-compatible dict for API responses.
        
        Maps ComparisonResult fields to CompareResult format:
        - operations -> ops
        - distance included in meta
        - PhonologicalRepresentation serialized to IPA strings
        """
        return {
            "per": self.distance / max(len(self.target.segments), 1),
            "ops": self.operations,
            "alignment": [
                (self.target.segments[i] if i < len(self.target.segments) else None,
                 self.observed.segments[i] if i < len(self.observed.segments) else None)
                for i in range(max(len(self.target.segments), len(self.observed.segments)))
            ],
            "meta": {
                "distance": self.distance,
                "mode": self.mode,
                "evaluation_level": self.evaluation_level,
                "target_ipa": self.target.to_ipa(with_delimiters=False),
                "observed_ipa": self.observed.to_ipa(with_delimiters=False),
            },
        }


__all__ = [
    "RepresentationLevel",
    "PhonologicalRepresentation",
    "TranscriptionResult",
    "ComparisonResult",
    "tokenize_ipa",
]
