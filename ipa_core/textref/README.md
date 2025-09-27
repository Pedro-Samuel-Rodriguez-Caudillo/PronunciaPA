# TextRef

Paquete que transforma texto de referencia en secuencias IPA normalizadas.

## Clases incluidas
- base.TextRef: interfaz abstracta con el metodo text_to_ipa.
- nop.NoopTextRef: implementacion de prueba que devuelve una cadena fija.

## Flujo recomendado
1. Limpiar el texto de entrada (minusculas, signos).
2. Aplicar el convertidor G2P seleccionado segun el idioma.
3. Normalizar simbolos de salida para que sean compatibles con los comparadores.

## Registro como plugin
Anada la clase al grupo ipa_core.plugins.textref en pyproject.toml con un nombre unico.

## Ideas de extensiones
- Integracion con gruut, epitran u otros recursos G2P.
- Soporte para multiples idiomas mediante lang opcional.
- Reglas de post-procesamiento para ajustar signos diacriticos y acentos.

