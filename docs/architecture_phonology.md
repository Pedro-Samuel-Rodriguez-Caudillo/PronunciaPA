# Arquitectura del Sistema Fonológico

## Visión General

PronunciaPA utiliza un sistema fonológico basado en la teoría generativa (SPE - Chomsky & Halle)
para analizar y evaluar la pronunciación del usuario.

## Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTRADA                                         │
│                                                                              │
│   Texto objetivo: "casa"              Audio del usuario: grabación.wav       │
│         │                                        │                           │
│         ▼                                        ▼                           │
│  ┌──────────────┐                       ┌──────────────┐                    │
│  │ eSpeak/      │                       │  Allosaurus  │                    │
│  │ Epitran      │                       │  (ASR)       │                    │
│  │ (G2P)        │                       │              │                    │
│  └──────┬───────┘                       └──────┬───────┘                    │
│         │                                      │                             │
│         ▼                                      ▼                             │
│    /kasa/                               [ˈka.sa] o [ˈka.θa]                 │
│    (fonémico)                           (fonético observado)                 │
│         │                                      │                             │
└─────────┼──────────────────────────────────────┼────────────────────────────┘
          │                                      │
          ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LANGUAGE PACK PLUGIN                                 │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                │
│  │   Inventario   │  │    Gramática   │  │    Scoring     │                │
│  │   Fonético     │  │   Fonológica   │  │    Profile     │                │
│  │                │  │                │  │                │                │
│  │ • Fonemas      │  │ • Reglas       │  │ • Pesos        │                │
│  │ • Alófonos     │  │   ordenadas    │  │ • Variantes    │                │
│  │ • Rasgos       │  │ • derive()     │  │   aceptables   │                │
│  │                │  │ • collapse()   │  │                │                │
│  └────────────────┘  └────────────────┘  └────────────────┘                │
│                                                                              │
│  Operaciones según evaluation_level:                                        │
│                                                                              │
│  evaluation_level = "phonemic":                                             │
│    Target:   /kasa/ (ya fonémico)                                           │
│    Observed: [ˈka.sa] → collapse() → /kasa/                                 │
│                                                                              │
│  evaluation_level = "phonetic":                                             │
│    Target:   /kasa/ → derive() → [ˈka.sa]                                   │
│    Observed: [ˈka.sa] (ya fonético)                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
          │                                      │
          └──────────────┬───────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COMPARADOR                                         │
│                                                                              │
│  • Alineación Wagner-Fischer (Levenshtein)                                  │
│  • Pesos articulatorios (fonemas similares = menor costo)                   │
│  • Aplicar ScoringProfile según mode                                        │
│                                                                              │
│  mode:                                                                       │
│    casual    → Alta tolerancia, variantes aceptadas                         │
│    objective → Balance entre precisión y pedagogía                          │
│    phonetic  → Muy estricto, cada detalle cuenta                            │
│                                                                              │
│  Output: ErrorReport con operaciones S/I/D y métricas                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Parámetros del Usuario

| Parámetro | Valores | Descripción |
|-----------|---------|-------------|
| `mode` | casual, objective, phonetic | Nivel de tolerancia/scoring |
| `evaluation_level` | phonemic, phonetic | Nivel de representación para comparar |

### Combinaciones

| mode | evaluation_level | Uso típico |
|------|------------------|------------|
| casual + phonemic | Principiantes. "Se entiende" es suficiente |
| objective + phonemic | Aprendices intermedios. Fonemas correctos |
| objective + phonetic | Avanzados. Detalles alofónicos |
| phonetic + phonetic | Profesionales/lingüistas. Máxima precisión |

## Componentes Principales

### 1. PhoneticInventory
Define qué sonidos son válidos para un dialecto.

```yaml
# inventory.yaml
consonants:
  phonemes: [p, b, t, d, k, g, ...]
  # Los alófonos se derivan de reglas
vowels:
  phonemes: [a, e, i, o, u]
```

