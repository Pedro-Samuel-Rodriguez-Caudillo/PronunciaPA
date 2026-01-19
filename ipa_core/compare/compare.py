"""Comparación con soporte para ScoringProfile.

Integra el comparador Levenshtein con perfiles de scoring por modo.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ipa_core.compare.levenshtein import LevenshteinComparator
from ipa_core.phonology.representation import (
    PhonologicalRepresentation,
    ComparisonResult,
    RepresentationLevel,
)

if TYPE_CHECKING:
    from ipa_core.plugins.language_pack import ScoringProfile


async def compare_representations(
    target: PhonologicalRepresentation,
    observed: PhonologicalRepresentation,
    *,
    mode: str = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
    profile: Optional["ScoringProfile"] = None,
    use_articulatory: bool = True,
) -> ComparisonResult:
    """Comparar dos representaciones fonológicas.
    
    Parámetros
    ----------
    target : PhonologicalRepresentation
        Representación objetivo (referencia).
    observed : PhonologicalRepresentation
        Representación observada (del usuario).
    mode : str
        Modo de evaluación: casual, objective, phonetic.
    evaluation_level : RepresentationLevel
        Nivel usado para comparación.
    profile : ScoringProfile
        Perfil de scoring opcional.
    use_articulatory : bool
        Si usar pesos articulatorios.
        
    Retorna
    -------
    ComparisonResult
        Resultado con distancia, score, y operaciones.
    """
    # Verificar que están al mismo nivel
    if target.level != observed.level:
        raise ValueError(
            f"Cannot compare different levels: {target.level} vs {observed.level}"
        )
    
    # Determinar costo mínimo según modo
    if mode == "casual":
        min_cost = 0.1  # Muy permisivo
    elif mode == "phonetic":
        min_cost = 0.5  # Estricto
    else:
        min_cost = 0.3  # Balance
    
    # Crear comparador
    comparator = LevenshteinComparator(
        use_articulatory=use_articulatory,
        articulatory_min_cost=min_cost,
    )
    
    # Comparar segmentos
    result = await comparator.compare(target.segments, observed.segments)
    
    # Calcular score ajustado por perfil
    per = result.get("per", 0.0)
    base_score = max(0.0, (1.0 - per) * 100.0)
    
    # Aplicar pesos del perfil si existe
    if profile is not None:
        # Contar errores de alófono vs fonema
        allophone_errors = 0
        phoneme_errors = 0
        
        for op in result.get("ops", []):
            if op["op"] in ("sub", "del", "ins"):
                # Simplificación: considerar subs como potenciales alófonos
                ref = op.get("ref", "")
                hyp = op.get("hyp", "")
                
                # Verificar si es par aceptable
                if (ref, hyp) in profile.acceptable_variants:
                    allophone_errors += 1
                else:
                    phoneme_errors += 1
        
        # Recalcular score con pesos
        total_segments = len(target.segments)
        if total_segments > 0:
            weighted_errors = (
                phoneme_errors * profile.phoneme_error_weight +
                allophone_errors * profile.allophone_error_weight
            )
            error_rate = weighted_errors / total_segments
            base_score = max(0.0, (1.0 - error_rate) * 100.0)
    
    return ComparisonResult(
        target=target,
        observed=observed,
        mode=mode,
        evaluation_level=evaluation_level,
        distance=result.get("meta", {}).get("distance", 0.0),
        score=base_score,
        operations=result.get("ops", []),
    )


__all__ = ["compare_representations"]
