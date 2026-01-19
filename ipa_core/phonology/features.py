"""Rasgos distintivos fonológicos (SPE - Sound Pattern of English).

Implementa la matriz de rasgos binarios propuesta por Chomsky & Halle
para representar segmentos fonológicos de manera formal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set


# Rasgos principales según SPE
MAJOR_CLASS_FEATURES = frozenset([
    "syllabic",      # ±syl: núcleo silábico
    "consonantal",   # ±cons: obstrucción en tracto vocal
    "sonorant",      # ±son: sonorante vs obstruyente
])

LARYNGEAL_FEATURES = frozenset([
    "voice",         # ±voice: sonoro
    "spread_glottis", # aspiración
    "constricted_glottis",  # glotalización
])

MANNER_FEATURES = frozenset([
    "continuant",    # ±cont: flujo continuo de aire
    "nasal",         # ±nasal
    "strident",      # ±strid: fricción intensa
    "lateral",       # ±lat
    "delayed_release",  # africadas
])

PLACE_FEATURES = frozenset([
    "labial",        # labios
    "coronal",       # lengua anterior
    "dorsal",        # lengua posterior
    "pharyngeal",    # faringe
    "laryngeal",     # glotis
])

CORONAL_SUBFEATURES = frozenset([
    "anterior",      # ±ant: alveolar vs postalveolar
    "distributed",   # ±dist: sh vs s
])

DORSAL_SUBFEATURES = frozenset([
    "high",          # altura vocálica
    "low",           # 
    "back",          # anterioridad
    "round",         # redondeo
    "tense",         # tensión vocálica
])

ALL_FEATURES = (
    MAJOR_CLASS_FEATURES
    | LARYNGEAL_FEATURES
    | MANNER_FEATURES
    | PLACE_FEATURES
    | CORONAL_SUBFEATURES
    | DORSAL_SUBFEATURES
)


@dataclass(frozen=True)
class FeatureBundle:
    """Conjunto inmutable de rasgos para un segmento.
    
    Los rasgos se representan como:
    - Presentes con valor True: {"+voice", "+nasal"}
    - Ausentes con valor False: {"-voice", "-nasal"}
    - No especificados: no aparecen en el bundle
    """
    positive: FrozenSet[str] = field(default_factory=frozenset)
    negative: FrozenSet[str] = field(default_factory=frozenset)
    
    def __post_init__(self) -> None:
        # Validar que no hay conflictos
        overlap = self.positive & self.negative
        if overlap:
            raise ValueError(f"Features cannot be both + and -: {overlap}")
    
    @classmethod
    def from_dict(cls, features: Dict[str, bool]) -> "FeatureBundle":
        """Crear desde diccionario {feature: True/False}."""
        positive = frozenset(f for f, v in features.items() if v)
        negative = frozenset(f for f, v in features.items() if not v)
        return cls(positive=positive, negative=negative)
    
    def to_dict(self) -> Dict[str, bool]:
        """Convertir a diccionario."""
        result = {f: True for f in self.positive}
        result.update({f: False for f in self.negative})
        return result
    
    def has(self, feature: str) -> Optional[bool]:
        """Obtener valor de un rasgo (True, False, o None si no especificado)."""
        if feature in self.positive:
            return True
        if feature in self.negative:
            return False
        return None
    
    def is_positive(self, feature: str) -> bool:
        """Verificar si un rasgo es positivo."""
        return feature in self.positive
    
    def is_negative(self, feature: str) -> bool:
        """Verificar si un rasgo es negativo."""
        return feature in self.negative
    
    def matches(self, other: "FeatureBundle") -> bool:
        """Verificar si este bundle es compatible con otro (subsumption)."""
        # Todos los rasgos especificados en self deben coincidir en other
        for f in self.positive:
            if f in other.negative:
                return False
        for f in self.negative:
            if f in other.positive:
                return False
        return True
    
    def distance(self, other: "FeatureBundle") -> int:
        """Contar cuántos rasgos difieren."""
        diff = 0
        all_features = self.positive | self.negative | other.positive | other.negative
        for f in all_features:
            if self.has(f) != other.has(f) and self.has(f) is not None and other.has(f) is not None:
                diff += 1
        return diff
    
    def __repr__(self) -> str:
        parts = [f"+{f}" for f in sorted(self.positive)]
        parts.extend(f"-{f}" for f in sorted(self.negative))
        return f"[{', '.join(parts)}]"


# Definiciones de rasgos para segmentos comunes
# Basado en SPE y convenciones modernas

CONSONANT_FEATURES: Dict[str, FeatureBundle] = {
    # Plosivas sordas
    "p": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": False, "nasal": False,
        "labial": True,
    }),
    "t": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": False, "nasal": False,
        "coronal": True, "anterior": True,
    }),
    "k": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": False, "nasal": False,
        "dorsal": True,
    }),
    
    # Plosivas sonoras
    "b": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": False, "nasal": False,
        "labial": True,
    }),
    "d": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": False, "nasal": False,
        "coronal": True, "anterior": True,
    }),
    "g": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": False, "nasal": False,
        "dorsal": True,
    }),
    
    # Fricativas (continuantes)
    "f": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": True, "strident": True,
        "labial": True,
    }),
    "v": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": True, "strident": True,
        "labial": True,
    }),
    "s": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": True, "strident": True,
        "coronal": True, "anterior": True,
    }),
    "z": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": True, "strident": True,
        "coronal": True, "anterior": True,
    }),
    "ʃ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": True, "strident": True,
        "coronal": True, "anterior": False, "distributed": True,
    }),
    "ʒ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": True, "strident": True,
        "coronal": True, "anterior": False, "distributed": True,
    }),
    "θ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": True, "strident": False,
        "coronal": True, "anterior": True, "distributed": True,
    }),
    "ð": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": True, "strident": False,
        "coronal": True, "anterior": True, "distributed": True,
    }),
    "x": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": False, "continuant": True,
        "dorsal": True,
    }),
    "h": FeatureBundle.from_dict({
        "consonantal": False, "sonorant": True, "syllabic": False,
        "voice": False, "continuant": True,
        "laryngeal": True,
    }),
    
    # Nasales (sonorantes)
    "m": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "nasal": True, "continuant": False,
        "labial": True,
    }),
    "n": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "nasal": True, "continuant": False,
        "coronal": True, "anterior": True,
    }),
    "ɲ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "nasal": True, "continuant": False,
        "coronal": True, "anterior": False, "high": True,
    }),
    "ŋ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "nasal": True, "continuant": False,
        "dorsal": True,
    }),
    
    # Líquidas
    "l": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "lateral": True, "continuant": True,
        "coronal": True, "anterior": True,
    }),
    "r": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "lateral": False, "continuant": False,
        "coronal": True, "anterior": True,
    }),
    "ɾ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "lateral": False, "continuant": False,
        "coronal": True, "anterior": True,
    }),
    "ɹ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": True, "syllabic": False,
        "voice": True, "lateral": False, "continuant": True,
        "coronal": True, "anterior": True,
    }),
    
    # Aproximantes/Glides
    "j": FeatureBundle.from_dict({
        "consonantal": False, "sonorant": True, "syllabic": False,
        "voice": True, "continuant": True,
        "dorsal": True, "high": True, "back": False,
    }),
    "w": FeatureBundle.from_dict({
        "consonantal": False, "sonorant": True, "syllabic": False,
        "voice": True, "continuant": True,
        "labial": True, "dorsal": True, "high": True, "back": True, "round": True,
    }),
    
    # Alófonos
    "β": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": True,
        "labial": True,
    }),
    "ɣ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": True,
        "dorsal": True,
    }),
    "ʝ": FeatureBundle.from_dict({
        "consonantal": True, "sonorant": False, "syllabic": False,
        "voice": True, "continuant": True,
        "coronal": True, "anterior": False, "high": True,
    }),
}

VOWEL_FEATURES: Dict[str, FeatureBundle] = {
    # Vocales cardinales
    "i": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": True, "low": False, "back": False, "round": False,
    }),
    "e": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": False, "back": False, "round": False,
    }),
    "a": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": True, "back": False, "round": False,
    }),
    "o": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": False, "back": True, "round": True,
    }),
    "u": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": True, "low": False, "back": True, "round": True,
    }),
    
    # Vocales adicionales (inglés)
    "ɪ": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": True, "low": False, "back": False, "round": False, "tense": False,
    }),
    "ɛ": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": False, "back": False, "round": False,
    }),
    "æ": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": True, "back": False, "round": False,
    }),
    "ʌ": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": False, "back": True, "round": False,
    }),
    "ʊ": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": True, "low": False, "back": True, "round": True, "tense": False,
    }),
    "ə": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": False, "back": False, "round": False,
    }),
    "ɑ": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": True, "back": True, "round": False,
    }),
    "ɔ": FeatureBundle.from_dict({
        "syllabic": True, "consonantal": False, "sonorant": True,
        "voice": True, "continuant": True,
        "high": False, "low": False, "back": True, "round": True,
    }),
}

# Combinar todos los segmentos
ALL_SEGMENT_FEATURES = {**CONSONANT_FEATURES, **VOWEL_FEATURES}


def get_features(symbol: str) -> Optional[FeatureBundle]:
    """Obtener rasgos para un símbolo IPA."""
    return ALL_SEGMENT_FEATURES.get(symbol)


def feature_distance(symbol_a: str, symbol_b: str) -> int:
    """Calcular distancia de rasgos entre dos símbolos."""
    feat_a = get_features(symbol_a)
    feat_b = get_features(symbol_b)
    
    if feat_a is None or feat_b is None:
        return 999  # Máxima distancia para desconocidos
    
    return feat_a.distance(feat_b)


def natural_class(features: FeatureBundle) -> List[str]:
    """Encontrar todos los segmentos que coinciden con un bundle de rasgos."""
    matches = []
    for symbol, feats in ALL_SEGMENT_FEATURES.items():
        if features.matches(feats):
            matches.append(symbol)
    return matches


__all__ = [
    "FeatureBundle",
    "CONSONANT_FEATURES",
    "VOWEL_FEATURES",
    "ALL_SEGMENT_FEATURES",
    "ALL_FEATURES",
    "get_features",
    "feature_distance",
    "natural_class",
]
