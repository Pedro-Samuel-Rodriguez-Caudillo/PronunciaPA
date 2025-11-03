# TODO - compare

- [ ] Implementar un comparador basado en distancia de edicion que calcule PER real.
- [ ] Entrenar/integrar un BiLSTM bidireccional para obtener alineaciones suaves previo al calculo de PER.
- [ ] Exponer configuracion para ponderar sustituciones, inserciones y borrados.
- [ ] Proveer formato de salida opcional (texto tabular, JSON) para las operaciones.
- [ ] Agregar pruebas unitarias con casos simples y ejemplos reales.
- [ ] Documentar convenciones de tokenizacion IPA usadas por los comparadores.

## Módulos propuestos

- ipa_core/compare/levenshtein.py
  - Distancia de edición y PER con pesos (sub/ins/del).
- ipa_core/compare/alignment.py
  - Recuperación de alineación (backtrace) y operaciones (`EditOp`).
- ipa_core/compare/metrics.py
  - Cálculo de PER, CER opcional, agregaciones.

## Contrato Comparator

```python
class Comparator(Protocol):
    def compare(self, ref: TokenSeq, hyp: TokenSeq, *, weights: Optional[CompareWeights] = None, **kw) -> CompareResult: ...

# Pesos por defecto
DEFAULT_WEIGHTS = {"sub": 1.0, "ins": 1.0, "del": 1.0}
```

## Formatos de salida

- `CompareResult.per`: float en [0,1].
- `CompareResult.ops`: lista de operaciones con `op ∈ {eq,sub,ins,del}`.
- `CompareResult.alignment`: tuplas `(ref_token|None, hyp_token|None)` por paso.
