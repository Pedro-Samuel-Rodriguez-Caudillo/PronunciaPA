"""Reglas fonológicas ordenadas (SPE-style).

Una regla fonológica transforma segmentos en contextos específicos:
  A → B / X_Y
  (A se convierte en B cuando está entre X e Y)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from ipa_core.phonology.representation import tokenize_ipa


@dataclass
class PhonologicalRule:
    """Regla fonológica sensible al contexto.
    
    Atributos
    ---------
    name : str
        Nombre descriptivo de la regla.
    input_segments : List[str]
        Segmentos de entrada que la regla transforma.
    output_segments : List[str]
        Segmentos de salida correspondientes.
    left_context : str
        Regex para contexto izquierdo. Vacío = cualquiera.
        Usar "_" para marcar la posición del segmento.
    right_context : str
        Regex para contexto derecho. Vacío = cualquiera.
    order : int
        Orden de aplicación (menor = antes).
    optional : bool
        Si es True, la regla puede no aplicarse (variación libre).
    register : str
        Registro donde aplica (formal, informal, all).
    description : str
        Descripción de la regla.
    """
    name: str
    input_segments: List[str]
    output_segments: List[str]
    left_context: str = ""
    right_context: str = ""
    order: int = 0
    optional: bool = False
    register: str = "all"
    description: str = ""
    
    def __post_init__(self) -> None:
        if len(self.input_segments) != len(self.output_segments):
            raise ValueError(
                f"Input and output must have same length: "
                f"{self.input_segments} → {self.output_segments}"
            )
        
        # Crear mapeo de transformación
        self._transform_map = dict(zip(self.input_segments, self.output_segments))
        # Mapa inverso (solo para salidas no vacías y únicas)
        self._inverse_map: Dict[str, str] = {
            out: inp for inp, out in self._transform_map.items() if out
        }
        
        # Compilar patrones de contexto
        self._left_re = re.compile(f"({self.left_context})$") if self.left_context else None
        self._right_re = re.compile(f"^({self.right_context})") if self.right_context else None
    
    def matches_context(self, left: str, right: str) -> bool:
        """Verificar si el contexto coincide con la regla."""
        if self._left_re:
            if not self._left_re.search(left):
                return False
        if self._right_re:
            if not self._right_re.match(right):
                return False
        return True
    
    def can_apply(self, segment: str) -> bool:
        """Verificar si la regla puede aplicarse a un segmento."""
        return segment in self._transform_map
    
    def transform(self, segment: str) -> str:
        """Transformar un segmento según la regla."""
        return self._transform_map.get(segment, segment)
    
    def apply(self, input_str: str) -> str:
        """Aplicar la regla a una cadena completa (tokenizada).

        Tokeniza usando dígrafos; aplica transformación si coincide contexto.
        """
        if not input_str:
            return input_str

        tokens = tokenize_ipa(input_str)
        result: List[str] = []

        for idx, segment in enumerate(tokens):
            if self.can_apply(segment):
                left = "".join(tokens[:idx])
                right = "".join(tokens[idx + 1 :])

                if self.matches_context(left, right):
                    result.append(self.transform(segment))
                else:
                    result.append(segment)
            else:
                result.append(segment)

        return "".join(result)

    def apply_inverse(self, input_str: str) -> str:
        """Aplicar la regla de forma inversa (colapso alófonos→fonemas).

        Solo se aplica si la salida no está vacía y hay correspondencia 1:1.
        """
        if not input_str or not self._inverse_map:
            return input_str

        tokens = tokenize_ipa(input_str)
        result: List[str] = []

        for idx, segment in enumerate(tokens):
            if segment in self._inverse_map:
                left = "".join(tokens[:idx])
                right = "".join(tokens[idx + 1 :])

                if self.matches_context(left, right):
                    result.append(self._inverse_map[segment])
                else:
                    result.append(segment)
            else:
                result.append(segment)

        return "".join(result)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializar a diccionario."""
        d = {
            "name": self.name,
            "input": self.input_segments,
            "output": self.output_segments,
            "order": self.order,
        }
        if self.left_context:
            d["left"] = self.left_context
        if self.right_context:
            d["right"] = self.right_context
        if self.optional:
            d["optional"] = True
        if self.register != "all":
            d["register"] = self.register
        if self.description:
            d["description"] = self.description
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhonologicalRule":
        """Crear desde diccionario."""
        return cls(
            name=data.get("name", ""),
            input_segments=data.get("input", []),
            output_segments=data.get("output", []),
            left_context=data.get("left", ""),
            right_context=data.get("right", ""),
            order=data.get("order", 0),
            optional=data.get("optional", False),
            register=data.get("register", "all"),
            description=data.get("description", ""),
        )
    
    def __repr__(self) -> str:
        inputs = ",".join(self.input_segments)
        outputs = ",".join(self.output_segments)
        context = ""
        if self.left_context or self.right_context:
            context = f" / {self.left_context}_{self.right_context}"
        return f"{self.name}: {inputs} → {outputs}{context}"


# Reglas predefinidas comunes

SPIRANTIZATION_ES = PhonologicalRule(
    name="Espirantización",
    input_segments=["b", "d", "g"],
    output_segments=["β", "ð", "ɣ"],
    left_context="[aeiouəɛɪʊʌɔlɾrmɲnŋ]",  # después de vocal o sonorante
    right_context="",
    order=2,  # Después de asimilación nasal para que g siga disponible
    description="Oclusivas sonoras → fricativas tras vocal o sonorante",
)

NASAL_VELAR_ASSIMILATION_ES = PhonologicalRule(
    name="Asimilación nasal velar",
    input_segments=["n"],
    output_segments=["ŋ"],
    left_context="",
    right_context="[kgx]",
    order=1,  # Antes de espirantización
    description="n → ŋ antes de velar (tengo, cinco)",
)

SESEO_ES = PhonologicalRule(
    name="Seseo",
    input_segments=["θ"],
    output_segments=["s"],
    order=0,  # Muy temprano
    description="θ → s en dialectos seseantes",
)

YEISMO_ES = PhonologicalRule(
    name="Yeísmo",
    input_segments=["ʎ"],
    output_segments=["ʝ"],
    order=0,
    description="ʎ → ʝ en dialectos yeístas",
)

D_ELISION_ES = PhonologicalRule(
    name="Elisión de /d/ final",
    input_segments=["d"],
    output_segments=[""],  # Elisión
    left_context="[aeiou]",
    right_context="$",  # Final de palabra (aproximado)
    order=10,
    optional=True,
    register="informal",
    description="d → ∅ en posición final tras vocal",
)


__all__ = [
    "PhonologicalRule",
    "SPIRANTIZATION_ES",
    "NASAL_VELAR_ASSIMILATION_ES",
    "SESEO_ES",
    "YEISMO_ES",
    "D_ELISION_ES",
]
