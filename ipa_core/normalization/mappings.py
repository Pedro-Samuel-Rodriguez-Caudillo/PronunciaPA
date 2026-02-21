"""Mapeos Unicode para símbolos IPA equivalentes.

Diferentes proveedores pueden usar distintos caracteres Unicode para
el mismo símbolo fonético. Este módulo proporciona mapeos canónicos.
"""
from __future__ import annotations

import unicodedata
from typing import Dict

# Mapeos de caracteres Unicode visualmente similares a sus formas canónicas IPA
UNICODE_MAPPINGS: Dict[str, str] = {
    # Consonantes
    # NOTE: U+0261 (ɡ) IS the canonical IPA voiced velar stop.
    # Do NOT map it to ASCII 'g' (U+0067) — that would undo the Allosaurus
    # fix in postprocess.py which correctly converts ASCII g → ɡ.
    # The two transforms would silently cancel each other out.
    "ɡ": "ɡ",       # U+0261 (IPA voiced velar stop) — keep canonical form
    "ɢ": "ɢ",       # U+0262 (keep uvular)
    "ʔ": "ʔ",       # U+0294 (glottal stop - keep)
    
    # Variantes de 'a'
    "ɑ": "ɑ",       # U+0251 (open back unrounded)
    "α": "ɑ",       # Greek alpha → IPA
    
    # Variantes de 'e'
    "ə": "ə",       # U+0259 (schwa - canonical)
    "ǝ": "ə",       # U+01DD → schwa
    
    # Variantes de 'i'
    "ɪ": "ɪ",       # U+026A (near-close near-front)
    "ı": "ɪ",       # U+0131 (dotless i) → ɪ
    
    # Modificadores y diacríticos
    "ˈ": "ˈ",       # U+02C8 (primary stress - canonical)
    "'": "ˈ",       # ASCII apostrophe → stress mark
    "ˌ": "ˌ",       # U+02CC (secondary stress - canonical)
    
    # Longitud vocálica
    "ː": "ː",       # U+02D0 (length mark - canonical)
    ":": "ː",       # ASCII colon → length mark
    
    # Nasalización
    "̃": "̃",        # U+0303 (combining tilde - canonical)
    "~": "̃",        # ASCII tilde → combining tilde
    
    # Africadas comunes (mantener como secuencias)
    # tʃ, dʒ, ts, dz se manejan como secuencias, no se mapean
    
    # Aproximantes
    "ɹ": "ɹ",       # U+0279 (alveolar approximant)
    "ɻ": "ɻ",       # U+027B (retroflex approximant)
    
    # Laterales
    "ɫ": "ɫ",       # U+026B (velarized l)
    "ʎ": "ʎ",       # U+028E (palatal lateral)
    
    # Nasales
    "ŋ": "ŋ",       # U+014B (velar nasal)
    "ɲ": "ɲ",       # U+0272 (palatal nasal)
    "ɴ": "ɴ",       # U+0274 (uvular nasal)
    
    # Fricativas
    "θ": "θ",       # U+03B8 (voiceless dental fricative)
    "ð": "ð",       # U+00F0 (voiced dental fricative)
    "ʃ": "ʃ",       # U+0283 (voiceless postalveolar)
    "ʒ": "ʒ",       # U+0292 (voiced postalveolar)
    "ç": "ç",       # U+00E7 (voiceless palatal)
    "χ": "χ",       # U+03C7 (voiceless uvular)
    "ʁ": "ʁ",       # U+0281 (voiced uvular)
    "ħ": "ħ",       # U+0127 (voiceless pharyngeal)
    "ʕ": "ʕ",       # U+0295 (voiced pharyngeal)
    
    # Vibrantes
    "ɾ": "ɾ",       # U+027E (alveolar tap)
    "ɽ": "ɽ",       # U+027D (retroflex flap)
    "ʀ": "ʀ",       # U+0280 (uvular trill)
    
    # Vocales
    "æ": "æ",       # U+00E6 (near-open front)
    "ɛ": "ɛ",       # U+025B (open-mid front)
    "ɔ": "ɔ",       # U+0254 (open-mid back rounded)
    "ʊ": "ʊ",       # U+028A (near-close near-back)
    "ʌ": "ʌ",       # U+028C (open-mid back unrounded)
    "ɒ": "ɒ",       # U+0252 (open back rounded)
    "œ": "œ",       # U+0153 (open-mid front rounded)
    "ø": "ø",       # U+00F8 (close-mid front rounded)
    "y": "y",       # close front rounded
    "ɨ": "ɨ",       # U+0268 (close central unrounded)
    "ʉ": "ʉ",       # U+0289 (close central rounded)
    "ɯ": "ɯ",       # U+026F (close back unrounded)
    
    # Silencio/pausa
    " ": " ",       # Espacio (separador de palabras)
    ".": ".",       # Separador silábico
    "|": "|",       # Pausa menor
    "‖": "‖",       # Pausa mayor
}

# Caracteres a eliminar durante normalización
STRIP_CHARS = frozenset([
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\ufeff",  # BOM (Byte Order Mark)
    "\ufffe",  # Noncharacter
])


def normalize_unicode(text: str) -> str:
    """Normalizar un texto IPA a su forma canónica Unicode.
    
    Parámetros
    ----------
    text : str
        Texto IPA a normalizar.
        
    Retorna
    -------
    str
        Texto normalizado en NFC con caracteres mapeados.
    """
    # 1. Normalizar a NFC para combinar diacríticos
    result = unicodedata.normalize("NFC", text)
    
    # 2. Eliminar caracteres invisibles
    result = "".join(c for c in result if c not in STRIP_CHARS)
    
    # 3. Aplicar mapeos de equivalencia
    mapped = []
    for char in result:
        mapped.append(UNICODE_MAPPINGS.get(char, char))
    
    return "".join(mapped)


def decompose_to_base_and_diacritics(char: str) -> tuple[str, list[str]]:
    """Descomponer un carácter en su base y diacríticos.
    
    Parámetros
    ----------
    char : str
        Carácter (posiblemente con diacríticos combinados).
        
    Retorna
    -------
    tuple[str, list[str]]
        Base y lista de diacríticos.
    """
    decomposed = unicodedata.normalize("NFD", char)
    if not decomposed:
        return "", []
    
    base = decomposed[0]
    diacritics = list(decomposed[1:])
    return base, diacritics


__all__ = [
    "UNICODE_MAPPINGS",
    "STRIP_CHARS",
    "normalize_unicode",
    "decompose_to_base_and_diacritics",
]
