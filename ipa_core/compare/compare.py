"""Comparación con soporte para ScoringProfile.

Integra el comparador Levenshtein con perfiles de scoring por modo.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ipa_core.compare.levenshtein import LevenshteinComparator
from ipa_core.compare.articulatory import articulatory_distance
from ipa_core.phonology.representation import (
    PhonologicalRepresentation,
    ComparisonResult,
    RepresentationLevel,
)

if TYPE_CHECKING:
    from ipa_core.plugins.language_pack import ScoringProfile
    from ipa_core.packs.schema import ErrorWeights


async def compare_representations(
    target: PhonologicalRepresentation,
    observed: PhonologicalRepresentation,
    *,
    mode: str = "objective",
    evaluation_level: RepresentationLevel = "phonemic",
    profile: Optional["ScoringProfile"] = None,
    use_articulatory: bool = True,
    error_weights: Optional["ErrorWeights"] = None,
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
    error_weights : ErrorWeights, optional
        Pesos de error del LanguagePack (semantic/frequency/articulatory).
        Si se proporciona, el escalar ``articulatory`` ajusta la distancia
        articulatoria y los pesos ``semantic``/``frequency`` pueden usarse
        en cálculos downstream.

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
    
    # Determinar costo mínimo según modo/perfil
    if profile is not None:
        tol = profile.tolerance
        if tol == "high":
            min_cost = 0.1
        elif tol == "low":
            min_cost = 0.5
        else:
            min_cost = 0.3
    else:
        if mode == "casual":
            min_cost = 0.1  # Muy permisivo
        elif mode == "phonetic":
            min_cost = 0.5  # Estricto
        else:
            min_cost = 0.3  # Balance
    
    # Aplicar escalar articulatorio del pack (si está disponible)
    art_scalar: float = 1.0
    if error_weights is not None:
        art_scalar = error_weights.articulatory

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
        weighted_errors = 0.0
        total_segments = max(len(target.segments), 1)

        for op in result.get("ops", []):
            if op["op"] == "eq":
                continue

            ref = op.get("ref") or ""
            hyp = op.get("hyp") or ""

            if op["op"] == "sub":
                if (ref, hyp) in profile.acceptable_variants or (hyp, ref) in profile.acceptable_variants:
                    weighted_errors += profile.allophone_error_weight
                else:
                    if use_articulatory and ref and hyp:
                        # Scale by articulatory distance so phonetically similar
                        # substitutions contribute less than completely different ones.
                        # Apply error_weights.articulatory scalar if provided.
                        art_dist = articulatory_distance(ref, hyp)
                        weighted_errors += art_dist * art_scalar * profile.phoneme_error_weight
                    else:
                        weighted_errors += profile.phoneme_error_weight
            else:  # ins/del
                weighted_errors += profile.phoneme_error_weight

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
