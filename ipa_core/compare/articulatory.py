"""Distancia articulatoria para comparación fonética.

Proporciona una matriz de distancia basada en rasgos articulatorios
para calcular costos de sustitución más precisos en el comparador.

La función principal ``articulatory_distance()`` usa rasgos SPE
(FeatureBundle de phonology/features.py) cuando ambos fonemas están
en la base de datos SPE, y cae de respaldo a índices de Enum cuando
alguno no está cubierto.  Esto elimina el artefacto de tratar
ordinales como escala métrica lineal.

Tabla explícita de distancias entre lugares de articulación
-----------------------------------------------------------
``PLACE_DISTANCE_TABLE`` codifica distancias fonéticamente motivadas entre
each par de lugares de articulación.  A diferencia de la distancia ordinal
(abs(a.value - b.value)), esta tabla refleja la topología del tracto vocal:
- Lugares adyacentes (bilabial↔labiodental) = ~0.1
- Lugares muy distantes (bilabial↔glotal) = 1.0
El camino BILABIAL → LABIODENTAL → DENTAL → ALVEOLAR → POSTALVEOLAR →
RETROFLEX → PALATAL → VELAR → UVULAR → PHARYNGEAL → GLOTTAL refleja
la progresión anatómica de delantera a trasera en el tracto vocal.

Distinción tense/lax en vocales
--------------------------------
``Tenseness`` y la columna correspondiente en ``VowelFeatures`` permiten
diferenciar pares tense/lax (i/ɪ, u/ʊ, e/ɛ, o/ɔ) en el respaldo ordinal,
alineando con el rasgo SPE ``tense`` que ya existe en FeatureBundle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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


# Tabla explícita de distancias entre lugares de articulación.
# Codifica la topología del tracto vocal: lugares adyacentes son más cercanos.
# Valores simétricos en [0.0, 1.0].  Basado en distancias anatómicas estándar.
#
# Para interpretar: 0.0 = mismo lugar, 1.0 = máxima distancia.
# Formato: (Place_A, Place_B) → float.  Sólo se almacena el par ordenado
# (menor.value, mayor.value) para compacidad; _place_dist() consulta ambas.
_P = Place  # alias corto
_PLACE_RAW: list[tuple[Place, Place, float]] = [
    # Bilabial ↔ *
    (_P.BILABIAL, _P.LABIODENTAL, 0.1),
    (_P.BILABIAL, _P.DENTAL,      0.3),
    (_P.BILABIAL, _P.ALVEOLAR,    0.4),
    (_P.BILABIAL, _P.POSTALVEOLAR,0.5),
    (_P.BILABIAL, _P.RETROFLEX,   0.6),
    (_P.BILABIAL, _P.PALATAL,     0.7),
    (_P.BILABIAL, _P.VELAR,       0.8),
    (_P.BILABIAL, _P.UVULAR,      0.9),
    (_P.BILABIAL, _P.PHARYNGEAL,  0.9),
    (_P.BILABIAL, _P.GLOTTAL,     1.0),
    # Labiodental ↔ *
    (_P.LABIODENTAL, _P.DENTAL,      0.2),
    (_P.LABIODENTAL, _P.ALVEOLAR,    0.3),
    (_P.LABIODENTAL, _P.POSTALVEOLAR,0.4),
    (_P.LABIODENTAL, _P.RETROFLEX,   0.5),
    (_P.LABIODENTAL, _P.PALATAL,     0.6),
    (_P.LABIODENTAL, _P.VELAR,       0.7),
    (_P.LABIODENTAL, _P.UVULAR,      0.8),
    (_P.LABIODENTAL, _P.PHARYNGEAL,  0.9),
    (_P.LABIODENTAL, _P.GLOTTAL,     1.0),
    # Dental ↔ *
    (_P.DENTAL, _P.ALVEOLAR,     0.1),
    (_P.DENTAL, _P.POSTALVEOLAR, 0.2),
    (_P.DENTAL, _P.RETROFLEX,    0.3),
    (_P.DENTAL, _P.PALATAL,      0.5),
    (_P.DENTAL, _P.VELAR,        0.6),
    (_P.DENTAL, _P.UVULAR,       0.7),
    (_P.DENTAL, _P.PHARYNGEAL,   0.8),
    (_P.DENTAL, _P.GLOTTAL,      0.9),
    # Alveolar ↔ *
    (_P.ALVEOLAR, _P.POSTALVEOLAR, 0.1),
    (_P.ALVEOLAR, _P.RETROFLEX,    0.2),
    (_P.ALVEOLAR, _P.PALATAL,      0.4),
    (_P.ALVEOLAR, _P.VELAR,        0.5),
    (_P.ALVEOLAR, _P.UVULAR,       0.6),
    (_P.ALVEOLAR, _P.PHARYNGEAL,   0.7),
    (_P.ALVEOLAR, _P.GLOTTAL,      0.8),
    # Postalveolar ↔ *
    (_P.POSTALVEOLAR, _P.RETROFLEX,  0.1),
    (_P.POSTALVEOLAR, _P.PALATAL,    0.3),
    (_P.POSTALVEOLAR, _P.VELAR,      0.4),
    (_P.POSTALVEOLAR, _P.UVULAR,     0.5),
    (_P.POSTALVEOLAR, _P.PHARYNGEAL, 0.6),
    (_P.POSTALVEOLAR, _P.GLOTTAL,    0.7),
    # Retroflex ↔ *
    (_P.RETROFLEX, _P.PALATAL,    0.2),
    (_P.RETROFLEX, _P.VELAR,      0.4),
    (_P.RETROFLEX, _P.UVULAR,     0.5),
    (_P.RETROFLEX, _P.PHARYNGEAL, 0.6),
    (_P.RETROFLEX, _P.GLOTTAL,    0.7),
    # Palatal ↔ *
    (_P.PALATAL, _P.VELAR,      0.2),
    (_P.PALATAL, _P.UVULAR,     0.4),
    (_P.PALATAL, _P.PHARYNGEAL, 0.6),
    (_P.PALATAL, _P.GLOTTAL,    0.8),
    # Velar ↔ *
    (_P.VELAR, _P.UVULAR,     0.2),
    (_P.VELAR, _P.PHARYNGEAL, 0.4),
    (_P.VELAR, _P.GLOTTAL,    0.6),
    # Uvular ↔ *
    (_P.UVULAR, _P.PHARYNGEAL, 0.2),
    (_P.UVULAR, _P.GLOTTAL,    0.5),
    # Pharyngeal ↔ *
    (_P.PHARYNGEAL, _P.GLOTTAL, 0.3),
]

# Construir tabla simétrica para consulta rápida O(1)
PLACE_DISTANCE_TABLE: Dict[Tuple[Place, Place], float] = {}
for _a, _b, _d in _PLACE_RAW:
    PLACE_DISTANCE_TABLE[(_a, _b)] = _d
    PLACE_DISTANCE_TABLE[(_b, _a)] = _d
for _p in Place:
    PLACE_DISTANCE_TABLE[(_p, _p)] = 0.0
del _P, _PLACE_RAW, _a, _b, _d, _p


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


class Tenseness(Enum):
    """Tensión vocálica (tense vs lax).
    
    Distingue pares como /i/ (tense) vs /ɪ/ (lax), /u/ vs /ʊ/, etc.
    Codifica el rasgo SPE ``tense`` para el respaldo Enum en vocal_distance.
    """
    LAX = 0
    TENSE = 1


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
    tenseness: Tenseness = field(default=Tenseness.TENSE)


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
    "ʝ": ConsonantFeatures(Place.PALATAL, Manner.FRICATIVE, Voicing.VOICED),
}

# Mapeo de vocales IPA a rasgos articulatorios
# El cuarto argumento (Tenseness) distingue pares tense/lax:
#   tense: i, y, e, ø, o, u, a, ɑ  →  Tenseness.TENSE (default)
#   lax:   ɪ, ʊ, ɛ, œ, ɔ, æ, ə   →  Tenseness.LAX
VOWEL_FEATURES: Dict[str, VowelFeatures] = {
    # Close vowels — tense
    "i": VowelFeatures(Height.CLOSE, Backness.FRONT, Roundedness.UNROUNDED, Tenseness.TENSE),
    "y": VowelFeatures(Height.CLOSE, Backness.FRONT, Roundedness.ROUNDED, Tenseness.TENSE),
    "ɨ": VowelFeatures(Height.CLOSE, Backness.CENTRAL, Roundedness.UNROUNDED, Tenseness.TENSE),
    "ʉ": VowelFeatures(Height.CLOSE, Backness.CENTRAL, Roundedness.ROUNDED, Tenseness.TENSE),
    "ɯ": VowelFeatures(Height.CLOSE, Backness.BACK, Roundedness.UNROUNDED, Tenseness.TENSE),
    "u": VowelFeatures(Height.CLOSE, Backness.BACK, Roundedness.ROUNDED, Tenseness.TENSE),
    
    # Near-close vowels — lax (ɪ/ʊ son el prototipo de pares lax)
    "ɪ": VowelFeatures(Height.NEAR_CLOSE, Backness.NEAR_FRONT, Roundedness.UNROUNDED, Tenseness.LAX),
    "ʊ": VowelFeatures(Height.NEAR_CLOSE, Backness.NEAR_BACK, Roundedness.ROUNDED, Tenseness.LAX),
    
    # Close-mid vowels — tense
    "e": VowelFeatures(Height.CLOSE_MID, Backness.FRONT, Roundedness.UNROUNDED, Tenseness.TENSE),
    "ø": VowelFeatures(Height.CLOSE_MID, Backness.FRONT, Roundedness.ROUNDED, Tenseness.TENSE),
    "o": VowelFeatures(Height.CLOSE_MID, Backness.BACK, Roundedness.ROUNDED, Tenseness.TENSE),
    
    # Mid vowels — lax (schwa es reducida/lax por excelencia)
    "ə": VowelFeatures(Height.MID, Backness.CENTRAL, Roundedness.UNROUNDED, Tenseness.LAX),
    
    # Open-mid vowels — lax
    "ɛ": VowelFeatures(Height.OPEN_MID, Backness.FRONT, Roundedness.UNROUNDED, Tenseness.LAX),
    "œ": VowelFeatures(Height.OPEN_MID, Backness.FRONT, Roundedness.ROUNDED, Tenseness.LAX),
    "ʌ": VowelFeatures(Height.OPEN_MID, Backness.BACK, Roundedness.UNROUNDED, Tenseness.LAX),
    "ɔ": VowelFeatures(Height.OPEN_MID, Backness.BACK, Roundedness.ROUNDED, Tenseness.LAX),
    
    # Near-open vowels — lax
    "æ": VowelFeatures(Height.NEAR_OPEN, Backness.FRONT, Roundedness.UNROUNDED, Tenseness.LAX),
    "ɐ": VowelFeatures(Height.NEAR_OPEN, Backness.CENTRAL, Roundedness.UNROUNDED, Tenseness.LAX),
    
    # Open vowels — tense
    "a": VowelFeatures(Height.OPEN, Backness.FRONT, Roundedness.UNROUNDED, Tenseness.TENSE),
    "ɑ": VowelFeatures(Height.OPEN, Backness.BACK, Roundedness.UNROUNDED, Tenseness.TENSE),
    "ɒ": VowelFeatures(Height.OPEN, Backness.BACK, Roundedness.ROUNDED, Tenseness.TENSE),
}


def _spe_distance(phone_a: str, phone_b: str) -> Optional[float]:
    """Calcular distancia usando FeatureBundle SPE (phonology/features.py).

    Trata los rasgos no especificados como ausentes (False).
    Retorna None si alguno de los fonemas no está en la base de datos SPE.

    Parámetros
    ----------
    phone_a, phone_b : str
        Símbolos IPA a comparar.

    Retorna
    -------
    float | None
        Distancia normalizada en [0, 1], o None si no hay cobertura SPE.
    """
    try:
        from ipa_core.phonology.features import get_features
    except ImportError:
        return None

    feat_a = get_features(phone_a)
    feat_b = get_features(phone_b)
    if feat_a is None or feat_b is None:
        return None

    # Unión de todos los rasgos explícitamente especificados en alguno de los dos
    all_features = feat_a.positive | feat_a.negative | feat_b.positive | feat_b.negative
    if not all_features:
        return 0.0

    diffs = 0
    for f in all_features:
        # No especificado = ausente (False) para medir distancia
        val_a = feat_a.has(f)
        val_b = feat_b.has(f)
        a = val_a if val_a is not None else False
        b = val_b if val_b is not None else False
        if a != b:
            diffs += 1

    dist = diffs / len(all_features)
    # Si SPE no distingue dos fonemas distintos (bundles idénticos), retornar
    # None para activar el respaldo ordinal.  Ocurre con pares como /e/-/ə/
    # cuya diferencia de altura no está codificada en el subconjunto SPE de
    # phonology/features.py (ambos son [-high, -low, -back, -round]).
    if dist == 0.0:
        return None
    return dist


def consonant_distance(phone_a: str, phone_b: str) -> float:
    """Calcular distancia articulatoria entre dos consonantes.

    Intenta primero con rasgos SPE (FeatureBundle), que son fonológicamente
    más precisos que comparar ordinales de Enum.  Si algún fonema no está
    en la base SPE, cae de respaldo al cálculo por Enum.

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
    # Intentar con rasgos SPE (más preciso)
    spe = _spe_distance(phone_a, phone_b)
    if spe is not None:
        return spe

    # Respaldo: tabla explícita de lugares + modos (cobertura más amplia)
    feat_a = CONSONANT_FEATURES.get(phone_a)
    feat_b = CONSONANT_FEATURES.get(phone_b)

    if feat_a is None or feat_b is None:
        return 1.0  # Máxima distancia si no tenemos datos

    # Usar tabla de distancias explícita entre lugares de articulación.
    # Es más precisa que abs(ordinal_a - ordinal_b) / 10 porque refleja
    # la topología real del tracto vocal (p.ej. bilabial↔labiodental = 0.1
    # pero bilabial↔glotal = 1.0, no sólo la diferencia de índice).
    place_diff = PLACE_DISTANCE_TABLE.get(
        (feat_a.place, feat_b.place),
        abs(feat_a.place.value - feat_b.place.value) / 10.0,  # fallback seguro
    )
    manner_diff = abs(feat_a.manner.value - feat_b.manner.value) / 7.0
    voicing_diff = abs(feat_a.voicing.value - feat_b.voicing.value)

    distance = (0.4 * manner_diff + 0.4 * place_diff + 0.2 * voicing_diff)
    return min(1.0, distance)


