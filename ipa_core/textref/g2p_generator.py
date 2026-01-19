"""Generador G2P para ejercicios de pronunciación.

Usa proveedores TextRef para generar transcripciones IPA y crear
ejercicios, pares mínimos y drills para practicar pronunciación.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ipa_core.plugins.base import BasePlugin
from ipa_core.drill_types import DrillItem, DrillSet, MinimalPair

if TYPE_CHECKING:
    from ipa_core.ports.textref import TextRefProvider


# Diccionario de pares mínimos predefinidos por idioma
# Formato: target_phone -> [(word_a, word_b, contrast_phone, position), ...]
MINIMAL_PAIRS_EN: Dict[str, List[tuple]] = {
    "p": [
        ("pin", "bin", "b", "initial"),
        ("cap", "cab", "b", "final"),
        ("rapid", "rabid", "b", "medial"),
    ],
    "b": [
        ("bin", "pin", "p", "initial"),
        ("cab", "cap", "p", "final"),
    ],
    "t": [
        ("time", "dime", "d", "initial"),
        ("bat", "bad", "d", "final"),
        ("writer", "rider", "d", "medial"),
    ],
    "d": [
        ("dime", "time", "t", "initial"),
        ("bad", "bat", "t", "final"),
    ],
    "k": [
        ("cap", "gap", "g", "initial"),
        ("back", "bag", "g", "final"),
    ],
    "θ": [  # th voiceless
        ("think", "sink", "s", "initial"),
        ("bath", "bass", "s", "final"),
        ("thought", "taught", "t", "initial"),
    ],
    "ð": [  # th voiced
        ("this", "dis", "d", "initial"),
        ("breathe", "breeze", "z", "final"),
    ],
    "ʃ": [  # sh
        ("ship", "sip", "s", "initial"),
        ("mesh", "mess", "s", "final"),
        ("ship", "chip", "tʃ", "initial"),
    ],
    "tʃ": [  # ch
        ("chip", "ship", "ʃ", "initial"),
        ("catch", "cash", "ʃ", "final"),
    ],
    "r": [
        ("right", "light", "l", "initial"),
        ("wrong", "long", "l", "initial"),
    ],
    "l": [
        ("light", "right", "r", "initial"),
        ("long", "wrong", "r", "initial"),
    ],
    "i": [  # ee
        ("sheep", "ship", "ɪ", "medial"),
        ("beat", "bit", "ɪ", "medial"),
    ],
    "ɪ": [  # i
        ("ship", "sheep", "i", "medial"),
        ("bit", "beat", "i", "medial"),
    ],
    "æ": [  # a as in cat
        ("bat", "bet", "ɛ", "medial"),
        ("man", "men", "ɛ", "medial"),
    ],
    "ə": [  # schwa
        ("about", "a boat", "oʊ", "medial"),
    ],
}

MINIMAL_PAIRS_ES: Dict[str, List[tuple]] = {
    "p": [
        ("pato", "bato", "b", "initial"),
        ("copa", "coba", "b", "medial"),
    ],
    "b": [
        ("beso", "peso", "p", "initial"),
        ("lobo", "lopo", "p", "medial"),
    ],
    "t": [
        ("toca", "doca", "d", "initial"),
        ("pata", "pada", "d", "medial"),
    ],
    "d": [
        ("dedo", "tedo", "t", "initial"),
        ("codo", "coto", "t", "medial"),
    ],
    "k": [
        ("casa", "gasa", "g", "initial"),
        ("poca", "poga", "g", "medial"),
    ],
    "r": [  # vibrante múltiple
        ("perro", "pero", "ɾ", "medial"),
        ("carro", "caro", "ɾ", "medial"),
    ],
    "ɾ": [  # vibrante simple
        ("pero", "perro", "r", "medial"),
        ("caro", "carro", "r", "medial"),
    ],
    "ɲ": [  # ñ
        ("año", "ano", "n", "medial"),
        ("caña", "cana", "n", "medial"),
    ],
}


class G2PExerciseGenerator(BasePlugin):
    """Generador de ejercicios de pronunciación basado en G2P.
    
    Usa un proveedor TextRef para obtener transcripciones IPA
    y genera ejercicios, pares mínimos y drills.
    
    Parámetros
    ----------
    textref : TextRefProvider | None
        Proveedor de transcripción texto→IPA.
    default_lang : str
        Idioma por defecto para ejercicios.
    """
    
    _MINIMAL_PAIRS = {
        "en": MINIMAL_PAIRS_EN,
        "es": MINIMAL_PAIRS_ES,
    }
    
    def __init__(
        self,
        textref: Optional["TextRefProvider"] = None,
        *,
        default_lang: str = "en",
    ) -> None:
        self._textref = textref
        self._default_lang = default_lang
    
    def set_textref(self, textref: "TextRefProvider") -> None:
        """Establecer el proveedor TextRef."""
        self._textref = textref
    
    async def get_ipa(self, text: str, lang: Optional[str] = None) -> str:
        """Obtener transcripción IPA de un texto.
        
        Parámetros
        ----------
        text : str
            Texto a transcribir.
        lang : str | None
            Código de idioma.
            
        Retorna
        -------
        str
            Transcripción IPA como string.
        """
        if self._textref is None:
            # Sin TextRef, retornar placeholder
            return f"[{text}]"
        
        resolved_lang = lang or self._default_lang
        result = await self._textref.to_ipa(text, lang=resolved_lang)
        return " ".join(result["tokens"])
    
    async def generate_minimal_pairs(
        self,
        target_phone: str,
        *,
        lang: Optional[str] = None,
        max_pairs: int = 5,
    ) -> List[MinimalPair]:
        """Generar pares mínimos para un fonema objetivo.
        
        Parámetros
        ----------
        target_phone : str
            Fonema para el que generar pares.
        lang : str | None
            Código de idioma.
        max_pairs : int
            Número máximo de pares a retornar.
            
        Retorna
        -------
        list[MinimalPair]
            Lista de pares mínimos.
        """
        resolved_lang = lang or self._default_lang
        pairs_db = self._MINIMAL_PAIRS.get(resolved_lang, {})
        raw_pairs = pairs_db.get(target_phone, [])
        
        result: List[MinimalPair] = []
        for word_a, word_b, contrast, position in raw_pairs[:max_pairs]:
            ipa_a = await self.get_ipa(word_a, resolved_lang)
            ipa_b = await self.get_ipa(word_b, resolved_lang)
            
            result.append(MinimalPair(
                word_a=word_a,
                word_b=word_b,
                ipa_a=ipa_a,
                ipa_b=ipa_b,
                target_phone=target_phone,
                contrast_phone=contrast,
                position=position,
            ))
        
        return result
    
    async def generate_drills(
        self,
        target_phones: List[str],
        *,
        lang: Optional[str] = None,
        difficulty: int = 1,
    ) -> List[DrillItem]:
        """Generar ejercicios para una lista de fonemas.
        
        Parámetros
        ----------
        target_phones : list[str]
            Fonemas objetivo para practicar.
        lang : str | None
            Código de idioma.
        difficulty : int
            Nivel de dificultad (1-5).
            
        Retorna
        -------
        list[DrillItem]
            Lista de ejercicios.
        """
        resolved_lang = lang or self._default_lang
        drills: List[DrillItem] = []
        
        for phone in target_phones:
            # Obtener palabras de los pares mínimos que contienen el fonema
            pairs_db = self._MINIMAL_PAIRS.get(resolved_lang, {})
            raw_pairs = pairs_db.get(phone, [])
            
            for word_a, word_b, contrast, position in raw_pairs:
                # Crear drill para word_a
                ipa = await self.get_ipa(word_a, resolved_lang)
                hints = self._get_hints(phone, position, resolved_lang)
                
                drills.append(DrillItem(
                    text=word_a,
                    ipa=ipa,
                    target_phones=[phone],
                    difficulty=difficulty,
                    hints=hints,
                ))
        
        return drills
    
    async def generate_drill_set(
        self,
        name: str,
        target_phones: List[str],
        *,
        lang: Optional[str] = None,
        description: str = "",
    ) -> DrillSet:
        """Generar un set completo de ejercicios.
        
        Parámetros
        ----------
        name : str
            Nombre del set.
        target_phones : list[str]
            Fonemas objetivo.
        lang : str | None
            Código de idioma.
        description : str
            Descripción del set.
            
        Retorna
        -------
        DrillSet
            Set completo con items y pares mínimos.
        """
        resolved_lang = lang or self._default_lang
        
        drill_set = DrillSet(
            name=name,
            description=description or f"Práctica de {', '.join(target_phones)}",
            lang=resolved_lang,
            target_phones=target_phones,
        )
        
        # Generar drills y pares mínimos para cada fonema
        for phone in target_phones:
            pairs = await self.generate_minimal_pairs(phone, lang=resolved_lang, max_pairs=3)
            for pair in pairs:
                drill_set.add_minimal_pair(pair)
            
            drills = await self.generate_drills([phone], lang=resolved_lang)
            for drill in drills[:3]:  # Máximo 3 drills por fonema
                drill_set.add_item(drill)
        
        return drill_set
    
    def _get_hints(self, phone: str, position: str, lang: str) -> List[str]:
        """Obtener consejos de pronunciación para un fonema."""
        hints: List[str] = []
        
        # Consejos genéricos por posición
        if position == "initial":
            hints.append(f"Enfócate en pronunciar '{phone}' claramente al inicio.")
        elif position == "final":
            hints.append(f"No omitas '{phone}' al final de la palabra.")
        elif position == "medial":
            hints.append(f"Mantén '{phone}' claro en medio de la palabra.")
        
        # Consejos específicos por fonema (inglés)
        if lang == "en":
            if phone == "θ":
                hints.append("Coloca la lengua entre los dientes y sopla suavemente.")
            elif phone == "ð":
                hints.append("Como /θ/ pero con vibración de cuerdas vocales.")
            elif phone == "r":
                hints.append("No toques el paladar con la lengua; la /r/ inglesa es aproximante.")
            elif phone in ("i", "ɪ"):
                hints.append("Distingue entre 'ee' larga y 'i' corta.")
        
        # Consejos específicos por fonema (español)
        if lang == "es":
            if phone == "r":
                hints.append("Vibra la lengua múltiples veces contra el paladar.")
            elif phone == "ɾ":
                hints.append("Un solo golpe rápido de la lengua contra el paladar.")
            elif phone == "ɲ":
                hints.append("Presiona el cuerpo de la lengua contra el paladar.")
        
        return hints
    
    def get_available_phones(self, lang: Optional[str] = None) -> List[str]:
        """Obtener lista de fonemas disponibles para ejercicios.
        
        Parámetros
        ----------
        lang : str | None
            Código de idioma.
            
        Retorna
        -------
        list[str]
            Lista de fonemas con pares mínimos disponibles.
        """
        resolved_lang = lang or self._default_lang
        pairs_db = self._MINIMAL_PAIRS.get(resolved_lang, {})
        return list(pairs_db.keys())


__all__ = [
    "G2PExerciseGenerator",
    "MINIMAL_PAIRS_EN",
    "MINIMAL_PAIRS_ES",
]
