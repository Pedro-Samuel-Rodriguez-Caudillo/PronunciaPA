# TODO - textref

- [ ] Implementar convertidores reales texto -> IPA apoyandose en g2p gramatical o servicios externos.
- [ ] Gestionar seleccion de idioma y normalizacion previa del texto.
- [ ] Documentar convenciones de salida (espacios, separadores, simbolos especiales).
- [ ] Incorporar cache para evitar recalcular transcripciones repetidas.
- [ ] Crear pruebas unitarias con frases cortas en distintos idiomas.

## Módulos propuestos

- ipa_core/textref/phonemizer.py
  - Adaptador a `phonemizer`/`espeak-ng` u otro g2p.
- ipa_core/textref/normalizer.py
  - Limpieza de texto, casing, signos y mapeos a IPA.
- ipa_core/textref/cache.py
  - Caché in-memory/archivo por `(text, lang, backend)`.

## Contrato TextRefProvider

```python
class TextRefProvider(Protocol):
    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]: ...

# Parámetros mínimos esperados (params)
TextRefParams = {"lang": "es", "backend": "phonemizer"}
```

## Convenciones de salida

- Tokenización por símbolo IPA; espacios representan separadores.
- Normalización consistente con `Preprocessor.normalize_tokens`.
