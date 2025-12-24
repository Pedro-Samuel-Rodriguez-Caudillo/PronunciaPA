# Reglas Específicas del Proyecto

## Flujo de Control
*   **Nivel Máximo de Anidamiento:** Limitar el anidamiento a un máximo de 3 niveles.
*   **Cláusulas de Guarda:** Preferir retornos tempranos (guard clauses) en lugar de estructuras `if/else` profundamente anidadas.

## Arquitectura y Patrones
*   **Patrones de Diseño:** Utilizar patrones de diseño establecidos (ej. Strategy, Factory, Observer) cuando mejoren claramente la mantenibilidad o desacoplen componentes. No forzar patrones donde una lógica simple sea suficiente.

## Documentación y Comentarios
*   **Idioma:** Español.
*   **Nivel:** Profesional / Ingeniería.
*   **Verbosidad:** Equilibrada.
    *   Explicar el *por qué* de la lógica compleja o decisiones de diseño no obvias.
    *   Evitar explicar la sintaxis básica del lenguaje (no sobre-explicar).
    *   No dejar "números mágicos" o lógica oscura sin documentar (no infra-explicar).
