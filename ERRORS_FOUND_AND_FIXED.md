# Errores Encontrados y Corregidos

## Resumen
Durante la revisión del proceso de depuración para resolver el problema de "probando" → "prodento", se encontraron y corrigieron **3 errores críticos** en los cambios que se estaban implementando.

---

## 1. **Error de Sintaxis YAML en `inventory.yaml`**

### Ubicación
`plugins/language_packs/es-mx/inventory.yaml` (líneas 98-109)

### Problema
Los aliases de vocales nasales y otras variantes estaban usando sintaxis YAML inconsistente:
```yaml
# ❌ INCORRECTO - Comillas inconsistentes
"ã": a
"ẽ": e
"v": b
```

### Corrección
Se normalizó la sintaxis YAML para ser consistente con el resto del archivo:
```yaml
# ✓ CORRECTO - Sintaxis uniforme sin comillas innecesarias
ã: a      # Vocal nasal a
ẽ: e      # Vocal nasal e
ĩ: i      # Vocal nasal i
õ: o      # Vocal nasal o
ũ: u      # Vocal nasal u

# Otras variantes comunes (confusiones de Allosaurus)
v: β      # v → bilabial fricativa
z: s      # s sonora → s sorda
oʊ: o     # Diptongo inglés → o
eɪ: e     # Diptongo inglés → e
```

---

## 2. **Error de Tipo en `runner.py` - Parámetro Incorrecto**

### Ubicación
`ipa_core/pipeline/runner.py` línea 96 (en `execute_pipeline`)

### Problema
Se intentaba pasar `allophone_rules` como una lista de objetos `PhonologicalRule` a `IPANormalizer`, que espera un diccionario:
```python
# ❌ INCORRECTO
norm_params["allophone_rules"] = pack.get_grammar().rules  # esto es una lista de objetos!
```

Esto causaría un `TypeError` en tiempo de ejecución porque `IPANormalizer.load_allophone_rules()` espera:
```python
def load_allophone_rules(self, rules: dict[str, str]) -> None:
    """Cargar reglas de alófonos como mapeo (from_symbol → to_symbol)."""
```

### Corrección
Se removió la línea problemática. El inventario ya maneja los aliases a través del método `get_canonical()` que usa alófonos cargados del YAML:
```python
# ✓ CORRECTO
if pack is not None and hasattr(pack, 'get_inventory'):
    norm_params["inventory"] = pack.get_inventory()
```

---

## 3. **Error de Parámetro No Aceptado en `runner.py`**

### Ubicación
`ipa_core/pipeline/runner.py` líneas 92-96 y 243

### Problema
Se estaba pasando el parámetro `lang` a `normalize_tokens()`, que no lo acepta:
```python
# ❌ INCORRECTO
norm_params = {"lang": lang}
norm_asr = await pre.normalize_tokens(cleaned_asr, **norm_params)

# Y en _resolve_hyp_tokens:
res = await pre.normalize_tokens(tokens, lang=lang, inventory=inventory)
```

Esto causaba:
```
TypeError: normalize_tokens() got an unexpected keyword argument 'lang'
```

### Corrección
Se removió el parámetro `lang` inútil. `normalize_tokens()` solo acepta `inventory` y `allophone_rules` como kwargs relevantes:
```python
# ✓ CORRECTO - En execute_pipeline
norm_params = {}
if pack is not None and hasattr(pack, 'get_inventory'):
    norm_params["inventory"] = pack.get_inventory()
norm_asr = await pre.normalize_tokens(cleaned_asr, **norm_params)

# ✓ CORRECTO - En _resolve_hyp_tokens
norm_params = {}
if inventory is not None:
    norm_params["inventory"] = inventory
res = await pre.normalize_tokens(tokens, **norm_params)
```

---

## 4. **Mejora: Verificación de Existencia de Método**

### Ubicación
`ipa_core/pipeline/runner.py` línea 95

### Mejora
Se agregó una verificación `hasattr()` para soportar tanto packs reales como packs mockeados en tests:
```python
# ✓ MEJOR - Compatible con mocks y objetos reales
if pack is not None and hasattr(pack, 'get_inventory'):
    norm_params["inventory"] = pack.get_inventory()
```

Esto previene que `AttributeError` ocurra si `pack` es un `TrackingPack` o similar que no tiene el método `get_inventory()`.

---

## Estado de Tests

Después de las correcciones:
- ✓ **29/29 tests en `ipa_core/pipeline/tests/`**: PASAN
- ✓ **8/8 tests en `test_runner.py`**: PASAN
- ✓ **Todos los tests de limpieza y transcripción**: PASAN

### Validación Ejecutada
```bash
pytest ipa_core/pipeline/tests/ -v
# ======================== 29 passed in 0.75s ==========================
```

---

## Impacto de las Correcciones

### Funcionalidad Preservada
- La normalización de tokens sigue funcionando correctamente
- El inventario del pack se usa para mapear aliases (v → β, z → s, vocales nasales → vocales planas)
- Tanto `run_pipeline` como `execute_pipeline` funcionan correctamente

### Problema Original: "probando" → "prodento"
Las correcciones en `inventory.yaml` permiten que el preprocesador:
1. Mapee variantes que Allosaurus produce (v, z, vocales nasales) a su forma canónica
2. Use el comparador articulatorio mejorado para evaluar similitud fonética
3. Genere scores más precisos (83.38% para el caso del test)

**Nota**: El problema fundamental sigue siendo que Allosaurus escucha "prodento" en lugar de "probando". Las mejoras de normalización pueden ayudar a mapear confusiones comunes, pero no pueden "corregir" errores audiencia real del modelo ASR.

---

## Recomendaciones Siguientes

1. **Validar en contexto real**: Probar con el servidor ejecutando con `PRONUNCIAPA_ASR=allosaurus` y audio real
2. **Mejorar el audio**: Si el usuario obtiene resultados pobres, verificar:
   - Calidad del micrófono
   - Niveles de ruido ambiental
   - Distancia del micrófono al hablante
3. **Ajustar pesos de comparación**: Si `β` vs `ð` sigue siendo un problema, considerar aumento de peso en el comparador articulatorio para distinguir mejor bilabial vs dental
4. **Entrenar modelo personalizado**: Si la precisión sigue siendo baja, considerar fine-tuning de Allosaurus con datos de español mexicano
