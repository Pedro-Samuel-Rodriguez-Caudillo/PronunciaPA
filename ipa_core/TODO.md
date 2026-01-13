# TODO
TODO (lineal, robusto, microkernel + adapters)
0) Selección de lección

Selección de lección: el sistema define language, dialect, mode (Casual/Objetivo/Fonético), goal (Se entiende/Contra objetivo), target_text, velocidad sugerida, longitud máxima (tokens/segundos) y criterio de aceptación (p. ej. 
𝑃
𝐸
𝑅
𝑤
PER
w
	​

 máximo y umbral de “fiabilidad del intento”).

1) Microkernel: carga de plugins (antes de grabar)

Carga de plugins: se cargan Language Pack del idioma/dialecto, Model Pack del LLM seleccionado (3B/7B/14B) y el Runtime Adapter correspondiente (ONNX o llama.cpp), validando compatibilidad de versiones, schema, inventario fonético, mappings de phones y configuración del scoring_profile.

2) Preparación de referencia (antes de grabar)

Preparación de referencia: se genera target_ipa_phonemic desde el catálogo léxico (palabra → IPA) con variantes contextuales; si mode=Fonético, se expande a target_ipa_phonetic aplicando reglas del pack (asimilación, reducciones permitidas, diacríticos habilitados) y se fija el conjunto de variantes permitidas con reglas de elección consistentes (sin “escoger la mejor” salvo que el modo lo autorice explícitamente).

3) Reproducción / ejemplo

Reproducción/ejemplo: se reproduce audio de referencia (TTS local o audio del pack) y, si aplica, una guía corta del foco del intento (1–2 fonemas objetivo) derivada de la adaptación previa.

4) Grabación y metadatos

Grabación: captura a tasa fija (p. ej. 16 kHz mono), con control de clipping y ganancia; se registran metadatos del intento (dispositivo, nivel de entrada, duración, timestamp local).

5) Detección de voz (VAD) y segmentación

Detección de voz (VAD): recorte de silencios, detección de pausas internas y segmentación (por palabra/frase) si el target excede un umbral de duración; se calcula ratio voz/silencio.

6) Preprocesamiento + quality gates

Preprocesamiento: normalización de nivel, reducción ligera de ruido (opcional), verificación de duración mínima, proxy de SNR y detección de clipping; si falla validación, se retorna feedback operativo (“repite más lento / más cerca / menos ruido”) y se omite análisis fonético fino.

7) Reconocimiento fonético (Allosaurus)

Reconocimiento fonético (Allosaurus): se obtiene observed_phone_seq por segmento; si existen timestamps o scores, se conservan; si no, se generan aproximaciones de duración por segmento desde VAD.

8) Normalización de inventario (phones → IPA consistente)

Normalización de inventario: se mapea observed_phone_seq al inventario interno del Language Pack y a IPA tokenizada consistente (símbolo base + diacríticos según reglas del modo); se aplica política de colapso alofónico según mode y se marca cualquier OOV con estrategia definida (colapsar por clase, marcar como desconocido o descartar con penalización).

9) Alineación + métrica (DP)

Alineación y métrica: se alinea target_ipa vs observed_ipa usando DP (Wagner–Fischer / Levenshtein) con costos ponderados por distancia articulatoria (errores cercanos penalizan menos) y peso adicional si el cambio afecta contraste que cambia significado; se obtiene lista de operaciones S/I/D y métricas 
𝑃
𝐸
𝑅
𝑤
PER
w
	​

, score 0–100 y desglose por clase de error.

10) Prosodia/ritmo (opcional por modo/tier)

Prosodia/ritmo: si está habilitado por mode/tier, se calculan métricas de pausas, velocidad y duraciones relativas por segmento (y desviaciones respecto al patrón del target); se integran al score según pesos del scoring_profile del pack (bajo en Casual, medio en Objetivo, configurable en Fonético).

11) Postprocesado de errores (selección 1–3 focos)

Postprocesado de errores: se agrupan errores por fonema y por rasgos articulatorios (sonoridad, lugar, modo; vocales: altura/redondeamiento), se filtran por “fiabilidad del intento” y se seleccionan 1–3 focos máximos por intento (priorizando impacto semántico, repetición histórica y baja estabilidad).

12) Construcción del Error Report (JSON canónico)

Error Report: se genera un JSON canónico (independiente del runtime/modelo) con target_text, target_ipa, observed_ipa, métricas, lista de errores con rasgos y severidad, sugerencias de delta articulatorio calculadas por reglas, contexto mode/goal/dialect y resumen de calidad de audio; este JSON es el único input permitido al LLM.

13) Generación de feedback (LLM local vía adapter)

Generación de feedback: se invoca el Runtime Adapter seleccionado (ONNX o llama.cpp) para ejecutar el Model Pack con un prompt determinista que exige salida JSON; el LLM devuelve advice_short (casual/pedagógico) y advice_long (técnico/fino), más drills (pares mínimos, sílabas y frases) y una línea “Se entiende, pero…” cuando goal=Se entiende o explicación estricta cuando goal=Contra objetivo.

14) Validación y guardrails

Validación y guardrails: se valida el JSON del LLM contra schema; si falla, se reintenta una sola vez con prompt de corrección; si vuelve a fallar, se usa un generador determinista de fallback (plantillas del Language Pack) para no bloquear UX.

15) Render (UI)

Render: se muestra target_ipa (y texto), observed_ipa, score y desglose (significado/segmental/prosodia), y el feedback con control de vista corta/larga y acciones (repetir, escuchar ejemplo, practicar drills).

16) Persistencia (local)

Persistencia: se guarda historial del intento, score, errores normalizados, métricas de calidad, confusiones frecuentes por fonema, progreso por modo y selección de dialecto; opcionalmente se guarda audio bajo consentimiento.

17) Adaptación

Adaptación: la siguiente lección prioriza fonemas/rasgos con mayor error ponderado, baja estabilidad y alta relevancia semántica; ajusta longitud del target y ritmo sugerido según el desempeño y la calidad de audio reciente.

18) Mantenimiento de packs (offline)

Mantenimiento de packs: se permite instalar/actualizar Language Packs y Model Packs offline; se valida firma/integridad y compatibilidad; se mantiene un índice local para revertir versiones si un pack degrada desempeño.

19) Bench y calibración local

Bench y calibración local: se ejecuta un conjunto pequeño de casos sintéticos por idioma/modo para calibrar umbrales de fiabilidad y medir tasa de JSON válido del LLM, latencia y memoria por tier (3B/7B/14B), ajustando automáticamente el tier recomendado para el dispositivo.

flowchart TD
  A[Selección lección] --> B[Carga plugins: Language/Model/Adapter]
  B --> C[Referencia: IPA + variantes]
  C --> D[Grabación + VAD + quality gates]
  D -->|OK| E[Allosaurus phones]
  E --> F[phones→IPA]
  F --> G[Alineación DP + score]
  G --> H[Error Report JSON]
  H --> I[LLM via Adapter → feedback JSON]
  I --> J[Validación/fallback]
  J --> K[Render]
  K --> L[Persistencia]
  L --> M[Adaptación]
  D -->|Falla| K
