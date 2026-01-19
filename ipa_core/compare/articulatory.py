"""Distancia articulatoria para comparación fonética.

Proporciona una matriz de distancia basada en rasgos articulatorios
para calcular costos de sustitución más precisos en el comparador.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Set, Tuple


class Place(Enum):
    """Lugar de articulación para consonantes."""
    BILABIAL = 0
    LABIODENTAL = 1
    DENTAL = 2
    ALVEOLAR = 3
    POSTALVEOLAR = 4
    RETROFLEX = 5
    PALATAL = 6
    VELAR = 7
    UVULAR = 8
    PHARYNGEAL = 9
    GLOTTAL = 10


class Manner(Enum):
    """Modo de articulación para consonantes."""
    PLOSIVE = 0
    NASAL = 1
    TRILL = 2
    TAP = 3
    FRICATIVE = 4
    AFFRICATE = 5
    APPROXIMANT = 6
    LATERAL = 7


class Voicing(Enum):
    """Sonoridad."""
    VOICELESS = 0
    VOICED = 1


class Height(Enum):
    """Altura vocálica."""
    CLOSE = 0
    NEAR_CLOSE = 1
    CLOSE_MID = 2
    MID = 3
    OPEN_MID = 4
    NEAR_OPEN = 5
    OPEN = 6


class Backness(Enum):
    """Anterioridad/posterioridad vocálica."""
    FRONT = 0
    NEAR_FRONT = 1
    CENTRAL = 2
    NEAR_BACK = 3
    BACK = 4


class Roundedness(Enum):
    """Redondeo vocálico."""
    UNROUNDED = 0
    ROUNDED = 1


@dataclass
class ConsonantFeatures:
    """Rasgos articulatorios de una consonante."""
    place: Place
    manner: Manner
    voicing: Voicing


@dataclass
class VowelFeatures:
    """Rasgos articulatorios de una vocal."""
    height: Height
    backness: Backness
    roundedness: Roundedness


# Mapeo de consonantes IPA a rasgos articulatorios
CONSONANT_FEATURES: Dict[str, ConsonantFeatures] = {
    # Plosives
    "p": ConsonantFeatures(Place.BILABIAL, Manner.PLOSIVE, Voicing.VOICELESS),
    "b": ConsonantFeatures(Place.BILABIAL, Manner.PLOSIVE, Voicing.VOICED),
    "t": ConsonantFeatures(Place.ALVEOLAR, Manner.PLOSIVE, Voicing.VOICELESS),
    "d": ConsonantFeatures(Place.ALVEOLAR, Manner.PLOSIVE, Voicing.VOICED),
    "k": ConsonantFeatures(Place.VELAR, Manner.PLOSIVE, Voicing.VOICELESS),
    "g": ConsonantFeatures(Place.VELAR, Manner.PLOSIVE, Voicing.VOICED),
    "ʔ": ConsonantFeatures(Place.GLOTTAL, Manner.PLOSIVE, Voicing.VOICELESS),
    
    # Nasals
    "m": ConsonantFeatures(Place.BILABIAL, Manner.NASAL, Voicing.VOICED),
    "n": ConsonantFeatures(Place.ALVEOLAR, Manner.NASAL, Voicing.VOICED),
    "ɲ": ConsonantFeatures(Place.PALATAL, Manner.NASAL, Voicing.VOICED),
    "ŋ": ConsonantFeatures(Place.VELAR, Manner.NASAL, Voicing.VOICED),
    "ɴ": ConsonantFeatures(Place.UVULAR, Manner.NASAL, Voicing.VOICED),
    
    # Trills
    "r": ConsonantFeatures(Place.ALVEOLAR, Manner.TRILL, Voicing.VOICED),
    "ʀ": ConsonantFeatures(Place.UVULAR, Manner.TRILL, Voicing.VOICED),
    
    # Taps/Flaps
    "ɾ": ConsonantFeatures(Place.ALVEOLAR, Manner.TAP, Voicing.VOICED),
    "ɽ": ConsonantFeatures(Place.RETROFLEX, Manner.TAP, Voicing.VOICED),
    
    # Fricatives
    "f": ConsonantFeatures(Place.LABIODENTAL, Manner.FRICATIVE, Voicing.VOICELESS),
    "v": ConsonantFeatures(Place.LABIODENTAL, Manner.FRICATIVE, Voicing.VOICED),
    "θ": ConsonantFeatures(Place.DENTAL, Manner.FRICATIVE, Voicing.VOICELESS),
    "ð": ConsonantFeatures(Place.DENTAL, Manner.FRICATIVE, Voicing.VOICED),
    "s": ConsonantFeatures(Place.ALVEOLAR, Manner.FRICATIVE, Voicing.VOICELESS),
    "z": ConsonantFeatures(Place.ALVEOLAR, Manner.FRICATIVE, Voicing.VOICED),
    "ʃ": ConsonantFeatures(Place.POSTALVEOLAR, Manner.FRICATIVE, Voicing.VOICELESS),
    "ʒ": ConsonantFeatures(Place.POSTALVEOLAR, Manner.FRICATIVE, Voicing.VOICED),
    "ç": ConsonantFeatures(Place.PALATAL, Manner.FRICATIVE, Voicing.VOICELESS),
    "x": ConsonantFeatures(Place.VELAR, Manner.FRICATIVE, Voicing.VOICELESS),
    "ɣ": ConsonantFeatures(Place.VELAR, Manner.FRICATIVE, Voicing.VOICED),
    "χ": ConsonantFeatures(Place.UVULAR, Manner.FRICATIVE, Voicing.VOICELESS),
    "ʁ": ConsonantFeatures(Place.UVULAR, Manner.FRICATIVE, Voicing.VOICED),
    "h": ConsonantFeatures(Place.GLOTTAL, Manner.FRICATIVE, Voicing.VOICELESS),
    "ħ": ConsonantFeatures(Place.PHARYNGEAL, Manner.FRICATIVE, Voicing.VOICELESS),
    "ʕ": ConsonantFeatures(Place.PHARYNGEAL, Manner.FRICATIVE, Voicing.VOICED),
    
    # Affricates
    "tʃ": ConsonantFeatures(Place.POSTALVEOLAR, Manner.AFFRICATE, Voicing.VOICELESS),
    "dʒ": ConsonantFeatures(Place.POSTALVEOLAR, Manner.AFFRICATE, Voicing.VOICED),
    "ts": ConsonantFeatures(Place.ALVEOLAR, Manner.AFFRICATE, Voicing.VOICELESS),
    "dz": ConsonantFeatures(Place.ALVEOLAR, Manner.AFFRICATE, Voicing.VOICED),
    
    # Approximants
    "j": ConsonantFeatures(Place.PALATAL, Manner.APPROXIMANT, Voicing.VOICED),
    "w": ConsonantFeatures(Place.VELAR, Manner.APPROXIMANT, Voicing.VOICED),
    "ɹ": ConsonantFeatures(Place.ALVEOLAR, Manner.APPROXIMANT, Voicing.VOICED),
    "ɻ": ConsonantFeatures(Place.RETROFLEX, Manner.APPROXIMANT, Voicing.VOICED),
    
    # Laterals
    "l": ConsonantFeatures(Place.ALVEOLAR, Manner.LATERAL, Voicing.VOICED),
    "ɫ": ConsonantFeatures(Place.VELAR, Manner.LATERAL, Voicing.VOICED),
    "ʎ": ConsonantFeatures(Place.PALATAL, Manner.LATERAL, Voicing.VOICED),
    "ʟ": ConsonantFeatures(Place.VELAR, Manner.LATERAL, Voicing.VOICED),
    
    # Allophones comunes
    "β": ConsonantFeatures(Place.BILABIAL, Manner.FRICATIVE, Voicing.VOICED),
}

# Mapeo de vocales IPA a rasgos articulatorios
VOWEL_FEATURES: Dict[str, VowelFeatures] = {
    # Close vowels
    "i": VowelFeatures(Height.CLOSE, Backness.FRONT, Roundedness.UNROUNDED),
    "y": VowelFeatures(Height.CLOSE, Backness.FRONT, Roundedness.ROUNDED),
    "ɨ": VowelFeatures(Height.CLOSE, Backness.CENTRAL, Roundedness.UNROUNDED),
    "ʉ": VowelFeatures(Height.CLOSE, Backness.CENTRAL, Roundedness.ROUNDED),
    "ɯ": VowelFeatures(Height.CLOSE, Backness.BACK, Roundedness.UNROUNDED),
    "u": VowelFeatures(Height.CLOSE, Backness.BACK, Roundedness.ROUNDED),
    
    # Near-close vowels
    "ɪ": VowelFeatures(Height.NEAR_CLOSE, Backness.NEAR_FRONT, Roundedness.UNROUNDED),
    "ʊ": VowelFeatures(Height.NEAR_CLOSE, Backness.NEAR_BACK, Roundedness.ROUNDED),
    
    # Close-mid vowels
    "e": VowelFeatures(Height.CLOSE_MID, Backness.FRONT, Roundedness.UNROUNDED),
    "ø": VowelFeatures(Height.CLOSE_MID, Backness.FRONT, Roundedness.ROUNDED),
    "o": VowelFeatures(Height.CLOSE_MID, Backness.BACK, Roundedness.ROUNDED),
    
    # Mid vowels
    "ə": VowelFeatures(Height.MID, Backness.CENTRAL, Roundedness.UNROUNDED),
    
    # Open-mid vowels
    "ɛ": VowelFeatures(Height.OPEN_MID, Backness.FRONT, Roundedness.UNROUNDED),
    "œ": VowelFeatures(Height.OPEN_MID, Backness.FRONT, Roundedness.ROUNDED),
    "ʌ": VowelFeatures(Height.OPEN_MID, Backness.BACK, Roundedness.UNROUNDED),
    "ɔ": VowelFeatures(Height.OPEN_MID, Backness.BACK, Roundedness.ROUNDED),
    
    # Near-open vowels
    "æ": VowelFeatures(Height.NEAR_OPEN, Backness.FRONT, Roundedness.UNROUNDED),
    "ɐ": VowelFeatures(Height.NEAR_OPEN, Backness.CENTRAL, Roundedness.UNROUNDED),
    
    # Open vowels
    "a": VowelFeatures(Height.OPEN, Backness.FRONT, Roundedness.UNROUNDED),
    "ɑ": VowelFeatures(Height.OPEN, Backness.BACK, Roundedness.UNROUNDED),
    "ɒ": VowelFeatures(Height.OPEN, Backness.BACK, Roundedness.ROUNDED),
}


def consonant_distance(phone_a: str, phone_b: str) -> float:
    """Calcular distancia articulatoria entre dos consonantes.
    
    La distancia se basa en:
    - Diferencia de lugar (0-10 posiciones)
    - Diferencia de modo (0-7 posiciones)
    - Diferencia de sonoridad (0-1)
    
    Parámetros
    ----------
    phone_a : str
        Primera consonante.
    phone_b : str
        Segunda consonante.
        
    Retorna
    -------
    float
        Distancia normalizada en [0, 1].
    """
    feat_a = CONSONANT_FEATURES.get(phone_a)
    feat_b = CONSONANT_FEATURES.get(phone_b)
    
    if feat_a is None or feat_b is None:
        return 1.0  # Máxima distancia si no tenemos datos
    
    # Calcular diferencias
    place_diff = abs(feat_a.place.value - feat_b.place.value) / 10.0
    manner_diff = abs(feat_a.manner.value - feat_b.manner.value) / 7.0
    voicing_diff = abs(feat_a.voicing.value - feat_b.voicing.value)
    
    # Ponderar: modo > lugar > sonoridad
    distance = (0.4 * manner_diff + 0.4 * place_diff + 0.2 * voicing_diff)
    return min(1.0, distance)


def vowel_distance(phone_a: str, phone_b: str) -> float:
    """Calcular distancia articulatoria entre dos vocales.
    
    La distancia se basa en:
    - Diferencia de altura (0-6 posiciones)
    - Diferencia de anterioridad (0-4 posiciones)
    - Diferencia de redondeo (0-1)
    
    Parámetros
    ----------
    phone_a : str
        Primera vocal.
    phone_b : str
        Segunda vocal.
        
    Retorna
    -------
    float
        Distancia normalizada en [0, 1].
    """
    feat_a = VOWEL_FEATURES.get(phone_a)
    feat_b = VOWEL_FEATURES.get(phone_b)
    
    if feat_a is None or feat_b is None:
        return 1.0  # Máxima distancia si no tenemos datos
    
    # Calcular diferencias
    height_diff = abs(feat_a.height.value - feat_b.height.value) / 6.0
    backness_diff = abs(feat_a.backness.value - feat_b.backness.value) / 4.0
    round_diff = abs(feat_a.roundedness.value - feat_b.roundedness.value)
    
    # Ponderar: altura > anterioridad > redondeo
    distance = (0.5 * height_diff + 0.3 * backness_diff + 0.2 * round_diff)
    return min(1.0, distance)


def is_consonant(phone: str) -> bool:
    """Verificar si un fonema es consonante."""
    return phone in CONSONANT_FEATURES


def is_vowel(phone: str) -> bool:
    """Verificar si un fonema es vocal."""
    return phone in VOWEL_FEATURES


def articulatory_distance(phone_a: str, phone_b: str) -> float:
    """Calcular distancia articulatoria entre dos fonemas.
    
    Maneja consonantes, vocales, y fonemas desconocidos.
    La distancia está normalizada en [0, 1].
    
    Parámetros
    ----------
    phone_a : str
        Primer fonema.
    phone_b : str
        Segundo fonema.
        
    Retorna
    -------
    float
        Distancia normalizada. 0 = idénticos, 1 = máxima diferencia.
    """
    if phone_a == phone_b:
        return 0.0
    
    a_is_c = is_consonant(phone_a)
    b_is_c = is_consonant(phone_b)
    a_is_v = is_vowel(phone_a)
    b_is_v = is_vowel(phone_b)
    
    # Ambas consonantes
    if a_is_c and b_is_c:
        return consonant_distance(phone_a, phone_b)
    
    # Ambas vocales
    if a_is_v and b_is_v:
        return vowel_distance(phone_a, phone_b)
    
    # Consonante vs vocal = máxima distancia
    if (a_is_c and b_is_v) or (a_is_v and b_is_c):
        return 1.0
    
    # Fonemas desconocidos
    return 1.0


def articulatory_substitution_cost(
    phone_a: str,
    phone_b: str,
    *,
    base_cost: float = 1.0,
    min_cost: float = 0.3,
) -> float:
    """Calcular costo de sustitución basado en distancia articulatoria.
    
    El costo se escala entre min_cost y base_cost según la distancia.
    Fonemas similares tienen menor costo de sustitución.
    
    Parámetros
    ----------
    phone_a : str
        Fonema de referencia.
    phone_b : str
        Fonema hipótesis.
    base_cost : float
        Costo máximo (para fonemas muy diferentes).
    min_cost : float
        Costo mínimo (para fonemas muy similares).
        
    Retorna
    -------
    float
        Costo de sustitución en [min_cost, base_cost].
    """
    distance = articulatory_distance(phone_a, phone_b)
    # Escalar linealmente entre min_cost y base_cost
    return min_cost + (base_cost - min_cost) * distance


__all__ = [
    "Place",
    "Manner",
    "Voicing",
    "Height",
    "Backness",
    "Roundedness",
    "ConsonantFeatures",
    "VowelFeatures",
    "CONSONANT_FEATURES",
    "VOWEL_FEATURES",
    "consonant_distance",
    "vowel_distance",
    "is_consonant",
    "is_vowel",
    "articulatory_distance",
    "articulatory_substitution_cost",
]