def vowel_distance(phone_a: str, phone_b: str) -> float:
    """Calcular distancia articulatoria entre dos vocales.

    Intenta primero con rasgos SPE (FeatureBundle), que son fonológicamente
    más precisos que comparar ordinales de Enum.  Si algún fonema no está
    en la base SPE, cae de respaldo al cálculo por Enum.

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
    # Intentar con rasgos SPE (más preciso)
    spe = _spe_distance(phone_a, phone_b)
    if spe is not None:
        return spe

    # Respaldo: índices de Enum (incluye tenseness)
    feat_a = VOWEL_FEATURES.get(phone_a)
    feat_b = VOWEL_FEATURES.get(phone_b)

    if feat_a is None or feat_b is None:
        return 1.0  # Máxima distancia si no tenemos datos

    height_diff = abs(feat_a.height.value - feat_b.height.value) / 6.0
    backness_diff = abs(feat_a.backness.value - feat_b.backness.value) / 4.0
    round_diff = abs(feat_a.roundedness.value - feat_b.roundedness.value)
    # Penalización por diferencia tense/lax (p.ej. i vs ɪ, u vs ʊ).
    # Peso menor que altura/anterioridad porque tense/lax es un rasgo
    # secundario en muchos sistemas vocálicos.
    tense_diff = abs(feat_a.tenseness.value - feat_b.tenseness.value) * 0.15

    distance = (0.45 * height_diff + 0.25 * backness_diff + 0.15 * round_diff + tense_diff)
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
    "Tenseness",
    "ConsonantFeatures",
    "VowelFeatures",
    "CONSONANT_FEATURES",
    "VOWEL_FEATURES",
    "PLACE_DISTANCE_TABLE",
    "consonant_distance",
    "vowel_distance",
    "is_consonant",
    "is_vowel",
    "articulatory_distance",
    "articulatory_substitution_cost",
]