### 2. PhonologicalGrammar
Reglas ordenadas para convertir entre niveles.

```yaml
# rules.yaml
- name: "Espirantización"
  input: [b, d, g]
  output: [β, ð, ɣ]
  context: "V_V"  # entre vocales
  order: 1
```

**Operaciones**:
- `derive(phonemic) → phonetic`: Aplica reglas para generar forma superficial
- `collapse(phonetic) → phonemic`: Revierte alófonos a fonemas base

### 3. ScoringProfile
Pesos configurables por modo.

```yaml
# scoring/objective.yaml
phoneme_error_weight: 1.0
allophone_error_weight: 0.3  # [β] por /b/ es menor error
prosody_weight: 0.5
acceptable_variants:
  - [b, β]  # En modo casual, son equivalentes
```

## Jerarquía de Chomsky en Fonología

| Tipo | Uso |
|------|-----|
| Type 3 (Regular) | Inventario de fonemas |
| Type 2 (Context-Free) | Estructura silábica |
| Type 1 (Context-Sensitive) | Reglas alofónicas |

Las reglas fonológicas son **sensibles al contexto** (Type 1):
- `/b/ → [β]` solo ocurre entre vocales
- `/n/ → [m]` solo antes de labiales

## Estructura de Archivos

```
ipa_core/
├── phonology/
│   ├── __init__.py
│   ├── features.py      # Rasgos SPE (+voice, +continuant, ...)
│   ├── segment.py       # Clase Segment (fonema/alófono)
│   ├── inventory.py     # PhoneticInventory
│   ├── rule.py          # PhonologicalRule
│   └── grammar.py       # PhonologicalGrammar (derive/collapse)
│
├── plugins/
│   └── language_pack.py # LanguagePackPlugin
│
├── scoring/
│   └── profile.py       # ScoringProfile
│
└── pipeline/
    └── transcribe.py    # Pipeline con mode + evaluation_level

## Implementación actual (estado)

- **Tokenización IPA**: `tokenize_ipa` reconoce dígrafos/africadas (tʃ, dʒ, ts, dz)
  y diptongos frecuentes (aɪ, aʊ, ɔɪ, oʊ, eɪ, ai, ei, oi, au, eu, iu); elimina acentos
  y separadores silábicos para aplicar reglas y alineación sobre segmentos.
- **Reglas bidireccionales**: `PhonologicalRule.apply` opera sobre tokens; `apply_inverse`
  revierte alófonos→fonemas cuando la salida es invertible, permitiendo `collapse`
  más fiel antes de usar el inventario.
- **Gramática**: `derive` aplica reglas ordenadas; `collapse` elimina suprasegmentales,
  revierte reglas en orden inverso y luego mapea al inventario (`collapse_to_phoneme`).
- **Language Pack en pipeline**: `compare_with_pack` (y `run_pipeline_with_pack`) orquesta
  preprocesado→ASR→TextRef, aplica `derive/collapse` según `evaluation_level` y
  usa el `ScoringProfile` (tolerancia/acceptable_variants/pesos) al comparar.
- **Scoring**: el comparador ajusta costos mínimos según `tolerance` del perfil y pondera
  sustituciones aceptables como errores de alófono (peso menor) vs. errores de fonema.

### Próximos pasos sugeridos

- Exponer `evaluation_level` y `mode` en CLI/API usando `run_pipeline_with_pack`.
- Añadir validaciones de inventario (todos los símbolos con rasgos conocidos) y reglas
  basadas en clases naturales.
- Ampliar pruebas de round-trip derive→collapse con language packs ES/EN.

plugins/language_packs/
├── es-mx/
│   ├── manifest.yaml
│   ├── inventory.yaml
│   ├── phonological_rules.yaml
│   ├── exceptions.yaml
│   └── scoring/
│       ├── casual.yaml
│       ├── objective.yaml
│       └── phonetic.yaml
└── en-us/
    └── ...
```
