# Comparadores IPA

Paquete responsable de calcular metrica y operaciones entre secuencias IPA.

## Componentes
- base.Comparator: interfaz abstracta que define compare(ref_ipa, hyp_ipa) y retorna CompareResult.
- base.CompareResult: dataclass con PER y lista de operaciones (op, ref, hyp).
- noop.NoopComparator: stub que devuelve PER 0 sin analizar entradas.

## Arquitectura de referencia
- Evaluar un BiLSTM (bidireccional) para modelar interdependencias secuenciales antes de calcular la distancia.
- Combinar la salida del BiLSTM con algoritmos clasicos (Levenshtein) para obtener PER explicable.
- Mantener interfaces puras para que el kernel solo orqueste sin acoplarse a arquitecturas especificas.

## Flujo esperado
1. Tokenizar ambas cadenas IPA (por simbolo o bigrama segun la convencion elegida).
2. Calcular distancia de edicion o metrica especifica.
3. Construir CompareResult con la puntuacion y el detalle de operaciones.

## Buenas practicas
- Mantener determinismo: mismas entradas deben producir siempre el mismo PER.
- Perfilar rendimiento: comparaciones largas pueden requerir algoritmos optimizados.
- Separar tokenizacion y metrica para reutilizar logica entre comparadores.

## Registro como plugin
Declare la clase en pyproject.toml dentro del grupo ipa_core.plugins.compare para que el kernel pueda descubrirla.
